"""Step 2 security verification: hashing, JWT, RBAC, login rules."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from tests.conftest import auth_headers, client, login_token, make_user, TestingSession
from app.core import security
from app.models.user import User
from app.core import security
from app.core.config import settings
from app.models.user import UserRole


def login(email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


@pytest.fixture(scope="module")
def admin_id():
    return make_user("admin@palms.edu", "adminpass1", UserRole.admin)


@pytest.fixture(scope="module")
def teacher_id():
    return make_user("teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student_id():
    return make_user("student@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def inactive_id():
    return make_user("off@palms.edu", "inactivepass1", UserRole.student, active=False)


def login(email, password):
    return client.post("/api/v1/auth/login", json={"email": email, "password": password})


def auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_success(admin_id):
    r = login("admin@palms.edu", "adminpass1")
    assert r.status_code == 200
    body = r.json()
    assert body["token_type"] == "bearer"
    assert body["user"]["email"] == "admin@palms.edu"
    assert body["user"]["role"] == "admin"
    assert "password_hash" not in body["user"]


def test_login_wrong_password_has_same_message_as_unknown_user():
    bad_pw = login("admin@palms.edu", "wrongpassword")
    unknown = login("nobody@palms.edu", "wrongpassword")
    assert bad_pw.status_code == 401
    assert unknown.status_code == 401
    assert bad_pw.json()["detail"] == unknown.json()["detail"]


def test_login_inactive_user_is_forbidden(inactive_id):
    r = login("off@palms.edu", "inactivepass1")
    assert r.status_code == 403


def test_me_requires_token():
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_with_tampered_token(admin_id):
    token = login("admin@palms.edu", "adminpass1").json()["access_token"]
    tampered = token[:-2] + ("ab" if not token.endswith("ab") else "cd")
    r = client.get("/api/v1/auth/me", headers=auth_headers(tampered))
    assert r.status_code == 401


def test_me_with_expired_token(admin_id):
    now = datetime.now(timezone.utc)
    expired = jwt.encode(
        {"sub": str(admin_id), "role": "admin", "iat": now - timedelta(hours=2),
         "exp": now - timedelta(hours=1)},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )
    r = client.get("/api/v1/auth/me", headers=auth_headers(expired))
    assert r.status_code == 401


def test_token_carries_expiry(admin_id):
    token = login("admin@palms.edu", "adminpass1").json()["access_token"]
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
    )
    assert payload["exp"] > payload["iat"]


def test_student_cannot_list_users(student_id):
    token = login("student@palms.edu", "studentpass1").json()["access_token"]
    r = client.get("/api/v1/users", headers=auth_headers(token))
    assert r.status_code == 403


def test_teacher_cannot_create_user(teacher_id):
    token = login("teacher@palms.edu", "teacherpass1").json()["access_token"]
    r = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={"full_name": "X", "email": "x@palms.edu", "password": "password1"},
    )
    assert r.status_code == 403


def test_admin_can_create_user(admin_id):
    token = login("admin@palms.edu", "adminpass1").json()["access_token"]
    r = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={
            "full_name": "New Teacher",
            "email": "newteacher@palms.edu",
            "password": "teacherpass2",
            "role": "teacher",
        },
    )
    assert r.status_code == 201
    assert r.json()["role"] == "teacher"
    db = TestingSession()
    stored = db.query(User).filter_by(email="newteacher@palms.edu").one()
    assert stored.password_hash != "teacherpass2"
    assert security.verify_password("teacherpass2", stored.password_hash)
    db.close()


def test_duplicate_email_conflicts(admin_id):
    token = login("admin@palms.edu", "adminpass1").json()["access_token"]
    r = client.post(
        "/api/v1/users",
        headers=auth_headers(token),
        json={
            "full_name": "Dupe",
            "email": "teacher@palms.edu",
            "password": "password12",
        },
    )
    assert r.status_code == 409


def test_admin_cannot_deactivate_self(admin_id):
    token = login("admin@palms.edu", "adminpass1").json()["access_token"]
    r = client.patch(
        f"/api/v1/users/{admin_id}",
        headers=auth_headers(token),
        json={"is_active": False},
    )
    assert r.status_code == 400


def test_password_hash_uses_bcrypt():
    hashed = security.hash_password("somepassword1")
    assert hashed != "somepassword1"
    assert hashed.startswith("$2b$")
    assert security.verify_password("somepassword1", hashed)
    assert not security.verify_password("wrongpassword", hashed)
