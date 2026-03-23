"""SQLAlchemy DeclarativeBase.

모든 ORM 모델이 이 Base를 상속한다.
Base.metadata에 모든 테이블 정보가 자동으로 모인다.
Alembic은 이 metadata를 읽어서 DB 스키마 변경을 감지한다.

Spring의 @Entity가 붙은 클래스들이 자동으로 스캔되는 것과 비슷한 원리.
"""

from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass