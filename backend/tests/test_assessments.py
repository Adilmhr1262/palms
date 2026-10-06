"""Step 4 verification: question bank, assessments, publishing, attempts, answers."""
import pytest

from tests.conftest import client, make_user, TestingSession
from app.models.user import UserRole


@pytest.fixture(scope="module")
def teacher():
    return make_user("qa-teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def outsider():
    return make_user("qa-outsider@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student():
    return make_user("qa-student@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def stranger():
    return make_user("qa-stranger@palms.edu", "studentpass1", UserRole.student)


def token(email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_t(teacher):
    return {"Authorization": f"Bearer {token('qa-teacher@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_o(outsider):
    return {"Authorization": f"Bearer {token('qa-outsider@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_s(student):
    return {"Authorization": f"Bearer {token('qa-student@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def h_str(stranger):
    return {"Authorization": f"Bearer {token('qa-stranger@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def course(h_t):
    r = client.post("/api/v1/courses", json={"title": "Algebra Basics"}, headers=h_t)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics", json={"title": "Equations"}, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def class_with_student(course, h_t, student):
    r = client.post(
        "/api/v1/classes",
        json={"name": "9-B", "academic_year": "2026", "course_id": course["id"]},
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
    return class_id


MCQ = {
    "qtype": "mcq",
    "prompt": "What is 2x = 10?",
    "options": ["x = 2", "x = 5", "x = 8", "x = 20"],
    "correct_option": 1,
    "points": 2,
}
TF = {"qtype": "true_false", "prompt": "x = 5 solves 2x = 10.", "correct_option": 0}
SA = {
    "qtype": "short_answer",
    "prompt": "Explain how to solve 3x = 12.",
    "model_answer": "Divide both sides by 3.",
    "points": 3,
}


def test_create_questions(topic, h_t):
    for payload in (MCQ, TF, SA):
        r = client.post(
            f"/api/v1/topics/{topic['id']}/questions", json=payload, headers=h_t
        )
        assert r.status_code == 201, r.text
    r = client.get(f"/api/v1/topics/{topic['id']}/questions", headers=h_t)
    assert r.status_code == 200
    assert len(r.json()) == 3
    mcq = [q for q in r.json() if q["qtype"] == "mcq"][0]
    assert mcq["options"] == MCQ["options"]
    assert mcq["correct_option"] == 1
    assert mcq["points"] == 2


def test_question_validation(topic, h_t):
    bad = dict(MCQ, options=["only one"])
    r = client.post(f"/api/v1/topics/{topic['id']}/questions", json=bad, headers=h_t)
    assert r.status_code == 422
    bad = dict(MCQ, correct_option=9)
    r = client.post(f"/api/v1/topics/{topic['id']}/questions", json=bad, headers=h_t)
    assert r.status_code == 422
    bad = dict(TF, correct_option=5)
    r = client.post(f"/api/v1/topics/{topic['id']}/questions", json=bad, headers=h_t)
    assert r.status_code == 422


def test_bank_rbac(topic, h_t, h_o, h_s):
    r = client.get(f"/api/v1/topics/{topic['id']}/questions", headers=h_o)
    assert r.status_code == 403
    r = client.post(
        f"/api/v1/topics/{topic['id']}/questions", json=MCQ, headers=h_o
    )
    assert r.status_code == 403
    r = client.get(f"/api/v1/topics/{topic['id']}/questions", headers=h_s)
    assert r.status_code == 403


def test_update_question(topic, h_t):
    r = client.get(f"/api/v1/topics/{topic['id']}/questions", headers=h_t)
    q = [x for x in r.json() if x["qtype"] == "short_answer"][0]
    r = client.patch(
        f"/api/v1/questions/{q['id']}", json={"points": 5}, headers=h_t
    )
    assert r.status_code == 200, r.text
    assert r.json()["points"] == 5


def test_delete_question(topic, h_t):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/questions", json=dict(SA), headers=h_t
    )
    qid = r.json()["id"]
    r = client.delete(f"/api/v1/questions/{qid}", headers=h_t)
    assert r.status_code == 204
    r = client.get(f"/api/v1/topics/{topic['id']}/questions", headers=h_t)
    assert all(q["id"] != qid for q in r.json())


@pytest.fixture(scope="module")
def assessment(topic, h_t):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/assessments",
        json={"title": "Equations quiz", "instructions": "Show your work."},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def questions(topic, h_t):
    r = client.get(f"/api/v1/topics/{topic['id']}/questions", headers=h_t)
    return r.json()


def test_publish_requires_questions(assessment, h_t):
    r = client.patch(
        f"/api/v1/assessments/{assessment['id']}/publish",
        json={"is_published": True},
        headers=h_t,
    )
    assert r.status_code == 400


def test_build_and_publish(assessment, questions, h_t):
    ids = [q["id"] for q in questions]
    for qid in ids:
        r = client.post(
            f"/api/v1/assessments/{assessment['id']}/questions",
            json={"question_id": qid},
            headers=h_t,
        )
        assert r.status_code == 201, r.text
    # duplicate rejected
    r = client.post(
        f"/api/v1/assessments/{assessment['id']}/questions",
        json={"question_id": ids[0]},
        headers=h_t,
    )
    assert r.status_code == 409
    # question from another topic rejected
    r = client.post(
        f"/api/v1/assessments/{assessment['id']}/questions",
        json={"question_id": 999999},
        headers=h_t,
    )
    assert r.status_code == 422
    # move to a new position
    r = client.patch(
        f"/api/v1/assessments/{assessment['id']}/questions/{ids[0]}",
        json={"position": 5},
        headers=h_t,
    )
    assert r.status_code == 200
    assert r.json()["position"] == 5
    # publish
    r = client.patch(
        f"/api/v1/assessments/{assessment['id']}/publish",
        json={"is_published": True},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    assert r.json()["is_published"] is True
    assert r.json()["question_count"] == 3
    # published assessment is locked for question changes
    r = client.delete(
        f"/api/v1/assessments/{assessment['id']}/questions/{ids[0]}", headers=h_t
    )
    assert r.status_code == 400
    # unpublish, then removal works
    r = client.patch(
        f"/api/v1/assessments/{assessment['id']}/publish",
        json={"is_published": False},
        headers=h_t,
    )
    assert r.status_code == 200
    r = client.delete(
        f"/api/v1/assessments/{assessment['id']}/questions/{ids[0]}", headers=h_t
    )
    assert r.status_code == 204
    r = client.post(
        f"/api/v1/assessments/{assessment['id']}/questions",
        json={"question_id": ids[0], "position": 1},
        headers=h_t,
    )
    assert r.status_code == 201
    r = client.patch(
        f"/api/v1/assessments/{assessment['id']}/publish",
        json={"is_published": True},
        headers=h_t,
    )
    assert r.status_code == 200


def test_assessment_visibility(topic, assessment, h_s, h_str, class_with_student):
    r = client.get(f"/api/v1/topics/{topic['id']}/assessments", headers=h_s)
    assert r.status_code == 200
    assert any(a["id"] == assessment["id"] for a in r.json())
    # student sees metadata but no question list or correct answers
    r = client.get(f"/api/v1/assessments/{assessment['id']}", headers=h_s)
    assert r.status_code == 200
    assert "questions" not in r.json()
    # unenrolled student has no course access
    r = client.get(f"/api/v1/topics/{topic['id']}/assessments", headers=h_str)
    assert r.status_code == 403


def test_attempt_flow(assessment, h_s, questions, class_with_student):
    # start attempt
    r = client.post(f"/api/v1/assessments/{assessment['id']}/attempts", headers=h_s)
    assert r.status_code == 200, r.text
    attempt = r.json()
    assert attempt["status"] == "in_progress"
    assert len(attempt["questions"]) == 3
    # no correct answers leak to the student
    for q in attempt["questions"]:
        assert "correct_option" not in q
        assert "model_answer" not in q
    # resume returns the same attempt
    r = client.post(f"/api/v1/assessments/{assessment['id']}/attempts", headers=h_s)
    assert r.json()["id"] == attempt["id"]
    aid = attempt["id"]
    by_type = {q["qtype"]: q for q in attempt["questions"]}
    mcq = by_type["mcq"]
    # valid mcq answer
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": mcq["id"], "selected_option": 1},
        headers=h_s,
    )
    assert r.status_code == 200, r.text
    assert r.json()["selected_option"] == 1
    # out-of-range option rejected
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": mcq["id"], "selected_option": 9},
        headers=h_s,
    )
    assert r.status_code == 422
    # question not in assessment rejected
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": 999999, "selected_option": 0},
        headers=h_s,
    )
    assert r.status_code == 422
    # short answer without text rejected
    sa = by_type["short_answer"]
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": sa["id"]},
        headers=h_s,
    )
    assert r.status_code == 422
    # true/false wrong value rejected
    tf = by_type["true_false"]
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": tf["id"], "selected_option": 4},
        headers=h_s,
    )
    assert r.status_code == 422
    # answer remaining questions
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": tf["id"], "selected_option": 0},
        headers=h_s,
    )
    assert r.status_code == 200
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": sa["id"], "student_text": "Divide both sides by 3."},
        headers=h_s,
    )
    assert r.status_code == 200
    # answers are visible on the attempt, without grading
    r = client.get(f"/api/v1/attempts/{aid}", headers=h_s)
    assert len(r.json()["answers"]) == 3
    # submit
    r = client.post(f"/api/v1/attempts/{aid}/submit", headers=h_s)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "submitted"
    assert r.json()["max_score"] == 8  # 2 + 1 + 5 after the points edit
    assert r.json()["total_score"] is None  # grading lands in step 5
    # submit twice blocked
    r = client.post(f"/api/v1/attempts/{aid}/submit", headers=h_s)
    assert r.status_code == 400
    # answer after submit blocked
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": mcq["id"], "selected_option": 0},
        headers=h_s,
    )
    assert r.status_code == 400
    # a new attempt can start after submission
    r = client.post(f"/api/v1/assessments/{assessment['id']}/attempts", headers=h_s)
    assert r.status_code == 200
    assert r.json()["id"] != aid
    # history
    r = client.get(f"/api/v1/assessments/{assessment['id']}/my-attempts", headers=h_s)
    assert len(r.json()) == 2


def test_attempt_isolation(assessment, h_s, h_str):
    r = client.get(f"/api/v1/assessments/{assessment['id']}/my-attempts", headers=h_s)
    aid = r.json()[0]["id"]
    r = client.get(f"/api/v1/attempts/{aid}", headers=h_str)
    assert r.status_code == 403
    r = client.put(
        f"/api/v1/attempts/{aid}/answers",
        json={"question_id": 1, "selected_option": 0},
        headers=h_str,
    )
    assert r.status_code == 403
    r = client.post(f"/api/v1/attempts/{aid}/submit", headers=h_str)
    assert r.status_code == 403


def test_teacher_sees_attempts(assessment, h_t):
    r = client.get(f"/api/v1/assessments/{assessment['id']}/attempts", headers=h_t)
    assert r.status_code == 200
    assert len(r.json()) == 2
    assert r.json()[0]["student_name"]


def test_unpublished_attempt_blocked(topic, h_t, h_s, class_with_student):
    r = client.post(
        f"/api/v1/topics/{topic['id']}/assessments",
        json={"title": "Draft quiz"},
        headers=h_t,
    )
    draft_id = r.json()["id"]
    r = client.post(f"/api/v1/assessments/{draft_id}/attempts", headers=h_s)
    assert r.status_code == 403
