"""CLI: txline-watch — live dashboard combining odds and scores streams."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.live import Live
from rich.table import Table

from txline.client import TxLineClient
from txline.models import Fixture, Heartbeat, OddsUpdate, ScoreUpdate


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
