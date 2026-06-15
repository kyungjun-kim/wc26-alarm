# Airflow 이미지: 공식 이미지 + wc26 패키지 의존성.
# DAG가 wc26.pipeline을 import하므로 런타임 의존성을 함께 설치한다.
FROM apache/airflow:2.9.2-python3.11

COPY requirements.txt /requirements.txt
RUN pip install --no-cache-dir -r /requirements.txt

# 패키지 소스는 docker-compose/k8s에서 /opt/wc26/src 로 마운트하고
# PYTHONPATH 에 추가한다 (이미지에 굽지 않아 개발 중 반영이 빠름).
ENV PYTHONPATH=/opt/wc26/src
