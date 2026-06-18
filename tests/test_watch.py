"""Tests for txline-watch logic — no network calls."""
from txline.cli.watch import FixtureState, parse_score
from txline.models import ScoreUpdate


def _score_update(**kwargs) -> ScoreUpdate:
    defaults = dict(
        fixtureId=1, gameState="FirstHalf", startTime=0, participant1Id=10,
        participant2Id=20, competitionId=5, countryId=1, sportId=1,
        fixtureGroupId=1, isTeam=True, participant1IsHome=True,
        action="Goal", id="abc", ts=0, connectionId="x", seq=1,
    )
    return ScoreUpdate(**{**defaults, **kwargs})


def test_parse_score_soccer_title_case():
    ev = _score_update(scoreSoccer={"Home": 2, "Away": 1})
    assert parse_score(ev) == "2 – 1"


def test_parse_score_soccer_lower_case():
    ev = _score_update(scoreSoccer={"home": 0, "away": 0})
    assert parse_score(ev) == "0 – 0"


def test_parse_score_fallback_to_score():
    ev = _score_update(score={"total": 3})
    assert parse_score(ev) == "{'total': 3}"


def test_parse_score_empty():
    ev = _score_update()
    assert parse_score(ev) == "—"


def test_fixture_state_defaults():
    fs = FixtureState(fixture_id=99, name="99")
    assert fs.competition == "—"
    assert fs.score == "—"
    assert fs.game_state == "—"
    assert fs.bookmaker == "—"
    assert fs.market == "—"
    assert fs.prices == "—"
    assert fs.updated == ""
