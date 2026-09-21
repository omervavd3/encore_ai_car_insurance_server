FROM python:3.13-slim

# Fail fast on unbuffered logs so Cloud Run captures output immediately.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8080

WORKDIR /srv

# Dependencies first so image layers cache across code-only rebuilds.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Cloud Run recommends running as a non-root user.
RUN useradd --create-home --uid 1000 appuser
USER appuser

EXPOSE 8080

# Shell form so ${PORT} expands; exec so uvicorn is PID 1 and receives SIGTERM
# for graceful shutdown when Cloud Run scales the instance down.
CMD exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
