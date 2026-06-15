# wc26-alarm

> 2026 월드컵, 새벽에 알람 맞출 가치가 있는 경기를 골라주는 큐레이터

## 개요

2026 월드컵은 미주(미국·캐나다·멕시코) 개최라, 한국에선 경기 대부분이 **새벽~아침**에 열립니다. 6주간 104경기 — 다 챙겨볼 수는 없습니다.

그래서 필요한 건 일정표가 아니라 **"새벽 4시에 알람 맞출 가치가 있는 경기"를 골라주는 도구**입니다. `wc26-alarm` 은 딱 하나의 질문에 답합니다:

### 오늘 밤, 뭘 챙겨봐야 하나?

각 경기를 한국 시간(KST) 기준으로 보여주고, 중요도를 점수화해 직관적인 라벨로 환산합니다.

| 점수 | 라벨 |
| --- | --- |
| 80+ | 🔥 새벽에 일어나서 볼 가치 충분 |
| 55–79 | 👍 챙겨볼 만함 |
| 30–54 | ⏩ 하이라이트로 충분 |
| <30 | 💤 스킵해도 OK |

## 데이터 소스

비용을 최소화하기 위해 무료·저렴한 소스를 조합합니다.

| 데이터 | 소스 | 비용 |
| --- | --- | --- |
| 경기 일정 · 킥오프 · 조편성 · 녹아웃 단계 | football-data.org | 무료 (10 req/분) |
| 라이브 스코어 · xG 등 상세 지표 | FotMob (비공식 엔드포인트) | 무료 |
| FIFA 랭킹 (랭킹 격차 점수용) | 대회 시작 시점 스냅샷 (`src/wc26/rankings.py`) | 정적 |

- **football-data.org** 를 안정적인 기반으로 사용해 일정·단계 데이터를 받습니다.
- **FotMob** 은 비공식 API라 깨질 수 있어 보조 지표 보강용으로만 쓰고, 실패해도 핵심 기능엔 영향이 없도록 graceful하게 처리합니다. `enrich` 단계가 진행/종료된 경기를 팀명·날짜로 FotMob(`/api/data/matches`·`/api/data/matchDetails`)과 매칭(`src/wc26/sources/fotmob.py`)해 xG를 `match_metrics`에 적재하며, 매칭 실패나 엔드포인트 변경 시 조용히 건너뜁니다.
- **FIFA 랭킹** 은 대회 중 변하지 않으므로 스냅샷을 정적 데이터로 둡니다.

## 아키텍처

단순 웹앱이 아니라 작은 **데이터 플랫폼**으로 구성합니다 — 수집 → 저장 → 변환 → 서빙.

```
 [Ingestion]                [Storage]            [Transform]           [Serving]
 football-data.org ──┐                                                 FastAPI
   (일정·단계)        ├──▶  PostgreSQL  ──▶  점수 산정(score.py) ──▶   GET /api/tonight
 FotMob (xG, 보강) ──┘     raw_matches        scored_matches           + 오늘 밤 화면
                          match_metrics       tonight_view (KST)
                                  ▲
                  Airflow DAG: ingest → transform → enrich → publish
                          (또는 K8s CronJob)
```

| 계층 | 기술 | 위치 |
| --- | --- | --- |
| Ingestion | Python (requests) | `src/wc26/sources/` |
| Storage | PostgreSQL | `db/schema.sql` |
| Transform | Python (가중합 점수) | `src/wc26/transform/score.py` |
| Orchestration | Airflow (TaskFlow DAG) | `dags/wc26_pipeline.py` |
| Serving | FastAPI + 정적 프론트 | `src/wc26/api/` |
| Container / Deploy | Docker · Docker Compose · Kubernetes | `docker/`, `docker-compose.yml`, `k8s/` |

### API

| 엔드포인트 | 설명 |
| --- | --- |
| `GET /api/tonight?hours=24&min_score=0` | 지금(KST)부터 `hours`시간 내 경기, 점수순. `min_score`로 하한 필터 |
| `GET /api/day/{YYYY-MM-DD}?min_score=0` | 특정 KST 날짜의 모든 경기, 점수순 |
| `GET /healthz` | 헬스체크 |
| `GET /` | "오늘 밤" 화면 (정적 프론트, 이전/다음 날 네비게이션) |

각 경기 응답에는 FotMob 보강이 있으면 `home_xg`/`away_xg`가 포함됩니다(없으면 `null`). 프론트는 xG가 있을 때만 표시합니다.

### 점수 산정 (`transform/score.py`)

추천도는 여러 요인의 가중합(0~100)입니다.

- **한국전 여부** — 무조건 최우선 (+60)
- **FIFA 랭킹 격차** — 격차가 작을수록 명승부 가능성 ↑ (최대 +25)
- **토너먼트 단계** — 녹아웃 > 조별 최종전 > 조별 1·2차전
- **빅매치** — 양 팀 모두 상위 랭킹이면 보너스 (최대 +20)

## 실행

### 사전 준비

football-data.org에서 [무료 키를 발급](https://www.football-data.org/client/register)받아 환경변수에 넣습니다.

```bash
cp .env.example .env
# .env 의 FOOTBALL_DATA_TOKEN 채우기
```

> 키가 없어도 스키마·점수 로직·프론트는 동작하지만, 실제 경기 일정은 비어 있습니다.

### 로컬 (Docker Compose)

```bash
docker compose up -d                                   # postgres + api + airflow
docker compose exec api python -m wc26.run all         # ingest → transform → publish
curl localhost:8000/api/tonight                        # JSON 확인
# 브라우저: http://localhost:8000  (오늘 밤 화면)
#           http://localhost:8080  (Airflow UI)
```

스키마는 Postgres 최초 기동 시 `db/schema.sql`로 자동 적용됩니다 (수동 적용은 `python -m wc26.run initdb`).

### 단위 테스트

```bash
pip install -e ".[dev]"
pytest tests/
```

### Kubernetes

```bash
docker build -f docker/app.Dockerfile -t wc26-alarm-app:latest .
kubectl apply -f k8s/
# Secret에 실제 토큰 주입
kubectl -n wc26 create secret generic wc26-secrets \
  --from-literal=FOOTBALL_DATA_TOKEN=<발급받은_토큰> \
  --dry-run=client -o yaml | kubectl apply -f -
# 파이프라인 수동 1회 실행
kubectl -n wc26 create job --from=cronjob/wc26-pipeline manual-run
kubectl -n wc26 port-forward svc/api 8000:80           # http://localhost:8000
```

파이프라인 스케줄은 클러스터에선 **K8s CronJob**(`k8s/40-pipeline-cronjob.yaml`), 로컬에선 **Airflow**가 담당합니다 — 둘 중 하나만 활성화하면 됩니다.
