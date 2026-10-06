"""Step 5 verification: auto-grading, teacher grading, mastery."""
import pytest

from tests.conftest import client, make_user
from app.models.user import UserRole
from app.services.mastery import mastery_status
from app.models.mastery import MasteryStatus


@pytest.fixture(scope="module")
def teacher():
    return make_user("gr-teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def outsider():
    return make_user("gr-outsider@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student():
    return make_user("gr-student@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def other_student():
    return make_user("gr-other@palms.edu", "studentpass1", UserRole.student)


def token(email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_t(teacher):
    return {"Authorization": f"Bearer {token('gr-teacher@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_o(outsider):
    return {"Authorization": f"Bearer {token('gr-outsider@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_s(student):
    return {"Authorization": f"Bearer {token('gr-student@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def h_os(other_student):
    return {"Authorization": f"Bearer {token('gr-other@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def course(h_t):
    r = client.post("/api/v1/courses", json={"title": "Grading 101"}, headers=h_t)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics", json={"title": "Basics"}, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def setup(course, h_t, student):
    r = client.post(
        "/api/v1/classes",
        json={"name": "G-1", "academic_year": "2026", "course_id": course["id"]},
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


def make_question(h_t, topic_id, payload):
    r = client.post(
        f"/api/v1/topics/{topic_id}/questions", json=payload, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def assessment(topic, h_t, setup):
    mcq = make_question(
        h_t,
        topic["id"],
        {
            "qtype": "mcq",
            "prompt": "2 + 2?",
            "options": ["3", "4", "5"],
            "correct_option": 1,
            "points": 2,
        },
    )
    tf = make_question(
        h_t,
        topic["id"],
        {
            "qtype": "true_false",
            "prompt": "2 + 2 = 4.",
            "correct_option": 0,
            "points": 1,
        },
    )
    sa = make_question(
        h_t,
        topic["id"],
        {
            "qtype": "short_answer",
            "prompt": "Explain addition.",
            "model_answer": "Combining quantities.",
            "points": 3,
        },
    )
    r = client.post(
        f"/api/v1/topics/{topic['id']}/assessments",
        json={"title": "Basics quiz"},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    aid = r.json()["id"]
    for q in (mcq, tf, sa):
        r = client.post(
            f"/api/v1/assessments/{aid}/questions",
            json={"question_id": q["id"]},
            headers=h_t,
        )
        assert r.status_code == 201, r.text
    r = client.patch(
        f"/api/v1/assessments/{aid}/publish",
        json={"is_published": True},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    return {"id": aid, "mcq": mcq, "tf": tf, "sa": sa}


def start(h_s, aid):
    r = client.post(f"/api/v1/assessments/{aid}/attempts", headers=h_s)
    assert r.status_code == 200, r.text
    return r.json()


def answer(h_s, attempt_id, question_id, **kwargs):
    r = client.put(
        f"/api/v1/attempts/{attempt_id}/answers",
        json={"question_id": question_id, **kwargs},
        headers=h_s,
    )
    assert r.status_code == 200, r.text
    return r.json()


def submit(h_s, attempt_id):
    r = client.post(f"/api/v1/attempts/{attempt_id}/submit", headers=h_s)
    assert r.status_code == 200, r.text
    return r.json()


def test_auto_grading_on_submit(assessment, h_s):
    a = start(h_s, assessment["id"])
    aid = a["id"]
    answer(h_s, aid, assessment["mcq"]["id"], selected_option=1)  # correct
    answer(h_s, aid, assessment["tf"]["id"], selected_option=1)  # wrong
    answer(h_s, aid, assessment["sa"]["id"], student_text="Putting things together.")
    result = submit(h_s, aid)
    # short answer still pending: attempt stays submitted, no total yet
    assert result["status"] == "submitted"
    assert result["total_score"] is None
    r = client.get(f"/api/v1/attempts/{aid}", headers=h_s)
    by_q = {x["question_id"]: x for x in r.json()["answers"]}
    mcq = by_q[assessment["mcq"]["id"]]
    assert mcq["is_correct"] is True
    assert mcq["points_earned"] == 2
    tf = by_q[assessment["tf"]["id"]]
    assert tf["is_correct"] is False
    assert tf["points_earned"] == 0
    sa = by_q[assessment["sa"]["id"]]
    assert sa["points_earned"] is None
    assert sa["is_correct"] is None


def test_unanswered_closed_question_scores_zero(assessment, h_s):
    a = start(h_s, assessment["id"])
    aid = a["id"]
    # answer only the mcq; leave true/false blank
    answer(h_s, aid, assessment["mcq"]["id"], selected_option=1)
    answer(h_s, aid, assessment["sa"]["id"], student_text="Some text.")
    submit(h_s, aid)
    r = client.get(f"/api/v1/attempts/{aid}", headers=h_s)
    by_q = {x["question_id"]: x for x in r.json()["answers"]}
    tf = by_q[assessment["tf"]["id"]]
    assert tf["points_earned"] == 0
    assert tf["is_correct"] is False


def test_grading_queue_lists_pending(assessment, h_t):
    r = client.get(
        f"/api/v1/assessments/{assessment['id']}/grading-queue", headers=h_t
    )
    assert r.status_code == 200, r.text
    pending = [x for x in r.json() if x["points_earned"] is None]
    assert len(pending) == 2
    assert pending[0]["student_text"] == "Putting things together."
    assert pending[0]["question_points"] == 3


def _grade_first_pending(h_t, assessment_id, points, comment):
    r = client.get(
        f"/api/v1/assessments/{assessment_id}/grading-queue", headers=h_t
    )
    pending = [x for x in r.json() if x["points_earned"] is None]
    item = pending[0]
    return _grade_item(h_t, item, points, comment), item


def _grade_item(h_t, item, points, comment):
    r = client.post(
        f"/api/v1/answers/{item['answer_id']}/grade",
        json={"points_earned": points, "teacher_comment": comment},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _grade_attempt_sa(h_t, assessment_id, attempt_id, points, comment):
    r = client.get(
        f"/api/v1/assessments/{assessment_id}/grading-queue", headers=h_t
    )
    items = [
        x
        for x in r.json()
        if x["points_earned"] is None and x["attempt_id"] == attempt_id
    ]
    assert items, "no pending short answer for this attempt"
    return _grade_item(h_t, items[0], points, comment)


def test_teacher_grades_short_answer(assessment, h_t, h_s, topic, teacher):
    graded, item = _grade_first_pending(
        h_t, assessment["id"], 2, "Good start, add an example."
    )
    assert graded["points_earned"] == 2
    assert graded["teacher_comment"] == "Good start, add an example."
    assert graded["graded_by"] == teacher
    assert graded["graded_at"] is not None
    # attempt 1: mcq 2 + tf 0 + sa 2 = 4 of 6 -> graded
    r = client.get(f"/api/v1/attempts/{item['attempt_id']}", headers=h_s)
    detail = r.json()
    assert detail["status"] == "graded"
    assert detail["total_score"] == 4
    # mastery: 66.7%, threshold 70 -> developing
    r = client.get(f"/api/v1/topics/{topic['id']}/mastery", headers=h_s)
    assert r.status_code == 200, r.text
    records = r.json()
    assert len(records) == 1
    m = records[0]
    assert m["attempts_count"] == 1
    assert m["latest_score"] == pytest.approx(66.7, abs=0.05)
    assert m["best_score"] == pytest.approx(66.7, abs=0.05)
    assert m["status"] == "developing"


def test_grading_unauthorized(assessment, topic, h_o, h_s, h_os):
    r = client.get(
        f"/api/v1/assessments/{assessment['id']}/grading-queue", headers=h_o
    )
    assert r.status_code == 403
    r = client.get(
        f"/api/v1/assessments/{assessment['id']}/grading-queue", headers=h_s
    )
    assert r.status_code == 403
    r = client.post(
        "/api/v1/answers/1/grade",
        json={"points_earned": 1},
        headers=h_s,
    )
    assert r.status_code == 403
    # teacher of another course cannot see this topic's mastery
    r = client.get(f"/api/v1/topics/{topic['id']}/mastery", headers=h_o)
    assert r.status_code in (403, 404)


def test_grading_validation(assessment, h_t):
    r = client.get(
        f"/api/v1/assessments/{assessment['id']}/grading-queue", headers=h_t
    )
    pending = [x for x in r.json() if x["points_earned"] is None]
    answer_id = pending[0]["answer_id"]
    # more than the question's points
    r = client.post(
        f"/api/v1/answers/{answer_id}/grade",
        json={"points_earned": 99},
        headers=h_t,
    )
    assert r.status_code == 422
    # negative
    r = client.post(
        f"/api/v1/answers/{answer_id}/grade",
        json={"points_earned": -1},
        headers=h_t,
    )
    assert r.status_code == 422


def test_mastery_updates_with_second_attempt(assessment, h_t, h_s, topic):
    a = start(h_s, assessment["id"])
    aid = a["id"]
    answer(h_s, aid, assessment["mcq"]["id"], selected_option=1)
    answer(h_s, aid, assessment["tf"]["id"], selected_option=0)
    answer(h_s, aid, assessment["sa"]["id"], student_text="Full explanation here.")
    result = submit(h_s, aid)
    assert result["status"] == "submitted"  # sa pending
    _grade_attempt_sa(h_t, assessment["id"], aid, 3, "Complete.")
    r = client.get(f"/api/v1/attempts/{aid}", headers=h_s)
    assert r.json()["status"] == "graded"
    assert r.json()["total_score"] == 6
    r = client.get(f"/api/v1/topics/{topic['id']}/mastery", headers=h_s)
    m = r.json()[0]
    assert m["attempts_count"] == 2
    assert m["latest_score"] == pytest.approx(100.0)
    assert m["best_score"] == pytest.approx(100.0)
    assert m["status"] == "mastered"


def test_teacher_sees_all_mastery(topic, h_t, h_s, h_os):
    r = client.get(f"/api/v1/topics/{topic['id']}/mastery", headers=h_t)
    assert r.status_code == 200, r.text
    assert len(r.json()) == 1
    assert r.json()[0]["student_name"]
    # unenrolled student sees nothing
    r = client.get(f"/api/v1/topics/{topic['id']}/mastery", headers=h_os)
    assert r.status_code == 403


def test_mastery_status_boundaries():
    cases = [
        (49, "needs_support"),
        (50, "developing"),
        (69, "developing"),
        (70, "proficient"),
        (84, "proficient"),
        (85, "mastered"),
        (100, "mastered"),
        (0, "needs_support"),
    ]
    for percent, expected in cases:
        assert mastery_status(percent, 70).value == expected, percent
    # the topic threshold moves the developing/proficient line
    assert mastery_status(79, 80) == MasteryStatus.developing
    assert mastery_status(80, 80) == MasteryStatus.proficient
    assert mastery_status(85, 95) == MasteryStatus.mastered
