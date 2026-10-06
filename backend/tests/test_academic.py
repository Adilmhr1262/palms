"""Step 3 verification: courses, course_teachers, classes, enrollments, RBAC."""
import pytest

from tests.conftest import auth_headers, client, login_token, make_user
from app.models.user import UserRole


@pytest.fixture(scope="module")
def admin():
    return make_user("ac-admin@palms.edu", "adminpass1", UserRole.admin)


@pytest.fixture(scope="module")
def teacher1():
    return make_user("ac-teacher1@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def teacher2():
    return make_user("ac-teacher2@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student1():
    return make_user("ac-student1@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def student2():
    return make_user("ac-student2@palms.edu", "studentpass1", UserRole.student)


def token(email, password):
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_admin(admin):
    return {"Authorization": f"Bearer {token('ac-admin@palms.edu', 'adminpass1')}"}


@pytest.fixture(scope="module")
def h_t1(teacher1):
    return {"Authorization": f"Bearer {token('ac-teacher1@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_t2(teacher2):
    return {"Authorization": f"Bearer {token('ac-teacher2@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_s1(student1):
    return {"Authorization": f"Bearer {token('ac-student1@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def course(h_t1):
    r = client.post(
        "/api/v1/courses",
        json={"title": "Algebra I", "description": "Intro algebra."},
        headers=h_t1,
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_creator_becomes_course_teacher(course, teacher1):
    teacher_ids = [t["id"] for t in course["teachers"]]
    assert teacher1 in teacher_ids


def test_student_cannot_create_course(h_s1):
    r = client.post("/api/v1/courses", json={"title": "Nope"}, headers=h_s1)
    assert r.status_code == 403


def test_add_coteacher(course, h_t1, teacher2):
    r = client.post(
        f"/api/v1/courses/{course['id']}/teachers",
        json={"teacher_id": teacher2},
        headers=h_t1,
    )
    assert r.status_code == 201, r.text
    # duplicate
    r = client.post(
        f"/api/v1/courses/{course['id']}/teachers",
        json={"teacher_id": teacher2},
        headers=h_t1,
    )
    assert r.status_code == 409


def test_cannot_add_student_as_teacher(course, h_t1, student1):
    r = client.post(
        f"/api/v1/courses/{course['id']}/teachers",
        json={"teacher_id": student1},
        headers=h_t1,
    )
    assert r.status_code == 422


def test_remove_coteacher_and_last_guard(course, h_t1, teacher1, teacher2):
    r = client.delete(
        f"/api/v1/courses/{course['id']}/teachers/{teacher2}", headers=h_t1
    )
    assert r.status_code == 204
    # removing the last teacher is blocked
    r = client.delete(
        f"/api/v1/courses/{course['id']}/teachers/{teacher1}", headers=h_t1
    )
    assert r.status_code == 400


def test_outsider_teacher_cannot_manage(course, h_t2):
    r = client.patch(
        f"/api/v1/courses/{course['id']}", json={"title": "Hijack"}, headers=h_t2
    )
    assert r.status_code == 403


def test_class_lifecycle(h_t1, h_admin, course, teacher1, student1):
    # teacher creates a class for themselves, linked to the course
    r = client.post(
        "/api/v1/classes",
        json={"name": "7-A", "academic_year": "2026", "course_id": course["id"]},
        headers=h_t1,
    )
    assert r.status_code == 201, r.text
    class_id = r.json()["id"]
    assert r.json()["teacher_id"] == teacher1
    # enroll the student
    r = client.post(
        f"/api/v1/classes/{class_id}/enrollments",
        json={"student_id": student1},
        headers=h_t1,
    )
    assert r.status_code == 201, r.text
    # duplicate enrollment blocked
    r = client.post(
        f"/api/v1/classes/{class_id}/enrollments",
        json={"student_id": student1},
        headers=h_t1,
    )
    assert r.status_code == 409
    # enrolling a non-student blocked
    r = client.post(
        f"/api/v1/classes/{class_id}/enrollments",
        json={"student_id": teacher1},
        headers=h_t1,
    )
    assert r.status_code == 422
    # admin creating a class without teacher_id is rejected
    r = client.post(
        "/api/v1/classes",
        json={"name": "7-B", "academic_year": "2026"},
        headers=h_admin,
    )
    assert r.status_code == 422
    # course cannot be deleted while a class uses it
    r = client.delete(f"/api/v1/courses/{course['id']}", headers=h_t1)
    assert r.status_code == 409
    # cleanup: delete class, then course
    r = client.delete(f"/api/v1/classes/{class_id}", headers=h_t1)
    assert r.status_code == 204
    r = client.delete(f"/api/v1/courses/{course['id']}", headers=h_t1)
    assert r.status_code == 204


def test_student_course_visibility(h_t1, h_s1, teacher1, student1):
    r = client.post(
        "/api/v1/courses", json={"title": "Geometry"}, headers=h_t1
    )
    assert r.status_code == 201
    course_id = r.json()["id"]
    # not enrolled yet: course is invisible
    r = client.get("/api/v1/courses", headers=h_s1)
    assert all(c["id"] != course_id for c in r.json())
    r = client.get(f"/api/v1/courses/{course_id}", headers=h_s1)
    assert r.status_code == 403
    # enroll through a class, then it becomes visible
    r = client.post(
        "/api/v1/classes",
        json={"name": "8-A", "academic_year": "2026", "course_id": course_id},
        headers=h_t1,
    )
    class_id = r.json()["id"]
    r = client.post(
        f"/api/v1/classes/{class_id}/enrollments",
        json={"student_id": student1},
        headers=h_t1,
    )
    assert r.status_code == 201
    r = client.get("/api/v1/courses", headers=h_s1)
    assert any(c["id"] == course_id for c in r.json())
    r = client.get(f"/api/v1/courses/{course_id}", headers=h_s1)
    assert r.status_code == 200
    r = client.get(f"/api/v1/classes/{class_id}", headers=h_s1)
    assert r.status_code == 200
    assert r.json()["enrollments"] == []  # roster hidden from students


def test_directory(h_t1, h_s1):
    r = client.get("/api/v1/users/directory", params={"role": "student"}, headers=h_t1)
    assert r.status_code == 200
    assert all(u["role"] == "student" for u in r.json())
    assert all("password_hash" not in u for u in r.json())
    r = client.get("/api/v1/users/directory", params={"role": "student"}, headers=h_s1)
    assert r.status_code == 403
