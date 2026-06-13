# FastAPI SSE Proxy Server Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone FastAPI service that proxies TxLINE odds/scores SSE streams and fixture snapshots to browser clients.

**Architecture:** A `create_app(creds)` factory builds the FastAPI app with CORS and three endpoints. A `cli()` entry point loads credentials from disk and runs uvicorn. Tests use `httpx.AsyncClient` with `ASGITransport` to exercise the app without any network I/O.

**Tech Stack:** FastAPI, uvicorn[standard], sse-starlette, httpx (ASGI transport for tests), pytest-asyncio

---

### Task 1: Add dependencies and entry point

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update dependencies and scripts in pyproject.toml**

In the `[project]` section, replace `dependencies` with:

```toml
dependencies = [
    "httpx>=0.27",
    "httpx-sse>=0.4",
    "pydantic>=2.7",
    "pynacl>=1.5",
    "python-dotenv>=1.0",
    "solders>=0.21",
    "anchorpy>=0.20",
    "click>=8.1",
    "rich>=13.0",
    "fastapi>=0.111",
    "uvicorn[standard]>=0.29",
    "sse-starlette>=1.6",
]
```

Replace `[project.scripts]` with:

```toml
[project.scripts]
txline-subscribe = "txline.cli.subscribe:main"
txline-stream = "txline.cli.stream:main"
txline-server = "txline.api.server:cli"
```

- [ ] **Step 2: Install updated dependencies**

```bash
.venv/bin/pip install -e ".[dev]"
```

Expected: packages install without errors.

- [ ] **Step 3: Verify imports**

```bash
.venv/bin/python -c "import fastapi, uvicorn, sse_starlette; print('ok')"
```

Expected: `ok`

---

### Task 2: Create server with /fixtures endpoint (TDD)

**Files:**
- Create: `txline/api/__init__.py`
- Create: `txline/api/server.py`
- Create: `tests/__init__.py`
- Create: `tests/test_api_server.py`

- [ ] **Step 1: Create empty init files**

Create `txline/api/__init__.py` — empty file.
Create `tests/__init__.py` — empty file.

- [ ] **Step 2: Write failing tests**

Create `tests/test_api_server.py`:

```python
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from txline.api.server import create_app
from txline.models import Fixture, OddsUpdate, ScoreUpdate, Heartbeat, TokenCredentials


@pytest.fixture
def creds():
    return TokenCredentials(jwt="test-jwt", api_token="test-token")


@pytest.fixture
def app(creds):
    return create_app(creds)


FIXTURE_1 = Fixture(
    Ts=1000, StartTime=1781830800000, Competition="World Cup",
    CompetitionId=1, FixtureGroupId=1, Participant1Id=1,
    Participant1="Mexico", Participant2Id=2, Participant2="South Korea",
    FixtureId=17588223, Participant1IsHome=True,
)


async def test_fixtures_returns_list(app):
    with patch("txline.api.server.get_fixtures", new=AsyncMock(return_value=[FIXTURE_1])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/fixtures")
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 1
    assert data[0]["FixtureId"] == 17588223
    assert data[0]["Competition"] == "World Cup"


async def test_fixtures_passes_credentials(app):
    captured = {}

    async def mock_get_fixtures(http, jwt, api_token, **kwargs):
        captured["jwt"] = jwt
        captured["api_token"] = api_token
        return []

    with patch("txline.api.server.get_fixtures", new=mock_get_fixtures):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            await c.get("/fixtures")

    assert captured["jwt"] == "test-jwt"
    assert captured["api_token"] == "test-token"
```

- [ ] **Step 3: Run to confirm failure**

```bash
.venv/bin/pytest tests/test_api_server.py -v
```

Expected: `ModuleNotFoundError: No module named 'txline.api'`

- [ ] **Step 4: Create txline/api/server.py**

