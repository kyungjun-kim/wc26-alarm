"""경기 추천도 점수 산정.

여러 요인의 가중합으로 0~100 점수를 내고, 직관적 라벨로 환산한다.
요인: 한국전 여부(최우선) · FIFA 랭킹 격차 · 토너먼트 단계 · 빅매치.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..rankings import get_rank, is_korea

# 단계별 가중치 (녹아웃 > 조별 최종전 > 조별 1·2차전)
STAGE_WEIGHT = {
    "FINAL": 40,
    "THIRD_PLACE": 20,
    "SEMI_FINALS": 35,
    "QUARTER_FINALS": 30,
    "LAST_16": 25,
    "LAST_32": 18,
    "GROUP_STAGE": 12,
}

KOREA_BONUS = 60  # 한국전이면 무조건 최상위로


@dataclass(frozen=True)
class ScoredMatch:
    score: int
    label: str


def _ranking_gap_points(home: str | None, away: str | None) -> float:
    """랭킹 격차가 작을수록(=명승부 가능성↑) 높은 점수. 최대 25."""
    gap = abs(get_rank(home) - get_rank(away))
    # gap 0 -> 25점, gap 49+ -> 0점에 수렴
    return max(0.0, 25.0 * (1 - gap / 49))


def _big_match_points(home: str | None, away: str | None) -> float:
    """양 팀 모두 상위 랭킹이면 빅매치 보너스. 최대 20."""
    top = max(get_rank(home), get_rank(away))  # 둘 중 더 낮은(나쁜) 랭킹
    if top <= 10:
        return 20.0
    if top <= 20:
        return 10.0
    return 0.0


def _stage_points(stage: str | None) -> float:
    return float(STAGE_WEIGHT.get(stage or "", STAGE_WEIGHT["GROUP_STAGE"]))


def score_match(home: str | None, away: str | None, stage: str | None) -> ScoredMatch:
    raw = (
        _stage_points(stage)
        + _ranking_gap_points(home, away)
        + _big_match_points(home, away)
    )
    if is_korea(home) or is_korea(away):
        raw += KOREA_BONUS

    score = int(min(100, round(raw)))
    return ScoredMatch(score=score, label=label_for(score))


def label_for(score: int) -> str:
    if score >= 80:
        return "🔥 새벽에 일어나서 볼 가치 충분"
    if score >= 55:
        return "👍 챙겨볼 만함"
    if score >= 30:
        return "⏩ 하이라이트로 충분"
    return "💤 스킵해도 OK"
