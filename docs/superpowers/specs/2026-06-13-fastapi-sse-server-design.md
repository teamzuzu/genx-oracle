# FastAPI SSE Server Design

**Date:** 2026-06-13
**Status:** Approved

## Goal

A standalone FastAPI service that proxies TxLINE data to browser clients via SSE. Intended for embedding live odds in a website.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/fixtures` | JSON snapshot of upcoming fixtures |
| GET | `/odds/stream` | SSE passthrough of live odds updates |
| GET | `/scores/stream` | SSE passthrough of live score updates |

Both stream endpoints accept an optional `?fixtureId=<int>` query parameter, passed through to TxLINE unchanged.

Response format for streams mirrors TxLINE exactly — same `event:` names, same JSON `data:` payloads. Browser clients use the native `EventSource` API.

## Architecture

### New files

```
txline/api/__init__.py
txline/api/server.py        # FastAPI app + uvicorn CLI entry point
```

### New entry point (pyproject.toml)

```
txline-server = txline.api.server:cli
```

Run with: `.venv/bin/txline-server` (binds `0.0.0.0:8000` by default, overridable via `--host`/`--port`).

### Credentials

Loaded from `.txline-credentials.json` at startup via the existing `load_credentials()`. Server exits immediately with a clear error if the file is missing or invalid — run `txline-subscribe` first.

### CORS

`CORSMiddleware` configured with `allow_origins=["*"]`, `allow_methods=["GET"]`. The service is intentionally open.

### SSE passthrough mechanics

Each browser `EventSource` connection opens one TxLINE SSE connection. The existing `stream_odds()` / `stream_scores()` async generators are iterated and each event is re-emitted to the browser. On client disconnect, the generator is cancelled and the TxLINE connection closes.

`sse-starlette` handles SSE response formatting on the FastAPI side.

### Scale note

This is a direct passthrough — N browser clients = N TxLINE connections. Acceptable for low-traffic embeds. A fan-out broker can be added later if connection limits become a concern.

## Dependencies added

Added to core deps in `pyproject.toml`:

- `fastapi`
- `uvicorn[standard]`
- `sse-starlette`

## What stays unchanged

`TxLineClient`, all stream generators (`stream_odds`, `stream_scores`), `get_fixtures`, auth, and subscription code are untouched. The FastAPI layer is purely additive.
