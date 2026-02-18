"""
환경 설정 관리.

pydantic-settings를 사용하여 .env 파일이나 환경변수를 자동으로 읽는다.
docker-compose.yml의 environment에 설정한 값이 여기로 들어온다.
"""

from pydantic_settings import BaseSettings

class AppConfig(BaseSettings):
    # 프로젝트 기본 정보
    PROJECT_NAME: str = "ShopTracker"
    ENV: str = "dev"                    # dev/ prod
    DEBUG: bool = False                 # True면 SQLAlchemy SQL 로그 출력

    # DB 연결 URL - docker-compose.yml의 DATABASE_URL 환경변수가 이 값을 덮어씀
    DATABASE_URL: str = (
        "postgresql+asyncpg://shoptracker:shoptracker@Localhost:5432/shoptracker"
    )

    # pydantic-settings 설정: .env 파일이 있으면 거기서도 읽음
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

def get_config() -> AppConfig:
    """팩토리 함수, DI 컨테이너에서 이걸 호출하여 설정 객체를 생성한다."""
    return AppConfig()