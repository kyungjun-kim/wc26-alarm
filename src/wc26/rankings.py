"""FIFA 랭킹 정적 스냅샷.

랭킹은 대회 중 변하지 않으므로 외부 API 대신 대회 시작 시점 스냅샷을 둔다.
값은 대회 직전 FIFA 랭킹 기준의 대표 스냅샷이며, 정확한 최종 수치는 갱신 필요.
"""

# 팀명(영문) -> FIFA 랭킹. football-data.org 팀명 표기에 맞춘다.
FIFA_RANKING: dict[str, int] = {
    "Argentina": 1,
    "France": 2,
    "Spain": 3,
    "England": 4,
    "Brazil": 5,
    "Portugal": 6,
    "Netherlands": 7,
    "Belgium": 8,
    "Italy": 9,
    "Germany": 10,
    "Croatia": 11,
    "Morocco": 12,
    "Colombia": 13,
    "Uruguay": 14,
    "United States": 15,
    "Mexico": 16,
    "Switzerland": 17,
    "Senegal": 18,
    "Japan": 19,
    "Denmark": 20,
    "Iran": 21,
    "Korea Republic": 22,
    "Australia": 23,
    "Ecuador": 24,
    "Austria": 25,
    "Canada": 26,
    "Poland": 27,
    "Egypt": 28,
    "Nigeria": 29,
    "Serbia": 30,
    "Wales": 31,
    "Norway": 32,
}

# 한국 팀 식별 (football-data.org 표기)
KOREA_TEAM_NAMES = {"Korea Republic", "South Korea"}

DEFAULT_RANK = 50  # 스냅샷에 없는 팀 (예선 통과 약체 등)


def get_rank(team_name: str | None) -> int:
    if not team_name:
        return DEFAULT_RANK
    return FIFA_RANKING.get(team_name, DEFAULT_RANK)


def is_korea(team_name: str | None) -> bool:
    return team_name in KOREA_TEAM_NAMES if team_name else False
