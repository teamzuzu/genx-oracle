"""CLI: txline-watch — live dashboard combining odds and scores streams."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path  # noqa: F401
from typing import Optional

import click  # noqa: F401
from rich.console import Console
from rich.live import Live
from rich.table import Table

from txline.client import TxLineClient
from txline.models import Fixture, Heartbeat, OddsUpdate, ScoreUpdate

console = Console()


@dataclass
class FixtureState:
    fixture_id: int
    name: str
    competition: str = "—"
    score: str = "—"
    game_state: str = "—"
    bookmaker: str = "—"
    market: str = "—"
    prices: str = "—"
    updated: str = ""


def parse_score(event: ScoreUpdate) -> str:
    if event.scoreSoccer:
        h = event.scoreSoccer.get("Home", event.scoreSoccer.get("home", "?"))
        a = event.scoreSoccer.get("Away", event.scoreSoccer.get("away", "?"))
        return f"{h} – {a}"
    if event.score:
        return str(event.score)
    return "—"


def build_table(state: dict[int, FixtureState]) -> Table:
    t = Table(title="TxLINE Live", show_lines=True)
    for col in ("Fixture", "Competition", "Score", "State",
                "Bookmaker", "Market", "Prices", "Updated"):
        t.add_column(col)
    for fs in sorted(state.values(), key=lambda x: x.fixture_id):
        t.add_row(
            fs.name,
            fs.competition,
            fs.score,
            fs.game_state,
            fs.bookmaker,
            fs.market,
            fs.prices,
            fs.updated,
        )
    return t


def apply_event(
    event: OddsUpdate | ScoreUpdate,
    state: dict[int, FixtureState],
    fixtures_cache: dict[int, Fixture],
    now: str,
) -> int:
    fid = event.FixtureId if isinstance(event, OddsUpdate) else event.fixtureId

    if fid not in state:
        state[fid] = FixtureState(fixture_id=fid, name=str(fid), updated=now)

    fs = state[fid]

    if fs.name == str(fid) and fid in fixtures_cache:
        fix = fixtures_cache[fid]
        fs.name = f"{fix.Participant1} vs {fix.Participant2}"
        fs.competition = fix.Competition

    if isinstance(event, OddsUpdate):
        fs.bookmaker = event.Bookmaker
        fs.market = event.SuperOddsType
        fs.prices = str(event.Prices) if event.Prices else "—"
    else:
        fs.score = parse_score(event)
        fs.game_state = event.gameState

    fs.updated = now
    return fid


async def _fetch_fixtures(
    client: TxLineClient,
    cache: dict[int, Fixture],
) -> None:
    try:
        for f in await client.fixtures():
            cache[f.FixtureId] = f
    except Exception:
        pass  # dashboard continues with raw fixture IDs


async def _odds_task(
    client: TxLineClient,
    fixture_id: Optional[int],
    queue: asyncio.Queue,
) -> None:
    async for event in client.odds(fixture_id=fixture_id):
        if not isinstance(event, Heartbeat):
            await queue.put(event)


async def _scores_task(
    client: TxLineClient,
    fixture_id: Optional[int],
    queue: asyncio.Queue,
) -> None:
    async for event in client.scores(fixture_id=fixture_id):
        if not isinstance(event, Heartbeat):
            await queue.put(event)


async def _run(client: TxLineClient, fixture_id: Optional[int]) -> None:
    state: dict[int, FixtureState] = {}
    fixtures_cache: dict[int, Fixture] = {}
    fixtures_fetching = False
    queue: asyncio.Queue[OddsUpdate | ScoreUpdate] = asyncio.Queue()
    _bg_tasks: set = set()

    async def _display_loop() -> None:
        nonlocal fixtures_fetching
        with Live(build_table(state), console=console, refresh_per_second=4) as live:
            while True:
                event = await queue.get()
                now = datetime.now().strftime("%H:%M:%S")
                apply_event(event, state, fixtures_cache, now)
                if not fixtures_fetching:
                    fixtures_fetching = True
                    t = asyncio.create_task(_fetch_fixtures(client, fixtures_cache))
                    _bg_tasks.add(t)
                    t.add_done_callback(_bg_tasks.discard)
                live.update(build_table(state))

    await asyncio.gather(
        _odds_task(client, fixture_id, queue),
        _scores_task(client, fixture_id, queue),
        _display_loop(),
    )
