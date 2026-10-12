FROM python:3.12-slim

WORKDIR /app

# curl is needed by the docker-compose healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY services/safety/pyproject.toml ./
RUN uv pip install --system --no-cache -e .[dev]

ENV HF_HUB_OFFLINE=1
ENV TRANSFORMERS_OFFLINE=1

COPY services/safety/models ./models

COPY services/safety/src ./src
COPY services/safety/data ./data
COPY packages ./packages

EXPOSE 8002
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8002"]
