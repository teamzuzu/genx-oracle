"""CLI: txline-watch — live dashboard combining odds and scores streams."""

from dataclasses import dataclass

from txline.models import ScoreUpdate


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
