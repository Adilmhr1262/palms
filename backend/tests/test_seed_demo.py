"""Step 8 tests: the demo seed runs on a fresh database, all roles can log
in, the data demonstrates the five student scenarios and all five
recommendation rules, and the complete workflow is demonstrable via the API.
"""
import pytest
from sqlalchemy import func, select

from app.models.academic import Course, Enrollment, SchoolClass
from app.models.assessment import Assessment, Attempt
from app.models.content import Lesson, Resource, Topic
from app.models.mastery import Mastery
from app.models.recommendation import LessonProgress, Recommendation
from app.models.research import ResearchSession
from app.models.user import User, UserRole
from app.seed import seed_demo
from tests.conftest import TestingSession, client


# Function scope: the seed is idempotent, so repeat runs only verify skips.
@pytest.fixture(scope="function", autouse=True)
def demo(monkeypatch):
    # Run the seed against the shared in-memory test database instead of the
    # production engine configured in settings.
    monkeypatch.setattr(
        "app.seed.seed_demo.get_session_factory", lambda: TestingSession
    )
    monkeypatch.setattr(
        "app.seed.seed_content.get_session_factory", lambda: TestingSession
    )
    seed_demo.run()
    yield


def _login(email, password):
    r = client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert r.status_code == 200, r.text
    return r.json()


def _headers(email, password):
    token = _login(email, password)["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_demo_accounts_and_roles(demo):
    db = TestingSession()
    try:
        expected = {
            "admin@palms.edu": UserRole.admin,
            "sana.malik@palms.edu": UserRole.teacher,
            "imran.sheikh@palms.edu": UserRole.teacher,
            "ali.raza@student.palms.edu": UserRole.student,
            "fatima.noor@student.palms.edu": UserRole.student,
            "usman.tariq@student.palms.edu": UserRole.student,
            "hina.shah@student.palms.edu": UserRole.student,
            "danish.ali@student.palms.edu": UserRole.student,
        }
        for email, role in expected.items():
            user = db.scalar(select(User).where(User.email == email))
            assert user is not None, f"missing demo account {email}"
            assert user.role == role, f"{email} has role {user.role}"
            assert user.is_active
    finally:
        db.close()


def test_all_roles_can_log_in(demo):
    teacher = _login("sana.malik@palms.edu", "demo1234")
    assert teacher["user"]["role"] == "teacher"
    student = _login("ali.raza@student.palms.edu", "demo1234")
    assert student["user"]["role"] == "student"
    # The demo admin email is also used by the auth test module with its own
    # password; either way an admin must be able to sign in with it.
    r = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@palms.edu", "password": "demo1234"},
    )
    if r.status_code != 200:
        r = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@palms.edu", "password": "adminpass1"},
        )
    assert r.status_code == 200, r.text
    assert r.json()["user"]["role"] == "admin"


def test_course_structure_complete(demo):
    db = TestingSession()
    try:
        course = db.scalar(
            select(Course).where(Course.title == "Mathematics Foundations")
        )
        assert course is not None
        topics = db.scalars(
            select(Topic).where(Topic.course_id == course.id).order_by(Topic.position)
        ).all()
        assert [t.title for t in topics] == [
            "Fractions",
            "Decimals",
            "Percentages",
            "Basic Algebra",
        ]
        for topic in topics:
            lessons = db.scalars(
                select(Lesson).where(Lesson.topic_id == topic.id)
            ).all()
            assert len(lessons) >= 2, f"{topic.title} has no lessons"
            assessments = db.scalars(
                select(Assessment).where(
                    Assessment.topic_id == topic.id,
                    Assessment.is_published.is_(True),
                )
            ).all()
            assert len(assessments) == 1, f"{topic.title} needs one published assessment"
            lesson_ids = [lesson.id for lesson in lessons]
            resources = db.scalars(
                select(Resource).where(Resource.lesson_id.in_(lesson_ids))
            ).all()
            assert resources, f"{topic.title} has no resources"
        class_ = db.scalar(
            select(SchoolClass).where(
                SchoolClass.name == "7-A", SchoolClass.academic_year == "2026"
            )
        )
        assert class_ is not None
        enrolled = db.scalar(
            select(func.count(Enrollment.id)).where(
                Enrollment.class_id == class_.id
            )
        )
        assert enrolled == 5
    finally:
        db.close()


def _student_id(db, email):
    return db.scalar(select(User.id).where(User.email == email))


def _demo_topic_id(db, title):
    course_id = db.scalar(
        select(Course.id).where(Course.title == "Mathematics Foundations")
    )
    return db.scalar(
        select(Topic.id).where(
            Topic.course_id == course_id, Topic.title == title
        )
    )


