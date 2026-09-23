# Wraps the FastAPI stub for the scaffold. The actual llama.cpp server binary
# and Llama 3 8B Instruct GGUF weights are external artifacts fetched by
# infra/scripts/build-llamacpp.sh and infra/scripts/download-models.sh.
# Those scripts run once on the host, outside Docker, because model weights
# are too large to bake into image layers. See docs/architecture.md §7.

FROM python:3.12-slim

WORKDIR /app

# curl is needed by the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY services/llm/pyproject.toml ./
RUN uv pip install --system --no-cache -e .

COPY services/llm/src ./src
COPY services/llm/prompts ./prompts
COPY packages ./packages

EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
