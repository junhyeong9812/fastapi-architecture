"""Alembic 마이그레이션 환경 설정.

핵심:
- async 엔진을 사용하므로 일반적인 Alembic env.py와 다름
- 모든 모듈의 ORM 모델을 여기서 import해야 autogenerate가 테이블을 인식함
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Base.metadata에 모든 테이블 정보가 모인다
from app.shared.base_model import Base

# ★ 각 모듈의 ORM 모델을 import — 이래야 Alembic이 테이블을 인식
# Phase 1
from app.orders.infrastructure.models import OrderModel, OrderItemModel  # noqa: F401
from app.subscriptions.infrastructure.models import SubscriptionModel  # noqa: F401
# Phase 2에서 추가: from app.payments.infrastructure.models import ...
# Phase 3에서 추가: from app.shipping.infrastructure.models import ...
# Phase 4에서 추가: from app.tracking.infrastructure.models import ...

config = context.config

# alembic.ini의 로깅 설정 적용
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# autogenerate가 이 metadata를 기준으로 diff를 계산
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """오프라인 모드: DB 연결 없이 SQL만 생성"""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """실제 마이그레이션 실행 (sync connection에서 호출됨)"""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """async 엔진으로 마이그레이션 실행하는 핵심 함수"""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # 마이그레이션은 단발 작업이므로 풀링 불필요
    )
    async with connectable.connect() as connection:
        # run_sync: async connection에서 sync 함수를 실행하는 SQLAlchemy 유틸
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """온라인 모드: asyncio.run으로 async 마이그레이션 실행"""
    asyncio.run(run_async_migrations())


# Alembic이 호출하는 엔트리포인트
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()