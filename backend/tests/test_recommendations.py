"""Step 6 verification: rule-based recommendations linked to mastery."""
import pytest

from tests.conftest import TestingSession, client, make_user
from app.models.user import UserRole
from app.services.recommendations import generate_recommendations


@pytest.fixture(scope="module")
def teacher():
    return make_user("rc-teacher@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def outsider():
    return make_user("rc-outsider@palms.edu", "teacherpass1", UserRole.teacher)


@pytest.fixture(scope="module")
def student():
    return make_user("rc-student@palms.edu", "studentpass1", UserRole.student)


@pytest.fixture(scope="module")
def other_student():
    return make_user("rc-other@palms.edu", "studentpass1", UserRole.student)


def token(email, password):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return r.json()["access_token"]


@pytest.fixture(scope="module")
def h_t(teacher):
    return {"Authorization": f"Bearer {token('rc-teacher@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_o(outsider):
    return {"Authorization": f"Bearer {token('rc-outsider@palms.edu', 'teacherpass1')}"}


@pytest.fixture(scope="module")
def h_s(student):
    return {"Authorization": f"Bearer {token('rc-student@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def h_os(other_student):
    return {"Authorization": f"Bearer {token('rc-other@palms.edu', 'studentpass1')}"}


@pytest.fixture(scope="module")
def course(h_t):
    r = client.post("/api/v1/courses", json={"title": "Recommendations 101"}, headers=h_t)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics", json={"title": "Fractions"}, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def topic2(course, h_t):
    r = client.post(
        f"/api/v1/courses/{course['id']}/topics", json={"title": "Decimals"}, headers=h_t
    )
    assert r.status_code == 201, r.text
    return r.json()


@pytest.fixture(scope="module")
def setup(course, h_t, student, other_student):
    r = client.post(
        "/api/v1/classes",
        json={"name": "R-1", "academic_year": "2026", "course_id": course["id"]},
        headers=h_t,
    )
    assert r.status_code == 201, r.text
    class_id = r.json()["id"]
    for sid in (student, other_student):
        r = client.post(
            f"/api/v1/classes/{class_id}/enrollments",
            json={"student_id": sid},
            headers=h_t,
        )
        assert r.status_code == 201, r.text
    return class_id


def make_assessment(h_t, topic_id, title):
    def q(payload):
        r = client.post(f"/api/v1/topics/{topic_id}/questions", json=payload, headers=h_t)
        assert r.status_code == 201, r.text
        return r.json()

    mcq = q({"qtype": "mcq", "prompt": "2 + 2?", "options": ["3", "4", "5"], "correct_option": 1, "points": 2})
    tf = q({"qtype": "true_false", "prompt": "2 + 2 = 4.", "correct_option": 0, "points": 1})
    sa = q({"qtype": "short_answer", "prompt": "Explain addition.", "model_answer": "Combining quantities.", "points": 3})
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
def assessment(topic, h_t, setup):
    return make_assessment(h_t, topic["id"], "Fractions quiz")


@pytest.fixture(scope="module")
def assessment2(topic2, h_t, setup):
    return make_assessment(h_t, topic2["id"], "Decimals quiz")


def attempt_cycle(h_s, h_t, a, mcq_opt, tf_opt, sa_text, sa_points):
    """Start, answer, submit, then teacher-grade the short answer."""
    r = client.post(f"/api/v1/assessments/{a['id']}/attempts", headers=h_s)
    assert r.status_code == 200, r.text
    aid = r.json()["id"]
    for qid, kw in (
        (a["mcq"]["id"], {"selected_option": mcq_opt}),
        (a["tf"]["id"], {"selected_option": tf_opt}),
        (a["sa"]["id"], {"student_text": sa_text}),
    ):
        r = client.put(f"/api/v1/attempts/{aid}/answers", json={"question_id": qid, **kw}, headers=h_s)
        assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/attempts/{aid}/submit", headers=h_s)
    assert r.status_code == 200, r.text
    r = client.get(f"/api/v1/assessments/{a['id']}/grading-queue", headers=h_t)
    assert r.status_code == 200, r.text
    pending = [i for i in r.json() if i["points_earned"] is None]
    assert pending, "expected a pending short answer"
    r = client.post(
        f"/api/v1/answers/{pending[0]['answer_id']}/grade",
        json={"points_earned": sa_points, "teacher_comment": "Noted."},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    return aid


def active_for(h, topic_id):
    r = client.get("/api/v1/recommendations", headers=h)
    assert r.status_code == 200, r.text
    return [x for x in r.json() if x["topic_id"] == topic_id and x["status"] == "active"]


def test_low_performance_rule(assessment, h_s, h_t, topic):
    # 0 + 0 + 0 = 0%
    attempt_cycle(h_s, h_t, assessment, 0, 1, "no idea", 0)
    recs = active_for(h_s, topic["id"])
    assert len(recs) == 1
    rec = recs[0]
    assert rec["rule_code"] == "LOW_PERFORMANCE"
    assert rec["title"] == "Additional practice recommended"
    assert rec["reason"] == "Your performance is below the required level for this topic."


def test_duplicate_prevention(assessment, h_s, h_t, topic):
    # second 0% attempt: still exactly one active LOW_PERFORMANCE
    attempt_cycle(h_s, h_t, assessment, 0, 1, "still no idea", 0)
    recs = active_for(h_s, topic["id"])
    low = [r for r in recs if r["rule_code"] == "LOW_PERFORMANCE"]
    assert len(low) == 1


def test_rule_priority_repeated_difficulty(h_t, h_s, topic):
    # two consecutive sub-50% attempts: REPEATED_DIFFICULTY is present
    # and listed first, ahead of LOW_PERFORMANCE
    r = client.get("/api/v1/recommendations", headers=h_t)
    assert r.status_code == 200, r.text
    mine = [x for x in r.json() if x["topic_id"] == topic["id"] and x["status"] == "active"]
    codes = [x["rule_code"] for x in mine]
    assert "REPEATED_DIFFICULTY" in codes
    assert "LOW_PERFORMANCE" in codes
    assert codes.index("REPEATED_DIFFICULTY") < codes.index("LOW_PERFORMANCE")
    r4 = next(x for x in mine if x["rule_code"] == "REPEATED_DIFFICULTY")
    assert r4["reason"] == "This topic may require additional teacher support."


def test_developing_rule(assessment, h_s, h_t, topic):
    # 2 + 1 + 0 = 3/6 = 50%: DEVELOPING replaces LOW_PERFORMANCE,
    # repeated-difficulty flag clears
    attempt_cycle(h_s, h_t, assessment, 1, 0, "partial", 0)
    recs = active_for(h_s, topic["id"])
    codes = {r["rule_code"] for r in recs}
    assert codes == {"DEVELOPING"}
    dev = recs[0]
    assert dev["reason"] == "More practice is recommended before moving to the next topic."


def test_mastery_and_high_achievement_rules(assessment, h_s, h_t, topic):
    # 2 + 1 + 3 = 6/6 = 100%: MASTERY_ACHIEVED and HIGH_ACHIEVEMENT
    attempt_cycle(h_s, h_t, assessment, 1, 0, "full answer", 3)
    recs = active_for(h_s, topic["id"])
    codes = {r["rule_code"] for r in recs}
    assert codes == {"MASTERY_ACHIEVED", "HIGH_ACHIEVEMENT"}
    m = next(r for r in recs if r["rule_code"] == "MASTERY_ACHIEVED")
    assert m["reason"] == "You have achieved the required mastery level for this topic."
    e = next(r for r in recs if r["rule_code"] == "HIGH_ACHIEVEMENT")
    assert e["reason"] == "Your strong performance allows you to explore additional activities."


def test_mastery_threshold_change(assessment2, h_os, h_t, topic2, other_student):
    # 2 + 1 + 1 = 4/6 = 66.7%: below default threshold 70 -> DEVELOPING
    attempt_cycle(h_os, h_t, assessment2, 1, 0, "decent", 1)
    recs = active_for(h_os, topic2["id"])
    assert {r["rule_code"] for r in recs} == {"DEVELOPING"}
    # lower the threshold to 60 and regenerate: same score now masters it
    r = client.patch(
        f"/api/v1/topics/{topic2['id']}", json={"mastery_threshold": 60}, headers=h_t
    )
    assert r.status_code == 200, r.text
    db = TestingSession()
    try:
        generate_recommendations(db, other_student, topic2["id"])
        db.commit()
    finally:
        db.close()
    recs = active_for(h_os, topic2["id"])
    assert {r["rule_code"] for r in recs} == {"MASTERY_ACHIEVED"}


def test_dismissed_recommendation_persists(h_s, topic):
    recs = active_for(h_s, topic["id"])
    target = next(r for r in recs if r["rule_code"] == "MASTERY_ACHIEVED")
    r = client.post(f"/api/v1/recommendations/{target['id']}/dismiss", headers=h_s)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "dismissed"
    # the row still exists with status dismissed
    r = client.get(f"/api/v1/recommendations/{target['id']}", headers=h_s)
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "dismissed"
    # no longer listed as active
    assert all(r["id"] != target["id"] for r in active_for(h_s, topic["id"]))


def test_teacher_visibility_restrictions(h_t, h_o, topic):
    r = client.get("/api/v1/recommendations", headers=h_t)
    assert r.status_code == 200, r.text
    assert len(r.json()) > 0
    # outsider teacher sees nothing and cannot open the detail
    r = client.get("/api/v1/recommendations", headers=h_o)
    assert r.status_code == 200, r.text
    assert r.json() == []
    rec_id = client.get("/api/v1/recommendations", headers=h_t).json()[0]["id"]
    r = client.get(f"/api/v1/recommendations/{rec_id}", headers=h_o)
    assert r.status_code == 403, r.text


def test_student_visibility_restrictions(h_s, h_os, student, other_student):
    mine = client.get("/api/v1/recommendations", headers=h_s).json()
    assert all(r["student_id"] == student for r in mine)
    theirs = client.get("/api/v1/recommendations", headers=h_os).json()
    assert len(theirs) > 0
    assert all(r["student_id"] == other_student for r in theirs)
    # a student cannot dismiss another student's recommendation
    other_id = theirs[0]["id"]
    r = client.post(f"/api/v1/recommendations/{other_id}/dismiss", headers=h_s)
    assert r.status_code == 403, r.text


def test_teacher_review_marks_completed(h_t, topic):
    recs = client.get("/api/v1/recommendations", headers=h_t).json()
    target = next(
        r for r in recs if r["topic_id"] == topic["id"] and r["rule_code"] == "HIGH_ACHIEVEMENT"
    )
    r = client.post(
        f"/api/v1/recommendations/{target['id']}/review",
        json={"teacher_note": "Try the enrichment worksheet."},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "completed"
    assert body["teacher_note"] == "Try the enrichment worksheet."