```python
"""Standalone FastAPI service — proxies TxLINE data to browser clients via SSE."""

import json
import logging
from pathlib import Path
from typing import Optional

import click
import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from txline.auth import load_credentials
from txline.models import Heartbeat, TokenCredentials
from txline.rest.fixtures import get_fixtures
from txline.streams.odds import stream_odds
from txline.streams.scores import stream_scores

logger = logging.getLogger(__name__)
DEFAULT_CREDS = Path(".txline-credentials.json")


def create_app(creds: TokenCredentials) -> FastAPI:
    app = FastAPI(title="TxLINE Proxy")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/fixtures")
    async def fixtures_endpoint():
        async with httpx.AsyncClient() as http:
            return await get_fixtures(http, creds.jwt, creds.api_token)

    return app


@click.command()
@click.option("--credentials", default=str(DEFAULT_CREDS), show_default=True)
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8000, show_default=True)
def cli(credentials: str, host: str, port: int) -> None:
    """Run the TxLINE SSE proxy server."""
    creds = load_credentials(Path(credentials))
    if creds is None:
        raise click.ClickException(
            f"No credentials at {credentials}. Run `txline-subscribe` first."
        )
    uvicorn.run(create_app(creds), host=host, port=port)
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
.venv/bin/pytest tests/test_api_server.py -v
```

Expected: `2 passed`

- [ ] **Step 6: Commit**

```bash
git add txline/api/__init__.py txline/api/server.py tests/__init__.py tests/test_api_server.py pyproject.toml
git commit -m "feat: add FastAPI proxy server with /fixtures endpoint"
```

---

### Task 3: Add /odds/stream SSE endpoint (TDD)

**Files:**
- Modify: `txline/api/server.py`
- Modify: `tests/test_api_server.py`

- [ ] **Step 1: Append failing tests to tests/test_api_server.py**

```python
async def test_odds_stream_sse_format(app):
    async def mock_odds(jwt, api_token, fixture_id=None, last_event_id=None):
        yield OddsUpdate(
            FixtureId=1, MessageId="m1", Ts=1000, Bookmaker="bet365",
            BookmakerId=1, SuperOddsType="1x2", InRunning=False,
        )
        yield Heartbeat(Ts=2000)

    with patch("txline.api.server.stream_odds", new=mock_odds):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", "/odds/stream") as r:
                assert r.status_code == 200
                assert "text/event-stream" in r.headers["content-type"]
                content = b""
                async for chunk in r.aiter_bytes():
                    content += chunk

    text = content.decode()
    assert "event: odds" in text
    assert '"FixtureId":1' in text
    assert "event: heartbeat" in text


async def test_odds_stream_fixture_id_passthrough(app):
    captured = {}

    async def mock_odds(jwt, api_token, fixture_id=None, last_event_id=None):
        captured["fixture_id"] = fixture_id
        yield Heartbeat(Ts=1000)

    with patch("txline.api.server.stream_odds", new=mock_odds):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", "/odds/stream?fixtureId=42") as r:
                async for _ in r.aiter_bytes():
                    pass

    assert captured["fixture_id"] == 42
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/pytest tests/test_api_server.py::test_odds_stream_sse_format tests/test_api_server.py::test_odds_stream_fixture_id_passthrough -v
```

Expected: `404 Not Found` (route does not exist yet)

- [ ] **Step 3: Add /odds/stream to create_app() in txline/api/server.py**

Inside `create_app()`, add after `fixtures_endpoint` and before `return app`:

```python
    async def _odds_events(fixture_id: Optional[int]):
        async for event in stream_odds(creds.jwt, creds.api_token, fixture_id=fixture_id):
            if isinstance(event, Heartbeat):
                yield {"event": "heartbeat", "data": json.dumps({"Ts": event.Ts})}
            else:
                yield {"event": "odds", "data": event.model_dump_json()}

    @app.get("/odds/stream")
    async def odds_stream(fixture_id: Optional[int] = None):
        return EventSourceResponse(_odds_events(fixture_id))
```

- [ ] **Step 4: Run all tests**

```bash
.venv/bin/pytest tests/test_api_server.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add txline/api/server.py tests/test_api_server.py
git commit -m "feat: add /odds/stream SSE passthrough endpoint"
```

---

### Task 4: Add /scores/stream SSE endpoint (TDD)

**Files:**
- Modify: `txline/api/server.py`
- Modify: `tests/test_api_server.py`

- [ ] **Step 1: Append failing tests to tests/test_api_server.py**

