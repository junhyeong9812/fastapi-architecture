# 프로덕션 빌드용 이미지
# docker compose에서 app 서비스가 이 파일로 빌드됨

FROM python:3.14-slim AS base
# python:3.14-slim: Debian 기반 경량 이미지 (alpine 대신 slim — C 확장 호환성)

WORKDIR /app

# 의존성 먼저 설치 (레이어 캐싱: 소스 변경해도 의존성 레이어는 재사용)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 복사
COPY src/ src/
COPY alembic/ alembic/
COPY alembic.ini .

EXPOSE 8000

# 기본 실행 명령 (docker compose에서 command로 오버라이드 가능)
CMD ["uvicorn", "src.app.main:app", "--host", "0.0.0.0", "--port", "8000"]