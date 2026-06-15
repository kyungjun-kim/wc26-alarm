# app 이미지: ingest / transform / api 잡이 공유하는 단일 이미지.
# 멀티스테이지로 의존성 레이어를 분리해 빌드 캐시를 살린다.
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# 의존성 먼저 (소스 변경 시 재설치 회피)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스
COPY src/ ./src/
COPY db/ ./db/
ENV PYTHONPATH=/app/src

# 기본 커맨드는 API. 잡 컨테이너는 command를 덮어쓴다.
EXPOSE 8000
CMD ["uvicorn", "wc26.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