```python
async def test_scores_stream_sse_format(app):
    async def mock_scores(jwt, api_token, fixture_id=None, last_event_id=None):
        yield ScoreUpdate(
            fixtureId=99, gameState="active", startTime=1000,
            participant1Id=1, participant2Id=2, competitionId=1,
            countryId=1, sportId=1, fixtureGroupId=1,
            isTeam=True, participant1IsHome=True,
            action="goal", id="s1", ts=1000,
            connectionId="conn1", seq=1,
        )
        yield Heartbeat(Ts=3000)

    with patch("txline.api.server.stream_scores", new=mock_scores):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", "/scores/stream") as r:
                assert r.status_code == 200
                assert "text/event-stream" in r.headers["content-type"]
                content = b""
                async for chunk in r.aiter_bytes():
                    content += chunk

    text = content.decode()
    assert "event: scores" in text
    assert '"fixtureId":99' in text
    assert "event: heartbeat" in text


async def test_scores_stream_fixture_id_passthrough(app):
    captured = {}

    async def mock_scores(jwt, api_token, fixture_id=None, last_event_id=None):
        captured["fixture_id"] = fixture_id
        yield Heartbeat(Ts=1000)

    with patch("txline.api.server.stream_scores", new=mock_scores):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            async with c.stream("GET", "/scores/stream?fixtureId=7") as r:
                async for _ in r.aiter_bytes():
                    pass

    assert captured["fixture_id"] == 7
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/bin/pytest tests/test_api_server.py::test_scores_stream_sse_format tests/test_api_server.py::test_scores_stream_fixture_id_passthrough -v
```

Expected: `404 Not Found`

- [ ] **Step 3: Add /scores/stream to create_app() in txline/api/server.py**

Inside `create_app()`, add after `odds_stream` and before `return app`:

```python
    async def _scores_events(fixture_id: Optional[int]):
        async for event in stream_scores(creds.jwt, creds.api_token, fixture_id=fixture_id):
            if isinstance(event, Heartbeat):
                yield {"event": "heartbeat", "data": json.dumps({"Ts": event.Ts})}
            else:
                yield {"event": "scores", "data": event.model_dump_json()}

    @app.get("/scores/stream")
    async def scores_stream(fixture_id: Optional[int] = None):
        return EventSourceResponse(_scores_events(fixture_id))
```

- [ ] **Step 4: Run all tests**

```bash
.venv/bin/pytest tests/test_api_server.py -v
```

Expected: `6 passed`

- [ ] **Step 5: Commit**

```bash
git add txline/api/server.py tests/test_api_server.py
git commit -m "feat: add /scores/stream SSE passthrough endpoint"
```

---

### Task 5: CORS and missing-credentials tests

**Files:**
- Modify: `tests/test_api_server.py`

- [ ] **Step 1: Append tests to tests/test_api_server.py**

```python
async def test_cors_header_present(app):
    with patch("txline.api.server.get_fixtures", new=AsyncMock(return_value=[])):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.get("/fixtures", headers={"Origin": "https://example.com"})
    assert r.headers.get("access-control-allow-origin") == "*"


def test_cli_exits_on_missing_credentials(tmp_path):
    from click.testing import CliRunner
    from txline.api.server import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--credentials", str(tmp_path / "nope.json")])
    assert result.exit_code != 0
    assert "No credentials" in result.output
```

- [ ] **Step 2: Run all tests**

```bash
.venv/bin/pytest tests/test_api_server.py -v
```

Expected: `8 passed`

- [ ] **Step 3: Commit**

```bash
git add tests/test_api_server.py
git commit -m "test: add CORS and missing-credentials coverage"
```

---

### Task 6: Smoke test the running server

- [ ] **Step 1: Start the server**

```bash
.venv/bin/txline-server
```

Expected output (uvicorn startup):
```
INFO:     Started server process [...]
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to stop)
```

- [ ] **Step 2: Verify /fixtures in a second terminal**

```bash
curl -s http://localhost:8000/fixtures | python3 -m json.tool | head -20
```

Expected: JSON array of fixture objects.

- [ ] **Step 3: Verify /odds/stream**

```bash
curl -N http://localhost:8000/odds/stream
```

Expected: SSE events flowing, e.g.:
```
event: odds
data: {"FixtureId":17588223,...}

event: heartbeat
data: {"Ts":...}
```

- [ ] **Step 4: Stop server and update CLAUDE.md**

Add to the Commands section in `CLAUDE.md`:

```bash
# Server
.venv/bin/txline-server                          # start FastAPI proxy (port 8000)
.venv/bin/txline-server --port 9000              # custom port
```

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add txline-server usage to CLAUDE.md"
```
