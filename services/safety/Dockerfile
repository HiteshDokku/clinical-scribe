FROM python:3.12-slim

WORKDIR /app

# curl is needed by the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY services/safety/pyproject.toml ./
RUN uv pip install --system --no-cache -e .[dev]

# Pre-download the HuggingFace NLI model during build to ensure strict offline mode at runtime
ENV HF_HUB_OFFLINE=0
RUN python -c "from transformers import AutoTokenizer, AutoModelForSequenceClassification; \
    AutoTokenizer.from_pretrained('cross-encoder/nli-deberta-v3-small'); \
    AutoModelForSequenceClassification.from_pretrained('cross-encoder/nli-deberta-v3-small')"
ENV HF_HUB_OFFLINE=1

COPY services/safety/src ./src
COPY packages ./packages

EXPOSE 8002
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
