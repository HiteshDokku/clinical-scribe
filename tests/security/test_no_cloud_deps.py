"""
Enforces ADR-0001 (egress policy) at the dependency-declaration level.

This test is intentionally strict and un-negotiable: AGENTS.md tells an
agent not to add a hosted-AI dependency, but instructions in a markdown
file are advisory. This test is not. It runs in CI on every push.
"""

from pathlib import Path

import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]

BANNED = {
    "openai",
    "anthropic",
    "google-generativeai",
    "google-cloud-speech",
    "azure-cognitiveservices-speech",
    "boto3",
    "azure-identity",
    "assemblyai",
    "deepgram",
    "sentry-sdk",
}


def _declared_deps(pyproject_path: Path) -> set[str]:
    data = tomllib.loads(pyproject_path.read_text())
    deps = data.get("project", {}).get("dependencies", [])
    names = set()
    for dep in deps:
        # strip version specifiers and extras: "boto3[crt]>=1.0" -> "boto3"
        name = dep.split("==")[0].split(">=")[0].split("<")[0].split("[")[0].strip()
        names.add(name.lower())
    return names


def test_no_service_declares_a_banned_dependency():
    offenders: dict[str, set[str]] = {}
    for pyproject in (REPO_ROOT / "services").glob("*/pyproject.toml"):
        declared = _declared_deps(pyproject)
        hit = declared & BANNED
        if hit:
            offenders[str(pyproject.relative_to(REPO_ROOT))] = hit
    assert not offenders, f"banned dependency declared: {offenders}"


def test_web_client_declares_no_cloud_ai_sdk():
    package_json = REPO_ROOT / "apps" / "web" / "package.json"
    if not package_json.exists():
        return  # nothing to check yet at this stage of the build
    import json

    data = json.loads(package_json.read_text())
    all_deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
    banned_js = {"openai", "@anthropic-ai/sdk", "@google-cloud/speech", "aws-sdk"}
    hit = set(all_deps.keys()) & banned_js
    assert not hit, f"web client declares a banned cloud SDK: {hit}"
