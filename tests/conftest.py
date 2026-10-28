import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.database import engine
from app.main import app


@pytest.fixture
def client():
    # Entering the client runs the app's startup, which creates the tables.
    with TestClient(app) as client:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE books"))
        yield client
