"""
SQLAlchemy async 엔진 + 세션 팩토리

학습 포인트:
엔진(engine)은 DB 연결 풀이고, 세션(session)은 하나의 트랜잭션 단위다.
엔진은 앱 전체에서 1개, 세션은 요청마다 1개 생성된다.
이 생성 로직을 여기서 정의하고, 실제 주입은 DI 컨테이너가 한다.
"""

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.shared.config import AppConfig

def create_engine(config: AppConfig) -> AsyncEngine:
    """앱 전체에서 1개 생성되는 DB 연결 풀."""
    return create_async_engine(
        config.DATABASE_URL,
        echo=config.DEBUG,  #True면 실행되는 SQL을 콘솔에 출력
        pool_pre_ping=True, # 커넥션 사용 전 살아있는지 확인 (끊긴 연결 방지)
    )

def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """세션 팩토리. 이 팩토리로 요청마다 세션을 찍어낸다."""
    return async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,  # commit 후에도 객체 속성 접근 가능
        autocommit=False,
        autoflush=False,
    )