def test_student_scenarios(demo):
    db = TestingSession()
    try:
        scenarios = {
            "ali.raza@student.palms.edu": ("Fractions", 2, "mastered"),
            "fatima.noor@student.palms.edu": ("Fractions", 2, "needs_support"),
            "usman.tariq@student.palms.edu": ("Decimals", 2, "developing"),
            "danish.ali@student.palms.edu": ("Decimals", 1, "proficient"),
        }
        for email, (topic_title, attempts, status) in scenarios.items():
            sid = _student_id(db, email)
            topic_id = _demo_topic_id(db, topic_title)
            mastery = db.scalar(
                select(Mastery).where(
                    Mastery.student_id == sid, Mastery.topic_id == topic_id
                )
            )
            assert mastery is not None, f"no mastery for {email}"
            assert mastery.attempts_count == attempts
            assert mastery.status.value == status, f"{email}: {mastery.status}"
            graded = db.scalars(
                select(Attempt).where(
                    Attempt.student_id == sid, Attempt.status == "graded"
                )
            ).all()
            assert len(graded) == attempts
            assert all(a.total_score is not None for a in graded)
        # Incomplete learner: one lesson done, no attempts, no mastery.
        hina = _student_id(db, "hina.shah@student.palms.edu")
        assert db.scalar(
            select(func.count(LessonProgress.id)).where(
                LessonProgress.student_id == hina
            )
        ) == 1
        assert db.scalar(
            select(func.count(Attempt.id)).where(Attempt.student_id == hina)
        ) == 0
        assert db.scalar(
            select(func.count(Mastery.id)).where(Mastery.student_id == hina)
        ) == 0
    finally:
        db.close()


def test_all_five_recommendation_rules(demo):
    db = TestingSession()
    try:
        rules = set(
            db.scalars(
                select(Recommendation.rule_code).where(
                    Recommendation.status == "active"
                )
            ).all()
        )
        for rule in (
            "LOW_PERFORMANCE",
            "REPEATED_DIFFICULTY",
            "DEVELOPING",
            "MASTERY_ACHIEVED",
            "HIGH_ACHIEVEMENT",
        ):
            assert rule in rules, f"rule {rule} not demonstrated"
        # Spot check the scenarios behind the rules.
        fatima = _student_id(db, "fatima.noor@student.palms.edu")
        fatima_rules = set(
            db.scalars(
                select(Recommendation.rule_code).where(
                    Recommendation.student_id == fatima,
                    Recommendation.status == "active",
                )
            ).all()
        )
        assert fatima_rules == {"LOW_PERFORMANCE", "REPEATED_DIFFICULTY"}
        ali = _student_id(db, "ali.raza@student.palms.edu")
        ali_rules = set(
            db.scalars(
                select(Recommendation.rule_code).where(
                    Recommendation.student_id == ali,
                    Recommendation.status == "active",
                )
            ).all()
        )
        assert ali_rules == {"MASTERY_ACHIEVED", "HIGH_ACHIEVEMENT"}
    finally:
        db.close()


def test_research_records(demo):
    db = TestingSession()
    try:
        sessions = db.scalars(select(ResearchSession)).all()
        assert len(sessions) == 3
        changes = sorted(s.score_change for s in sessions)
        assert changes == [7.0, 18.0, 23.0]
        for s in sessions:
            assert s.score_change == round(s.post_test_score - s.pre_test_score, 2)
            assert s.learning_period
            assert s.notes
    finally:
        db.close()


def test_complete_workflow_via_api(demo):
    h_t = _headers("sana.malik@palms.edu", "demo1234")
    h_s = _headers("fatima.noor@student.palms.edu", "demo1234")
    db = TestingSession()
    try:
        class_id = db.scalar(
            select(SchoolClass.id).where(SchoolClass.name == "7-A")
        )
        fatima_id = _student_id(db, "fatima.noor@student.palms.edu")
    finally:
        db.close()
    # Teacher reviews progress: class report, student feedback history.
    r = client.get(
        f"/api/v1/classes/{class_id}/reports/class-progress", headers=h_t
    )
    assert r.status_code == 200, r.text
    assert len(r.json()) == 20  # 5 students x 4 topics
    r = client.get(
        f"/api/v1/classes/{class_id}/feedback-history",
        params={"student_id": fatima_id},
        headers=h_t,
    )
    assert r.status_code == 200, r.text
    rows = r.json()
    assert len(rows) == 2
    assert rows[0]["teacher_comment"]
    assert rows[0]["intervention"] == "Teacher support requested"
    # Student sees her own recommendations and learning path.
    r = client.get("/api/v1/recommendations", headers=h_s)
    assert r.status_code == 200, r.text
    assert {x["rule_code"] for x in r.json()} == {
        "LOW_PERFORMANCE",
        "REPEATED_DIFFICULTY",
    }
    r = client.get(f"/api/v1/classes/{class_id}/learning-path", headers=h_s)
    assert r.status_code == 200, r.text
    assert r.json()["current_activity"]["rule_code"] == "REPEATED_DIFFICULTY"


def test_seed_is_idempotent(demo):
    db = TestingSession()
    try:
        before = db.scalar(select(func.count(Attempt.id)))
    finally:
        db.close()
    seed_demo.run()
    db = TestingSession()
    try:
        after = db.scalar(select(func.count(Attempt.id)))
        assert before == after
        users = db.scalar(
            select(func.count(User.id)).where(User.email.like("%@student.palms.edu"))
        )
        assert users == 5
    finally:
        db.close()
