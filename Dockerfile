# 프로덕션 빌드용 이미지 (Phase 6 — multi-stage)
# docker compose에서 app 서비스가 이 파일로 빌드됨

# Stage 1: 의존성만 설치 (빌드 도구는 최종 이미지에 남기지 않음)
FROM python:3.14-slim AS builder
WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# Stage 2: 런타임 (builder에서 설치한 것만 복사 → 최종 이미지 가벼움)
FROM python:3.14-slim
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .
COPY gunicorn.conf.py .

EXPOSE 8000

# 프로덕션 실행: gunicorn + uvicorn worker × 4
# (개발 환경은 docker-compose.yml에서 uvicorn --reload로 오버라이드됨)
CMD ["gunicorn", "src.app.main:app", \
     "-c", "gunicorn.conf.py"]
