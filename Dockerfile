FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir \
    "httpx>=0.27" \
    "httpx-sse>=0.4" \
    "pydantic>=2.7" \
    "pynacl>=1.5" \
    "python-dotenv>=1.0" \
    "solders>=0.21" \
    "anchorpy>=0.20" \
    "click>=8.1" \
    "rich>=13.0" \
    "fastapi>=0.111" \
    "uvicorn[standard]>=0.29" \
    "sse-starlette>=1.6" \
    "aiofiles>=23.0"

COPY txline/ txline/
RUN pip install --no-cache-dir --no-deps .

RUN useradd --uid 1000 --no-create-home --shell /bin/false appuser \
    && mkdir -p /app/credentials \
    && chown appuser:appuser /app/credentials

USER appuser

EXPOSE 8000

VOLUME ["/app/credentials"]

ENTRYPOINT ["txline-server", "--credentials", "/app/credentials/.txline-credentials.json"]
