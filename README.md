# genx-oracle

Python client and server for the [TxLINE API](https://txline-docs.txodds.com) — a cryptographically-verifiable sports data feed (odds, scores, fixtures) backed by Solana on-chain subscriptions.

## Overview

- **`txline-subscribe`** — one-time wallet setup that activates your on-chain subscription and stores credentials locally
- **`txline-stream`** — CLI for tailing live SSE streams (odds, scores) or fetching fixture snapshots
- **`txline-server`** — FastAPI SSE proxy server for browser clients

## Requirements

- Python 3.11+
- A funded Solana wallet (0.02 SOL is sufficient)

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## One-time activation

Generate a wallet (or bring your own `wallet.json`), then activate your subscription:

```bash
.venv/bin/python3 scripts/generate_wallet.py   # creates wallet.json
.venv/bin/python3 scripts/check_wallet.py       # verify balance
.venv/bin/txline-subscribe                      # activates subscription, writes .txline-credentials.json
```

`wallet.json` and `.txline-credentials.json` are gitignored — back them up externally.

## CLI usage

```bash
# Live odds stream
.venv/bin/txline-stream odds

# Live scores stream, filtered by fixture
.venv/bin/txline-stream scores --fixture-id 12345

# Fixture snapshot (REST)
.venv/bin/txline-stream fixtures
```

## SSE proxy server

Serves browser clients that can't add custom headers directly.

```bash
.venv/bin/txline-server                   # starts on 0.0.0.0:8000
.venv/bin/txline-server --port 9000       # custom port
```

Endpoints:

| Path | Description |
|------|-------------|
| `GET /fixtures` | Fixture snapshot |
| `GET /odds/stream` | Live odds SSE stream |
| `GET /scores/stream` | Live scores SSE stream |

Both stream endpoints accept an optional `?fixtureId=<id>` query parameter.

## Docker

```bash
docker build -t txline-server .

docker run -p 8000:8000 \
  -v /path/to/.txline-credentials.json:/app/credentials/.txline-credentials.json:ro \
  txline-server
```

The image is published to `ghcr.io/teamzuzu/txline-server` on every `v*.*.*` tag and every push to `main`.

## Kubernetes

Install via the published Helm chart:

```bash
helm repo add txline https://teamzuzu.github.io/genx-oracle
helm repo update
helm install txline-server txline/txline-server \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)" \
  --set image.tag=0.0.1 \
  --set ingress.host=txline.example.com
```

Or from the local chart:

```bash
helm install txline-server helm/txline-server/ \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)"
```

Key values: `image.repository`, `image.tag`, `ingress.host`, `ingress.className`.

## Development

```bash
.venv/bin/ruff check txline/   # lint
.venv/bin/pytest               # tests
```

## Architecture

Credential lifecycle:
1. `txline-subscribe` generates a guest JWT, submits a zero-cost on-chain subscription via `anchorpy`, signs the activation message with the wallet key, and POSTs to `/api/token/activate`. The resulting `{jwt, api_token}` pair is saved to `.txline-credentials.json`.
2. At runtime, `TxLineClient` reads that file and sends `Authorization: Bearer {jwt}` + `X-Api-Token: {api_token}` on every request.

SSE streams (`txline/streams/`) use `httpx-sse` and yield typed Pydantic models (`OddsUpdate | Heartbeat`, `ScoreUpdate | Heartbeat`). Both support `Last-Event-ID` reconnection.
