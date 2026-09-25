FROM python:3.12-slim

WORKDIR /app

# curl is needed by the docker-compose healthcheck, ffmpeg is needed for faster-whisper
RUN apt-get update && apt-get install -y --no-install-recommends curl ffmpeg git git-lfs \
    && rm -rf /var/lib/apt/lists/*

COPY services/asr/models /models

ENV WHISPER_MODEL=tiny


RUN pip install --no-cache-dir uv

COPY services/asr/pyproject.toml ./
RUN uv pip install --system --no-cache --extra-index-url https://download.pytorch.org/whl/cpu torch torchaudio
RUN uv pip install --system --no-cache -e .

COPY services/asr/src ./src
COPY packages ./packages

RUN uv pip install --system pytest httpx websockets

# Pre-download models so they don't require internet at runtime
ENV HF_HOME=/root/.cache/huggingface
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('tiny', device='cpu', compute_type='int8')"
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
RUN python -c "from src.vad import VADGater; VADGater()"

ENV HF_HUB_OFFLINE=1

EXPOSE 8001
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8001"]
