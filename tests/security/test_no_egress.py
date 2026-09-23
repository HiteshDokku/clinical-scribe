"""
Enforces ADR-0001 (egress policy) at runtime, inside each service container.

Run this INSIDE the asr, llm, and safety containers (they should have no
route out at all), e.g.:

    docker compose run --rm --network none asr pytest tests/security/test_no_egress.py

The gateway and fhir-gateway containers are intentionally exempt from
test_container_cannot_reach_public_internet, since fhir-gateway needs a
narrow allowlisted egress — see test_fhir_gateway_egress_is_allowlisted_only
in tests/fhir/test_egress_allowlist.py for its equivalent guard.
"""

import socket

import pytest


def test_container_cannot_reach_public_internet():
    with pytest.raises((socket.timeout, OSError)):
        socket.create_connection(("1.1.1.1", 443), timeout=3)


def test_container_cannot_resolve_public_dns():
    with pytest.raises(socket.gaierror):
        socket.gethostbyname("api.openai.com")


def test_container_cannot_reach_common_llm_api_hosts():
    banned_hosts = [
        "api.openai.com",
        "api.anthropic.com",
        "generativelanguage.googleapis.com",
    ]
    for host in banned_hosts:
        with pytest.raises((socket.timeout, OSError, socket.gaierror)):
            socket.create_connection((host, 443), timeout=3)
