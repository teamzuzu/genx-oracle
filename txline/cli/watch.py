"""CLI: txline-watch — live dashboard combining odds and scores streams."""

import asyncio  # noqa: F401
from dataclasses import dataclass
from datetime import datetime  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Optional  # noqa: F401

import click  # noqa: F401
from rich.console import Console  # noqa: F401
from rich.live import Live  # noqa: F401
from rich.table import Table

from txline.client import TxLineClient  # noqa: F401
from txline.models import ScoreUpdate
from txline.models import Fixture, OddsUpdate


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
