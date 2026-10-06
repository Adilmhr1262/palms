from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

_engine = None
_SessionLocal = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(settings.database_url, pool_pre_ping=True)
    return _engine


def get_session_factory():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(), autoflush=False, autocommit=False
        )
    return _SessionLocal


def get_db():
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()
