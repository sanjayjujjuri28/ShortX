import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# Set test environment before importing app modules
os.environ["DATABASE_URL"] = "sqlite:///./test_shortx.db"
os.environ["SECRET_KEY"] = "test-secret-key-32chars-minimum-length-security"
os.environ["RATE_LIMIT_REQUESTS"] = "5"
os.environ["RATE_LIMIT_WINDOW_SECONDS"] = "60"

from app.database import Base, get_db

from app.main import app
from app.redis import reset_redis_client, InMemoryFallbackRedis

# Setup test DB engine
TEST_DATABASE_URL = "sqlite:///./test_shortx.db"
test_engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)
    if os.path.exists("./test_shortx.db"):
        try:
            os.remove("./test_shortx.db")
        except Exception:
            pass


@pytest.fixture(autouse=True)
def clean_redis_and_db():
    # Fresh isolated in-memory redis per test
    fake_redis = InMemoryFallbackRedis()
    reset_redis_client(fake_redis)
    yield
    fake_redis.flushdb()


@pytest.fixture
def db_session():
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    # Create test user and obtain auth headers
    email = "tester@shortx.io"
    password = "password123"
    client.post("/auth/signup", json={"email": email, "password": password})
    res = client.post("/auth/login", json={"email": email, "password": password})
    token = res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
