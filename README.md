# genx-oracle

Python client and server for the [TxLINE API](https://txline-docs.txodds.com) — a cryptographically-verifiable sports data feed (odds, scores, fixtures) backed by Solana on-chain subscriptions.

## Overview

| Tool | Description |
|------|-------------|
| `txline-subscribe` | One-time wallet setup — activates your on-chain subscription and stores credentials locally |
| `txline-stream` | CLI for tailing live SSE streams (odds, scores) or fetching fixture snapshots |
| `txline-watch` | Live terminal dashboard combining odds + scores streams (Rich.Live TUI) |
| `txline-server` | FastAPI SSE proxy + browser dashboard served at `/` |

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

# Live terminal dashboard (odds + scores combined)
.venv/bin/txline-watch
.venv/bin/txline-watch --fixture-id 12345
```

## Browser dashboard

`txline-server` serves a live web dashboard at `http://localhost:8000` alongside the SSE API endpoints.

```bash
.venv/bin/txline-server                   # starts on 0.0.0.0:8000
.venv/bin/txline-server --port 9000       # custom port
```

Open `http://localhost:8000` to see the live dashboard. It mirrors `txline-watch`: fixture names, scores, odds (decimal), and implied probabilities, updated in real-time with row flash highlighting.

### API endpoints

| Path | Description |
|------|-------------|
| `GET /` | Browser dashboard |
| `GET /fixtures` | Fixture snapshot (JSON) |
| `GET /odds/stream` | Live odds SSE stream (`event: odds`) |
| `GET /scores/stream` | Live scores SSE stream (`event: scores`) |

Both stream endpoints accept an optional `?fixtureId=<id>` query parameter.

## Docker

```bash
docker build -t txline-server .

docker run -p 8000:8000 \
  -v /path/to/.txline-credentials.json:/app/credentials/.txline-credentials.json:ro \
  txline-server
```

The image is published to `ghcr.io/teamzuzu/txline-server` automatically:
- Push to `main` → `:latest`
- Push a `v*.*.*` tag → versioned tag + `:latest`

## Kubernetes

### Quick start with a pre-existing secret

```bash
# Create the credentials secret once:
kubectl create secret generic txline-credentials \
  --from-file=.txline-credentials.json

# Install from the published Helm chart:
helm repo add txline https://teamzuzu.github.io/genx-oracle
helm repo update
helm install txline-server txline/txline-server \
  --set credentials.existingSecret=txline-credentials \
  --set image.tag=latest \
  --set ingress.host=txline.example.com
```

### Inline credentials (chart manages the Secret)

```bash
helm install txline-server txline/txline-server \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)" \
  --set image.tag=latest \
  --set ingress.host=txline.example.com
```

### Upgrade

```bash
# With pre-existing secret — no credentials needed:
helm upgrade txline-server txline/txline-server \
  --set credentials.existingSecret=txline-credentials \
  --set image.tag=<new-version>
```

Key values to override: `image.repository`, `image.tag`, `ingress.host`, `ingress.className`.

## Development

```bash
.venv/bin/ruff check txline/   # lint
.venv/bin/pytest               # tests (28 passing)
```

## Architecture

**Credential lifecycle:**
1. `txline-subscribe` generates a guest JWT, submits a zero-cost on-chain subscription via `anchorpy`, signs the activation message with the wallet key, and POSTs to `/api/token/activate`. The resulting `{jwt, api_token}` pair is saved to `.txline-credentials.json`.
2. At runtime, `TxLineClient` reads that file and sends `Authorization: Bearer {jwt}` + `X-Api-Token: {api_token}` on every request.

**SSE streams** (`txline/streams/`) use `httpx-sse` and yield typed Pydantic models (`OddsUpdate | Heartbeat`, `ScoreUpdate | Heartbeat`). Both support `Last-Event-ID` reconnection and optional `fixtureId` filtering.

**`txline-watch`** fans both streams into an `asyncio.Queue`, merges events into a `dict[int, FixtureState]`, and renders a `Rich.Live` table. Prices are integers ÷ 1000 = decimal odds.

**`txline-server`** proxies the three TxLINE endpoints and serves a vanilla JS dashboard from `txline/api/static/`. The browser dashboard opens two `EventSource` connections, maintains the same state map as `txline-watch`, and re-renders a table on every event with flash highlighting on updated rows.
