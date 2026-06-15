"""FotMob 매칭 순수 로직 테스트 (네트워크 불필요)."""

from wc26.sources.fotmob import _extract_candidates, _extract_metrics, normalize_team, select_match_id


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


# 실제 FotMob /api/data/matches 응답 형태
def test_extract_candidates_real_shape():
    payload = {
        "leagues": [
            {
                "name": "World Cup",
                "matches": [
                    {"id": 4667765, "home": {"name": "Haiti"}, "away": {"name": "Scotland"}}
                ],
            }
        ]
    }
    assert _extract_candidates(payload) == [
        {"id": 4667765, "home": "Haiti", "away": "Scotland"}
    ]


# 실제 FotMob /api/data/matchDetails 의 stats 구조 (type:"title" 디코이 포함)
def test_extract_metrics_picks_scalar_xg_over_title_decoy():
    payload = {
        "content": {
            "stats": {
                "Periods": {
                    "All": {
                        "stats": [
                            {
                                "stats": [
                                    {"key": "ball_possession", "stats": ["55", "45"]},
                                    {
                                        "key": "expected_goals",
                                        "type": "text",
                                        "stats": ["1.05", "1.27"],
                                    },
                                ]
                            },
                            {
                                "stats": [
                                    {
                                        "key": "expected_goals",
                                        "type": "title",
                                        "stats": [None, None],
                                    }
                                ]
                            },
                        ]
                    }
                }
            }
        }
    }
    assert _extract_metrics(payload) == {"home_xg": 1.05, "away_xg": 1.27}


def test_extract_metrics_missing_returns_none():
    assert _extract_metrics({}) == {"home_xg": None, "away_xg": None}
