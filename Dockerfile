FROM python:3.11-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot/ bot/
COPY config/ config/

# Persistent mount points (must match docker-compose volumes)
RUN mkdir -p /data /whisper-cache /app/tmp /app/logs

ENV PYTHONUNBUFFERED=1
# Absolute paths — required so data lands on mounted volumes, not ephemeral layer
ENV DATABASE_PATH=/data/bot.db
ENV WHISPER_CACHE_DIR=/whisper-cache
ENV HF_HOME=/whisper-cache
ENV HUGGINGFACE_HUB_CACHE=/whisper-cache/hub
ENV LOG_FILE=/app/logs/bot.log
ENV LLAMA_MODE=api
ENV LLAMA_API_URL=http://llama:8080
ENV WORKER_COUNT=1

CMD ["python", "-m", "bot"]
