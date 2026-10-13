import os
import tempfile

# Point the app at a throwaway database BEFORE importing it.
_tmpdir = tempfile.mkdtemp(prefix="vulatrust-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import models  # noqa: E402,F401  (registers the tables)
from app.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
