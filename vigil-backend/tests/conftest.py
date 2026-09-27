"""
Shared pytest fixtures for the Vigil backend test suite.

This conftest ensures that the SQLite database has all tables created
before any test module that uses the real app DB (via TestClient(app)).
"""
import pytest
from sqlalchemy import inspect

from app.db.session import engine
from app.db.base import Base


@pytest.fixture(autouse=True, scope="session")
def ensure_db_tables():
    """
    Ensure all SQLAlchemy models are reflected into the test database
    (the real vigil.db configured via DATABASE_URL) before any test runs.

    This is a no-op for in-memory SQLite fixtures that call
    Base.metadata.create_all themselves.
    """
    Base.metadata.create_all(bind=engine)
    yield
