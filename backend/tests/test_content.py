"""Step 3 verification: topics, lessons, resources, uploads, content RBAC."""
import pytest

from tests.conftest import auth_headers, client, login_token, make_user, TestingSession
from sqlalchemy import select
from app.models.content import Resource
from app.models.user import UserRole


@pytest.fixture(scope="module")
def teacher():
    return make_user("ct-teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def outsider():
    return make_user("ct-outsider@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student():
    return make_user("ct-student@palms.edu", "studentpass1", UserRole.student)


def token(email, password):
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_t(teacher):
    return {"Authorization": f"Bearer {token('ct-teacher@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_o(outsider):
    return {"Authorization": f"Bearer {token('ct-outsider@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_s(student):
    return {"Authorization": f"Bearer {token('ct-student@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def course(h_t):
    r = client.post("/api/v1/courses", json={"title": "Fractions 101"}, headers=h_t)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        json={"title": "Basics"},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    assert r.json()["position"] == 1  # auto-appended
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        json={"title": "Advanced"},
        headers=h_t,
    )
    assert r.json()["position"] == 2
    return r.json()


def test_topic_position_conflict(course, topic, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        json={"title": "Clash", "position": 2},
        headers=h_t,
    )
    assert r.status_code == 409


def test_topic_threshold_validation(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        json={"title": "Bad", "mastery_threshold": 120},
        headers=h_t,
    )
    assert r.status_code == 422


def test_outsider_cannot_manage_content(course, h_o, topic):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics",
        json={"title": "Hijack"},
        headers=h_o,
    )
    assert r.status_code == 403
    r = client.post(
        f"/api/v1/topics/{topic['id']}/lessons",
        json={"title": "Hijack lesson"},
        headers=h_o,
    )
    assert r.status_code == 403


def test_lesson_lifecycle(topic, h_t):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/lessons",
        json={"title": "Lesson one", "objectives": "Learn.", "body": "Text."},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    assert r.json()["position"] == 1
    lesson_id = r.json()["id"]
    r = client.post(
        f"/api/v1/topics/{topic['id']}/lessons",
        json={"title": "Lesson clash", "position": 1},
        headers=h_t,
    )
    assert r.status_code == 409
    r = client.patch(
        f"/api/v1/lessons/{lesson_id}",
        json={"title": "Lesson one, revised", "is_enrichment": True},
        headers=h_t,
    )
    assert r.status_code == 200
    assert r.json()["title"] == "Lesson one, revised"
    assert r.json()["is_enrichment"] is True


def test_student_read_needs_enrollment(course, topic, h_t, h_s, student):
    r = client.get(f"/api/v1/courses/{course['id']}/topics", headers=h_s)
    assert r.status_code == 403
    r = client.post(
        "/api/v1/classes",
        json={"name": "CT-1", "academic_year": "2026", "course_id": course["id"]},
        headers=h_t,
    )
    class_id = r.json()["id"]
    r = client.post(
        f"/api/v1/classes/{class_id}/enrollments",
        json={"student_id": student},
        headers=h_t,
    )
    assert r.status_code == 201
    r = client.get(f"/api/v1/courses/{course['id']}/topics", headers=h_s)
    assert r.status_code == 200


def test_resource_upload_rules(topic, h_t, h_o):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/lessons",
        json={"title": "Upload target"},
        headers=h_t,
    )
    lesson_id = r.json()["id"]
    pdf = ("notes.pdf", b"%PDF-1.4 fake", "application/pdf")
    r = client.post(
        f"/api/v1/lessons/{lesson_id}/resources", files={"file": pdf}, headers=h_t
    )
    assert r.status_code == 201, r.text
    assert r.json()["mime_type"] == "application/pdf"
    resource_id = r.json()["id"]
    # blocked type
    exe = ("run.exe", b"MZ fake", "application/x-msdownload")
    r = client.post(
        f"/api/v1/lessons/{lesson_id}/resources", files={"file": exe}, headers=h_t
    )
    assert r.status_code == 422
    # outsider cannot upload
    r = client.post(
        f"/api/v1/lessons/{lesson_id}/resources", files={"file": pdf}, headers=h_o
    )
    assert r.status_code == 403
    # oversized file rejected (limit is 10 MB)
    big = ("big.pdf", b"x" * (11 * 1024 * 1024), "application/pdf")
    r = client.post(
        f"/api/v1/lessons/{lesson_id}/resources", files={"file": big}, headers=h_t
    )
    assert r.status_code == 413
    # delete works
    r = client.delete(f"/api/v1/resources/{resource_id}", headers=h_t)
    assert r.status_code == 204
    db = TestingSession()
    assert db.scalar(select(Resource).where(Resource.id == resource_id)) is None
    db.close()


def test_lesson_detail_shape(topic, h_t, h_s):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/lessons",
        json={"title": "Detail check", "body": "Body text."},
        headers=h_t,
    )
    lesson_id = r.json()["id"]
    r = client.get(f"/api/v1/lessons/{lesson_id}", headers=h_s)
    assert r.status_code == 200
    data = r.json()
    assert data["topic_title"] == topic["title"]
    assert "resources" in data
