"""환경 설정. 모든 비밀값은 환경변수에서 읽는다 (코드에 키를 박지 않음)."""

import os
from dataclasses import dataclass
from zoneinfo import ZoneInfo

KST = ZoneInfo("Asia/Seoul")
UTC = ZoneInfo("UTC")

# football-data.org 월드컵 대회 코드
FOOTBALL_DATA_COMPETITION = "WC"
FOOTBALL_DATA_BASE = "https://api.football-data.org/v4"

# FotMob 비공식 엔드포인트 (공식 지원 아님 — 깨질 수 있음).
# 실제 데이터 API는 /api/data/ 하위에 있다 (/api/matches 는 404 HTML 반환).
FOTMOB_BASE = "https://www.fotmob.com/api/data"


@dataclass(frozen=True)
class Settings:
    database_url: str
    football_data_token: str
    request_timeout: int = 15

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get(
                "DATABASE_URL",
                "postgresql://wc26:wc26@localhost:5432/wc26",
            ),
            football_data_token=os.environ.get("FOOTBALL_DATA_TOKEN", ""),
            request_timeout=int(os.environ.get("REQUEST_TIMEOUT", "15")),
        )


settings = Settings.from_env()
