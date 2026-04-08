FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
ENV PYTHONPATH=/app
# Default task for the OpenEnv server (easy | medium | hard)
ENV SCAM_ENV_TASK=easy
EXPOSE 7860

# Hugging Face Spaces sets PORT; validator pings POST /reset
CMD ["sh", "-c", "uvicorn server.app:app --host 0.0.0.0 --port ${PORT:-7860}"]
