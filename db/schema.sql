-- wc26-alarm 스키마
-- raw_matches: football-data.org 원본 (안정적 기반)
-- match_metrics: FotMob 보강 지표 (선택)
-- scored_matches: 점수/라벨 (transform 결과)
-- tonight_view: 서빙용 KST 뷰

CREATE TABLE IF NOT EXISTS raw_matches (
    match_id     BIGINT PRIMARY KEY,
    utc_kickoff  TIMESTAMPTZ NOT NULL,
    stage        TEXT,
    group_name   TEXT,
    status       TEXT,
    home_team    TEXT,
    away_team    TEXT,
    home_score   INT,
    away_score   INT,
    ingested_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_raw_matches_kickoff ON raw_matches (utc_kickoff);

CREATE TABLE IF NOT EXISTS match_metrics (
    match_id  BIGINT PRIMARY KEY REFERENCES raw_matches (match_id) ON DELETE CASCADE,
    home_xg   REAL,
    away_xg   REAL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS scored_matches (
    match_id     BIGINT PRIMARY KEY REFERENCES raw_matches (match_id) ON DELETE CASCADE,
    score        INT NOT NULL,
    label        TEXT NOT NULL,
    computed_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 서빙 뷰: 경기 + 점수를 합쳐 KST 킥오프와 함께 노출
CREATE OR REPLACE VIEW tonight_view AS
SELECT
    r.match_id,
    r.utc_kickoff,
    r.utc_kickoff AT TIME ZONE 'Asia/Seoul' AS kst_kickoff,
    r.stage,
    r.group_name,
    r.status,
    r.home_team,
    r.away_team,
    r.home_score,
    r.away_score,
    s.score,
    s.label
FROM raw_matches r
LEFT JOIN scored_matches s USING (match_id);
