"""Shared test database for the whole suite.

One in-memory SQLite engine serves every test module, so the
dependency override registered here is the single source of truth.
User emails must be unique across modules (prefix per module).
"""
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core import security
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base.metadata.create_all(engine)


def override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def make_user(email: str, password: str, role: UserRole, active: bool = True) -> int:
    db = TestingSession()
    user = User(
        full_name=email.split("@")[0].replace(".", " ").title(),
        email=email,
        password_hash=security.hash_password(password),
        role=role,
        is_active=active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    uid = user.id
    db.close()
    return uid


def login_token(email: str, password: str) -> str:
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
