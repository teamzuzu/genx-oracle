# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Python client for the [TxLINE API](https://txline-docs.txodds.com) — a cryptographically-verifiable sports data feed (odds, scores, fixtures) backed by Solana on-chain subscriptions.

## Environment

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
```

## Commands

```bash
# Lint
.venv/bin/ruff check txline/

# Tests
.venv/bin/pytest
.venv/bin/pytest tests/test_auth.py::test_build_message   # single test

# CLI
.venv/bin/txline-subscribe          # one-time wallet → credentials setup
.venv/bin/txline-stream odds        # tail live SSE stream
.venv/bin/txline-stream scores --fixture-id 12345
.venv/bin/txline-stream fixtures    # REST snapshot

# Watch dashboard (live odds + scores combined, Rich.Live TUI)
.venv/bin/txline-watch                           # all fixtures
.venv/bin/txline-watch --fixture-id 12345        # filter to one fixture

# Server (FastAPI SSE proxy for browser clients)
.venv/bin/txline-server                          # start on 0.0.0.0:8000
.venv/bin/txline-server --port 9000              # custom port

# Wallet helpers (scripts run directly, not entry points)
.venv/bin/python3 scripts/generate_wallet.py
.venv/bin/python3 scripts/check_wallet.py
```

## Architecture

The credential lifecycle is:
1. **One-time setup** — `txline-subscribe` generates a guest JWT, submits a zero-cost on-chain subscription via `anchorpy`, NaCl-signs the activation message with the wallet key, and POSTs to `/api/token/activate`. The resulting `{jwt, api_token}` pair is persisted to `.txline-credentials.json`.
2. **Runtime** — `TxLineClient` loads credentials from that file and uses `Authorization: Bearer {jwt}` + `X-Api-Token: {api_token}` on every request.

**SSE streaming** (`txline/streams/`) uses `httpx-sse`. Both streams (`/api/odds/stream`, `/api/scores/stream`) support optional `fixtureId` filtering and reconnect via `Last-Event-ID`. Streams yield typed Pydantic models (`OddsUpdate | Heartbeat`, `ScoreUpdate | Heartbeat`).

**`txline-watch`** (`txline/cli/watch.py`) fans odds and scores SSE streams into an `asyncio.Queue`, applies events to a `dict[int, FixtureState]` via `apply_event`, and renders a `Rich.Live` table via `build_table`. Fixture names are resolved lazily from a one-shot REST snapshot fetch. Prices are stored as integers and displayed as decimal odds (÷ 1000).

**The Anchor IDL** (`txline/idl/txline.json`) is fetched from the chain on first run via `anchorpy._fetch_idl` and cached locally. The directory is gitignored. If on-chain fetch fails, place the IDL file there manually.

## Key constants (txline/subscription.py)

| Name | Value |
|------|-------|
| Program ID | `9ExbZjAapQww1vfcisDmrngPinHTEfpjYRWMunJgcKaA` |
| TxL mint | `Zhw9TVKp68a1QrftncMSd6ELXKDtpVMNuMGr1jNwdeL` (Token-2022) |
| Free tier (delayed) | `SERVICE_LEVEL_FREE_DELAYED = 1` |
| Free tier (real-time) | `SERVICE_LEVEL_FREE_REALTIME = 12` |

## Container image

The `Dockerfile` at the repo root builds `txline-server` as a non-root container image.

```bash
# Build locally
docker build -t txline-server .

# Run with credentials mounted
docker run -p 8000:8000 \
  -v /path/to/.txline-credentials.json:/app/credentials/.txline-credentials.json:ro \
  txline-server
```

GitHub Actions (`.github/workflows/docker.yml`) builds and pushes to `ghcr.io/teamzuzu/txline-server` automatically:
- Push to `main` → `:latest`
- Push a `v*.*.*` tag → versioned tag + `:latest`

## Kubernetes / Helm

The Helm chart lives at `helm/txline-server/`. Credentials are injected as a Kubernetes Secret.

Two ways to supply credentials:

**Option A — inline JSON (chart creates the Secret):**
```bash
helm install txline-server helm/txline-server/ \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)" \
  --set image.repository=ghcr.io/teamzuzu/txline-server \
  --set image.tag=latest \
  --set ingress.host=txline.example.com
```

**Option B — pre-existing Secret (no JSON at install time):**
```bash
# Create the secret once (outside Helm lifecycle):
kubectl create secret generic txline-credentials \
  --from-file=.txline-credentials.json

# Install without passing the JSON:
helm install txline-server helm/txline-server/ \
  --set credentials.existingSecret=txline-credentials \
  --set image.repository=ghcr.io/teamzuzu/txline-server \
  --set image.tag=latest \
  --set ingress.host=txline.example.com
```

**Upgrade:**
```bash
# Option A:
helm upgrade txline-server helm/txline-server/ \
  --set credentials.json="$(base64 -w0 .txline-credentials.json)" \
  --set image.tag=<new-version>

# Option B (secret already exists — no credentials needed):
helm upgrade txline-server helm/txline-server/ \
  --set credentials.existingSecret=txline-credentials \
  --set image.tag=<new-version>
```

### Published Helm repository

Once GitHub Pages is enabled (Settings → Pages → `gh-pages` / root), the chart is available at:

```bash
helm repo add txline https://teamzuzu.github.io/genx-oracle
helm repo update
helm install txline-server txline/txline-server \
  --set credentials.existingSecret=txline-credentials \
  --set image.tag=1.0.0 \
  --set ingress.host=txline.example.com
```

### Release checklist (before tagging)

1. Bump `version` and `appVersion` in `helm/txline-server/Chart.yaml` to match the release (e.g. `1.0.0`)
2. Commit: `git commit -m "chore: bump chart to 1.0.0"`
3. Tag: `git tag v1.0.0 && git push origin v1.0.0`
4. Both `docker.yml` and `helm-release.yml` workflows fire automatically

Key values to override: `image.repository`, `image.tag`, `ingress.host`, `ingress.className`.

## Sensitive files (all gitignored)

- `wallet.json` — Solana keypair; back up externally
- `.txline-credentials.json` — live JWT + API token
- `txline/idl/` — cached on-chain IDL


### Git Commits
- Always author and commit as the developer.
- Never include Claude or AI attribution in commit messages.
- Do not use `Co-Authored-By` tags or any other form of AI credit.

