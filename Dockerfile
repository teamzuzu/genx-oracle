FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
COPY txline/ txline/

RUN pip install --no-cache-dir . \
    && useradd --no-create-home --shell /bin/false appuser \
    && mkdir -p /app/credentials \
    && chown appuser:appuser /app/credentials

USER appuser

EXPOSE 8000

ENTRYPOINT ["txline-server", "--credentials", "/app/credentials/.txline-credentials.json"]
