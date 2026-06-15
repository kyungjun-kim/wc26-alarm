"""FotMob 매칭 순수 로직 테스트 (네트워크 불필요)."""

from wc26.sources.fotmob import normalize_team, select_match_id


def test_normalize_applies_aliases_and_punctuation():
    assert normalize_team("Korea Republic") == "south korea"
    assert normalize_team("IR Iran") == "iran"
    assert normalize_team("Côte d'Ivoire") == "ivory coast"
    assert normalize_team("United States") == "united states"


CANDIDATES = [
    {"id": 100, "home": "South Korea", "away": "Brazil"},
    {"id": 200, "home": "France", "away": "Argentina"},
]


def test_select_resolves_across_naming_difference():
    # football-data 표기 "Korea Republic" -> FotMob "South Korea"
    assert select_match_id(CANDIDATES, "Korea Republic", "Brazil") == 100


def test_select_matches_regardless_of_home_away_order():
    assert select_match_id(CANDIDATES, "Argentina", "France") == 200


def test_select_returns_none_when_absent():
    assert select_match_id(CANDIDATES, "Germany", "Spain") is None


def test_select_returns_none_on_missing_team():
    assert select_match_id(CANDIDATES, None, "Brazil") is None
