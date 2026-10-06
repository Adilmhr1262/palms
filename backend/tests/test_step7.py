"""Step 7 tests: feedback visibility, student privacy, report filtering,
CSV export permissions, research score calculation, unauthorized access."""
import pytest

from tests.conftest import auth_headers, client, make_user
from app.models.user import UserRole


@pytest.fixture(scope="module")
def teacher():
    return make_user("rp-teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def outsider():
    return make_user("rp-outsider@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student():
    return make_user("rp-student@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def other_student():
    return make_user("rp-other@palms.edu", "studentpass1", UserRole.student)


def token(email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_t(teacher):
    return auth_headers(token("rp-teacher@palms.edu", "teacherpass1"))


@pytest.fixture(scope="module")
def h_o(outsider):
    return auth_headers(token("rp-outsider@palms.edu", "teacherpass1"))


@pytest.fixture(scope="module")
def h_s(student):
    return auth_headers(token("rp-student@palms.edu", "studentpass1"))


@pytest.fixture(scope="module")
def h_os(other_student):
    return auth_headers(token("rp-other@palms.edu", "studentpass1"))


@pytest.fixture(scope="module")
def course(h_t):
    r = client.post("/api/v1/courses", json={"title": "Reporting 101"}, headers=h_t)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics", json={"title": "Ratios"}, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def class_id(course, h_t, student, other_student):
    r = client.post(
        "/api/v1/classes",
        json={"name": "RP-1", "academic_year": "2026", "course_id": course["id"]},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    cid = r.json()["id"]
    for sid in (student, other_student):
        r = client.post(
            f"/api/v1/classes/{cid}/enrollments", json={"student_id": sid}, headers=h_t
        )
        assert r.status_code == 201, r.text
    return cid


def make_assessment(h_t, topic_id, title):
    def q(payload):
        r = client.post(f"/api/v1/topics/{topic_id}/questions", json=payload, headers=h_t)
        assert r.status_code == 201, r.text
        return r.json()

    mcq = q({"qtype": "mcq", "prompt": "1 + 1?", "options": ["1", "2", "3"], "correct_option": 1, "points": 2})
    tf = q({"qtype": "true_false", "prompt": "1 + 1 = 2.", "correct_option": 0, "points": 1})
    sa = q({"qtype": "short_answer", "prompt": "Explain.", "model_answer": "Sum.", "points": 3})
    r = client.post(f"/api/v1/topics/{topic_id}/assessments", json={"title": title}, headers=h_t)
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    for qq in (mcq, tf, sa):
        r = client.post(f"/api/v1/assessments/{aid}/questions", json={"question_id": qq["id"]}, headers=h_t)
        assert r.status_code == 201, r.text
    r = client.patch(f"/api/v1/assessments/{aid}/publish", json={"is_published": True}, headers=h_t)
    assert r.status_code == 200, r.text
    return {"id": aid, "mcq": mcq, "tf": tf, "sa": sa}


@pytest.fixture(scope="module")
def assessment(topic, h_t, class_id):
    return make_assessment(h_t, topic["id"], "Ratios quiz")


@pytest.fixture(scope="module")
def graded(h_s, h_t, assessment, student):
    """One fully graded 0% attempt by the student."""
    r = client.post(f"/api/v1/assessments/{assessment['id']}/attempts", headers=h_s)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    for qid, kw in (
        (assessment["mcq"]["id"], {"selected_option": 0}),
        (assessment["tf"]["id"], {"selected_option": 1}),
        (assessment["sa"]["id"], {"student_text": "no idea"}),
    ):
        r = client.put(f"/api/v1/attempts/{aid}/answers", json={"question_id": qid, **kw}, headers=h_s)
        assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/attempts/{aid}/submit", headers=h_s)
    assert r.status_code == 200, r.text
    r = client.get(f"/api/v1/assessments/{assessment['id']}/grading-queue", headers=h_t)
    pending = [i for i in r.json() if i["points_earned"] is None]
    assert pending
    r = client.post(
        f"/api/v1/answers/{pending[0]['answer_id']}/grade",
        json={"points_earned": 0, "teacher_comment": "Review the examples."},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    return aid


def test_teacher_feedback_history(graded, h_t, class_id, student, assessment):
    r = client.get(
        f"/api/v1/classes/{class_id}/feedback-history",
        params={"student_id": student},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["assessment_title"] == "Ratios quiz"
    assert row["topic_title"] == "Ratios"
    assert row["score"] == "0 / 6 (0%)"
    assert row["teacher_comment"] == "Review the examples."
    assert row["intervention"] == "Additional practice recommended"


def test_teacher_feedback_unauthorized(graded, h_o, class_id, student, h_os):
    r = client.get(
        f"/api/v1/classes/{class_id}/feedback-history",
        params={"student_id": student},
        headers=h_o,
    )
    assert r.status_code == 403
    r = client.get(
        f"/api/v1/classes/{class_id}/feedback-history",
        params={"student_id": student},
        headers=h_os,
    )
    assert r.status_code in (401, 403)


def test_student_feedback_own_only(graded, h_s, h_os, assessment):
    r = client.get("/api/v1/feedback/my", headers=h_s)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["assessment_title"] == "Ratios quiz"
    assert row["teacher_comment"] == "Review the examples."
    assert "teacher_note" not in row
    assert row["suggestion"] == "Your latest score is below 50%. Review the topic lessons and attempt the assessment again."
    r = client.get("/api/v1/feedback/my", headers=h_os)
    assert r.status_code == 200, r.text
    assert r.json() == []


def test_class_progress_report(graded, h_t, h_o, class_id, student, other_student):
    r = client.get(f"/api/v1/classes/{class_id}/reports/class-progress", headers=h_t)
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2  # two students, one topic each
    by_name = {x["student_name"]: x for x in rows}
    main = by_name["Rp-Student"]
    assert main["attempts_count"] == 1
    assert main["latest_score"] == 0.0
    assert main["best_score"] == 0.0
    assert main["mastery_status"] == "needs_support"
    other = by_name["Rp-Other"]
    assert other["attempts_count"] == 0
    assert other["latest_score"] is None
    r = client.get(f"/api/v1/classes/{class_id}/reports/class-progress", headers=h_o)
    assert r.status_code == 403


def test_student_progress_report(graded, h_t, h_s, h_os, class_id, student, other_student):
    r = client.get(
        f"/api/v1/classes/{class_id}/reports/student-progress",
        params={"student_id": student},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 1
    row = rows[0]
    assert row["topic_title"] == "Ratios"
    assert row["assessment_attempts"] == 1
    assert row["latest_score"] == 0.0
    assert row["mastery_status"] == "needs_support"
    # student can view own, not another student's
    r = client.get(
        f"/api/v1/classes/{class_id}/reports/student-progress",
        params={"student_id": student},
        headers=h_s,
    )
    assert r.status_code == 200
    r = client.get(
        f"/api/v1/classes/{class_id}/reports/student-progress",
        params={"student_id": other_student},
        headers=h_s,
    )
    assert r.status_code == 403


def test_csv_export_permissions(graded, h_t, h_o, h_s, class_id, student):
    r = client.get("/api/v1/exports/mastery.csv", params={"class_id": class_id}, headers=h_t)
    assert r.status_code == 200, r.text
    assert "text/csv" in r.headers["content-type"]
    assert "Student,Topic,Attempts" in r.text
    r = client.get("/api/v1/exports/assessments.csv", params={"class_id": class_id}, headers=h_t)
    assert r.status_code == 200, r.text
    assert "Teacher comment" in r.text
    # student is denied
    r = client.get("/api/v1/exports/mastery.csv", params={"class_id": class_id}, headers=h_s)
    assert r.status_code in (401, 403)
    # outside teacher is denied
    r = client.get("/api/v1/exports/mastery.csv", params={"class_id": class_id}, headers=h_o)
    assert r.status_code == 403


def test_research_crud_and_score_change(h_t, h_o, class_id, student):
    payload = {
        "student_id": student,
        "pre_test_score": 45.0,
        "post_test_score": 72.5,
        "learning_period": "6 weeks",
        "notes": "Attended all sessions.",
    }
    r = client.post(f"/api/v1/classes/{class_id}/research-sessions", json=payload, headers=h_t)
    assert r.status_code == 201, r.text
    rec = r.json()
    assert rec["score_change"] == 27.5
    assert rec["student_name"] == "Rp-Student"
    assert rec["course_title"] == "Reporting 101"
    sid = rec["id"]
    # patch post score down -> negative change, measured only
    r = client.patch(f"/api/v1/research-sessions/{sid}", json={"post_test_score": 40.0}, headers=h_t)
    assert r.status_code == 200, r.text
    assert r.json()["score_change"] == -5.0
    # pre only -> no change
    r = client.patch(
        f"/api/v1/research-sessions/{sid}",
        json={"post_test_score": None},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    assert r.json()["score_change"] is None
    # outsider teacher cannot create or list
    r = client.post(f"/api/v1/classes/{class_id}/research-sessions", json=payload, headers=h_o)
    assert r.status_code == 403
    r = client.get(f"/api/v1/classes/{class_id}/research-sessions", headers=h_o)
    assert r.status_code == 403
    # list works for the class teacher
    r = client.get(f"/api/v1/classes/{class_id}/research-sessions", headers=h_t)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1


def test_research_csv_export(h_t, class_id):
    r = client.get("/api/v1/exports/research.csv", params={"class_id": class_id}, headers=h_t)
    assert r.status_code == 200, r.text
    assert "Pre-test score" in r.text
    assert "Score change" in r.text
