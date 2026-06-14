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

**The Anchor IDL** (`txline/idl/txline.json`) is fetched from the chain on first run via `anchorpy._fetch_idl` and cached locally. The directory is gitignored. If on-chain fetch fails, place the IDL file there manually.

## Key constants (txline/subscription.py)

| Name | Value |
|------|-------|
| Program ID | `9ExbZjAapQww1vfcisDmrngPinHTEfpjYRWMunJgcKaA` |
| TxL mint | `Zhw9TVKp68a1QrftncMSd6ELXKDtpVMNuMGr1jNwdeL` (Token-2022) |
| Free tier (delayed) | `SERVICE_LEVEL_FREE_DELAYED = 1` |
| Free tier (real-time) | `SERVICE_LEVEL_FREE_REALTIME = 12` |

## Sensitive files (all gitignored)

- `wallet.json` — Solana keypair; back up externally
- `.txline-credentials.json` — live JWT + API token
- `txline/idl/` — cached on-chain IDL

## Setup status

Wallet `B8Pp8mv1CjhfquSFwTmw3wu8pfyiRivWxaNCnXuavr9k` is funded (0.02 SOL). Credentials have **not** been activated yet.

### To continue on a new machine

1. Clone/copy this repo
2. Copy `wallet.json` across manually (it's gitignored — keep it secure)
3. Set up the venv: `python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"`
4. Confirm balance: `.venv/bin/python3 scripts/check_wallet.py`
5. Run the one-time activation: `.venv/bin/txline-subscribe`
6. Once `.txline-credentials.json` is created, the streams are ready to use
