"""Step 9 security tests: upload backdoor closed, login rate limiting,
production secret fail-fast, token lifetime, and data isolation."""
import io
from datetime import datetime, timezone

import pytest

from app.core import security
from app.core.config import settings
from app.main import assert_production_secrets
from app.models.user import UserRole
from app.routers import auth as auth_router
from tests.conftest import TestingSession, client, make_user


@pytest.fixture(scope="module")
def teacher():
    return make_user("sec-teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def outsider():
    return make_user("sec-outsider@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student():
    return make_user("sec-student@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def admin():
    return make_user("sec-admin@palms.edu", "adminpass1", UserRole.admin)


def token(email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_t(teacher):
    return {"Authorization": f"Bearer {token('sec-teacher@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_o(outsider):
    return {"Authorization": f"Bearer {token('sec-outsider@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_s(student):
    return {"Authorization": f"Bearer {token('sec-student@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def h_a(admin):
    return {"Authorization": f"Bearer {token('sec-admin@palms.edu', 'adminpass1')}"}


@pytest.fixture(scope="module")
def course(h_t):
    r = client.post("/api/v1/courses", json={"title": "Security 101"}, headers=h_t)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics", json={"title": "Locks"}, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def lesson(topic, h_t):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/lessons",
        json={
            "title": "Keys",
            "objectives": "Understand keys.",
            "body": "Keys open locks.",
            "position": 1,
        },
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def resource(lesson, h_t):
    files = {"file": ("notes.txt", io.BytesIO(b"secret study notes"), "text/plain")}
    r = client.post(
        f"/api/v1/lessons/{lesson['id']}/resources", files=files, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_uploads_not_served_statically(resource, h_t, h_o):
    # The old StaticFiles mount is gone: no unauthenticated file access.
    r = client.get("/uploads/does-not-exist.txt")
    assert r.status_code == 404
    # The authenticated endpoint still serves the file to course members.
    r = client.get(f"/api/v1/resources/{resource['id']}/download", headers=h_t)
    assert r.status_code == 200, r.text
    assert r.content == b"secret study notes"
    # An unrelated teacher cannot download it.
    r = client.get(f"/api/v1/resources/{resource['id']}/download", headers=h_o)
    assert r.status_code == 403


def test_login_rate_limit():
    email = "sec-ratelimit@palms.edu"
    other = "sec-ratelimit-ok@palms.edu"
    make_user(email, "correctpass1", UserRole.student)
    make_user(other, "rightpass1", UserRole.student)
    for _ in range(10):
        r = client.post(
            "/api/v1/auth/login", json={"email": email, "password": "wrongpass"}
        )
        assert r.status_code == 401, r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpass"})
    assert r.status_code == 429
    assert "Too many" in r.json()["detail"]
    # Other accounts are unaffected.
    r = client.post(
        "/api/v1/auth/login", json={"email": other, "password": "rightpass1"}
    )
    assert r.status_code == 200, r.text


def test_production_secret_fail_fast(monkeypatch):
    monkeypatch.setattr(settings, "env", "production")
    monkeypatch.setattr(settings, "jwt_secret", "change-me-to-a-long-random-string")
    with pytest.raises(RuntimeError):
        assert_production_secrets()
    monkeypatch.setattr(settings, "jwt_secret", "a-real-secret-value-here")
    assert_production_secrets()  # does not raise
    monkeypatch.setattr(settings, "env", "development")
    monkeypatch.setattr(settings, "jwt_secret", "change-me-to-a-long-random-string")
    assert_production_secrets()  # dev may use the placeholder


def test_token_lifetime_is_two_hours():
    raw = security.create_access_token(123, "student")
    payload = security.decode_token(raw)
    lifetime = payload["exp"] - payload["iat"]
    assert lifetime == 2 * 60 * 60


def test_login_still_rejects_bad_credentials(h_s):
    auth_router._LOGIN_FAILURES.clear()
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "sec-student@palms.edu", "password": "nope-not-it"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid email or password."


def test_admin_cannot_demote_self(h_a, admin):
    r = client.patch(
        f"/api/v1/users/{admin}", json={"role": "teacher"}, headers=h_a
    )
    assert r.status_code == 400
    r = client.patch(
        f"/api/v1/users/{admin}", json={"is_active": False}, headers=h_a
    )
    assert r.status_code == 400


def test_teacher_cannot_reach_unrelated_course(h_o, course):
    r = client.get(f"/api/v1/courses/{course['id']}", headers=h_o)
    assert r.status_code == 403
    r = client.get(f"/api/v1/courses/{course['id']}/topics", headers=h_o)
    assert r.status_code == 403


def test_student_attempt_isolation(course, topic, h_t, h_o, h_s, student):
    # Enroll the student so the assessment can be attempted.
    r = client.post(
        "/api/v1/classes",
        json={"name": "SEC-1", "academic_year": "2026", "course_id": course["id"]},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    class_id = r.json()["id"]
    r = client.post(
        f"/api/v1/classes/{class_id}/enrollments",
        json={"student_id": student},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    # Build a small assessment and have the student attempt it.
    def q(payload):
        r = client.post(
            f"/api/v1/topics/{topic['id']}/questions", json=payload, headers=h_t
        )
        assert r.status_code == 201, r.text
        return r.json()

    mcq = q({
        "qtype": "mcq", "prompt": "1+1?", "options": ["1", "2"],
        "correct_option": 1, "points": 1,
    })
    r = client.post(
        f"/api/v1/topics/{topic['id']}/assessments", json={"title": "Iso quiz"}, headers=h_t
    )
    aid = r.json()["id"]
    r = client.post(
        f"/api/v1/assessments/{aid}/questions", json={"question_id": mcq["id"]}, headers=h_t
    )
    r = client.patch(f"/api/v1/assessments/{aid}/publish", json={"is_published": True}, headers=h_t)
    r = client.post(f"/api/v1/assessments/{aid}/attempts", headers=h_s)
    attempt_id = r.json()["id"]
    # Another student cannot read or write to it.
    other = make_user("sec-other@palms.edu", "studentpass1", UserRole.student)
    oh = {"Authorization": f"Bearer {token('sec-other@palms.edu', 'studentpass1')}"}
    r = client.get(f"/api/v1/attempts/{attempt_id}", headers=oh)
    assert r.status_code == 403
    r = client.put(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={"question_id": mcq["id"], "selected_option": 0},
        headers=oh,
    )
    assert r.status_code == 403
    # The unrelated teacher cannot read it either.
    r = client.get(f"/api/v1/attempts/{attempt_id}", headers=h_o)
    assert r.status_code == 403
