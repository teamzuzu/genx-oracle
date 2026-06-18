"""CLI: txline-watch — live dashboard combining odds and scores streams."""

import asyncio  # noqa: F401
from dataclasses import dataclass
from datetime import datetime  # noqa: F401
from pathlib import Path  # noqa: F401
from typing import Optional  # noqa: F401

import click  # noqa: F401
from rich.console import Console  # noqa: F401
from rich.live import Live  # noqa: F401
from rich.table import Table  # noqa: F401

from txline.client import TxLineClient  # noqa: F401
from txline.models import ScoreUpdate
from txline.models import Fixture, Heartbeat, OddsUpdate  # noqa: F401


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
