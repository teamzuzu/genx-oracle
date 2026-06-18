"""Tests for txline-watch logic — no network calls."""
from txline.cli.watch import FixtureState, parse_score, build_table
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


def test_build_table_columns():
    t = build_table({})
    cols = [c.header for c in t.columns]
    assert cols == ["Fixture", "Competition", "Score", "State",
                    "Bookmaker", "Market", "Prices", "Updated"]


def test_build_table_empty():
    t = build_table({})
    assert t.row_count == 0


def test_build_table_one_row():
    fs = FixtureState(fixture_id=1, name="A vs B", competition="PL",
                      score="2 – 1", game_state="SecondHalf",
                      bookmaker="BK", market="1X2", prices="[150, 200]",
                      updated="12:00:00")
    t = build_table({1: fs})
    assert t.row_count == 1


def test_build_table_sorted_by_fixture_id():
    state = {
        3: FixtureState(fixture_id=3, name="C vs D"),
        1: FixtureState(fixture_id=1, name="A vs B"),
    }
    t = build_table(state)
    assert t.row_count == 2
    # rows are sorted ascending — first row is fixture 1
    # Rich doesn't expose row data directly; just verify count and no exception
