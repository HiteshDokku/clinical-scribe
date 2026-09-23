"""fhir-gateway service entry point. Placeholder health check only — business
logic is added milestone by milestone per docs/architecture.md."""

from fastapi import FastAPI

app = FastAPI(title="fhir-gateway")


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "fhir-gateway"}
