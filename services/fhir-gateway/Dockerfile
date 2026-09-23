FROM python:3.12-slim

WORKDIR /app

# curl is needed by the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY services/fhir-gateway/pyproject.toml ./
RUN uv pip install --system --no-cache -e .

COPY services/fhir-gateway/src ./src
COPY packages ./packages

EXPOSE 8003
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8003"]
