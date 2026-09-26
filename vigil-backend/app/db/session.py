from sqlalchemy import create_engine
from sqlalchemy.dialects.mssql import UNIQUEIDENTIFIER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


@compiles(UNIQUEIDENTIFIER, "sqlite")
def compile_uniqueidentifier_sqlite(type_, compiler, **kw):
    return "CHAR(36)"


db_url = settings.DATABASE_URL.strip() if settings.DATABASE_URL else ""
if not db_url:
    db_url = "sqlite:///:memory:"

engine = create_engine(
    db_url,
    pool_pre_ping=True if not db_url.startswith("sqlite") else False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()