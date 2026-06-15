"""점수 산정 로직 테스트 (DB/네트워크 불필요)."""

from wc26.transform.score import label_for, score_match


def test_korea_match_is_top_priority():
    sm = score_match("Korea Republic", "Brazil", "GROUP_STAGE")
    assert sm.score >= 80
    assert "🔥" in sm.label


def test_final_between_top_teams_scores_high():
    sm = score_match("Argentina", "France", "FINAL")
    assert sm.score >= 80


def test_lopsided_group_game_scores_low():
    # 큰 랭킹 격차 + 조별 + 비빅매치
    sm = score_match("Germany", "Unknownland", "GROUP_STAGE")
    assert sm.score < 55


def test_label_thresholds():
    assert "🔥" in label_for(80)
    assert "👍" in label_for(55)
    assert "⏩" in label_for(30)
    assert "💤" in label_for(29)


def test_score_capped_at_100():
    sm = score_match("Korea Republic", "Argentina", "FINAL")
    assert sm.score <= 100
