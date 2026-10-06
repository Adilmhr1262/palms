"""Realistic demonstration data for the complete PALMS workflow.

Seeds one institution-neutral demo: 1 admin, 2 teachers, 5 students, the
Mathematics Foundations course with lessons, resources, and assessments per
topic, a class with enrollments, graded assessment attempts that exercise
auto-grading, teacher grading, mastery updates, and recommendations, plus
research evaluation records.

Five student scenarios are built in:
  Ali Raza     high performer      Fractions 87.5% -> 100%  (mastery + enrichment)
  Fatima Noor  needs support       Fractions 25% -> 37.5%   (low performance + repeated difficulty)
  Usman Tariq  improving           Decimals 16.7% -> 66.7%  (developing)
  Hina Shah    incomplete learner  one lesson done, no attempts
  Danish Ali   proficient          Decimals 83.3%           (mastery achieved)

All five recommendation rules end up demonstrated. Attempts are created
through the real grading services (auto_grade_attempt, grade_short_answer,
finalize_attempt, recalculate_mastery), so seeding exercises the same code
paths as the application.

Idempotent: safe to run repeatedly; existing rows are skipped by email,
title, or natural key. Demo password for every account is "demo1234".
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import security
from app.core.config import settings
from app.db.session import get_session_factory

SessionLocal = None


def _session() -> Session:
    return get_session_factory()()

from app.models.academic import Course, CourseTeacher, Enrollment, SchoolClass
from app.models.assessment import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Attempt,
    AttemptStatus,
    Question,
    QuestionType,
)
from app.models.content import Lesson, Resource, Topic
from app.models.recommendation import LessonProgress
from app.models.research import ResearchSession, compute_score_change
from app.models.user import User, UserRole
from app.seed.seed_content import COURSE_TITLE, run as seed_base
from app.services.grading import (
    auto_grade_attempt,
    finalize_attempt,
    grade_short_answer,
)
from app.services.mastery import recalculate_mastery

DEMO_PASSWORD = "demo1234"

USERS = [
    ("Ayesha Khan", "admin@palms.edu", UserRole.admin),
    ("Sana Malik", "sana.malik@palms.edu", UserRole.teacher),
    ("Imran Sheikh", "imran.sheikh@palms.edu", UserRole.teacher),
    ("Ali Raza", "ali.raza@student.palms.edu", UserRole.student),
    ("Fatima Noor", "fatima.noor@student.palms.edu", UserRole.student),
    ("Usman Tariq", "usman.tariq@student.palms.edu", UserRole.student),
    ("Hina Shah", "hina.shah@student.palms.edu", UserRole.student),
    ("Danish Ali", "danish.ali@student.palms.edu", UserRole.student),
]

CLASS_NAME = "7-A"
CLASS_YEAR = "2026"

ASSESSMENTS = {
    "Decimals": {
        "title": "Decimals check",
        "instructions": "Answer each question in order. You may go back and change answers before submitting.",
        "questions": [
            {
                "qtype": QuestionType.mcq,
                "prompt": "Which decimal equals 3/4?",
                "options": ["0.34", "0.75", "0.43", "7.5"],
                "correct_option": 1,
                "points": 2,
            },
            {
                "qtype": QuestionType.true_false,
                "prompt": "0.5 and 0.50 have different values.",
                "correct_option": 1,
                "points": 1,
            },
            {
                "qtype": QuestionType.short_answer,
                "prompt": "Explain how to convert 0.125 to a fraction in lowest terms.",
                "model_answer": (
                    "0.125 means 125 thousandths, or 125/1000. "
                    "Divide numerator and denominator by 125 to get 1/8."
                ),
                "points": 3,
            },
        ],
    },
    "Percentages": {
        "title": "Percentages check",
        "instructions": "Answer each question in order. You may go back and change answers before submitting.",
        "questions": [
            {
                "qtype": QuestionType.mcq,
                "prompt": "What is 25% of 200?",
                "options": ["25", "50", "75", "100"],
                "correct_option": 1,
                "points": 2,
            },
            {
                "qtype": QuestionType.true_false,
                "prompt": "50% is the same as one half.",
                "correct_option": 0,
                "points": 1,
            },
            {
                "qtype": QuestionType.short_answer,
                "prompt": "A shop offers 20% off a Rs 1,500 jacket. Show how to find the sale price.",
                "model_answer": (
                    "20% of 1,500 is 0.20 x 1,500 = 300. "
                    "Subtract from the price: 1,500 - 300 = Rs 1,200."
                ),
                "points": 3,
            },
        ],
    },
    "Basic Algebra": {
        "title": "Basic Algebra check",
        "instructions": "Answer each question in order. You may go back and change answers before submitting.",
        "questions": [
            {
                "qtype": QuestionType.mcq,
                "prompt": "If x + 7 = 15, what is x?",
                "options": ["7", "8", "22", "105"],
                "correct_option": 1,
                "points": 2,
            },
            {
                "qtype": QuestionType.true_false,
                "prompt": "In the expression 3x + 2, x is called a coefficient.",
                "correct_option": 1,
                "points": 1,
            },
            {
                "qtype": QuestionType.short_answer,
                "prompt": "Solve 5x = 35 and explain each step.",
                "model_answer": (
                    "Divide both sides by 5, the inverse of multiplying by 5. "
                    "x = 7. Check: 5 x 7 = 35."
                ),
                "points": 3,
            },
        ],
    },
}

RESOURCES = {
    "Fractions": (
        "Fractions Study Guide.txt",
        "Fractions study guide\n\n"
        "1. A fraction a/b means a parts out of b equal parts.\n"
        "2. Multiply or divide top and bottom by the same number to get an equivalent fraction.\n"
        "3. Always simplify answers to lowest terms.\n"
        "4. To add fractions, first find a common denominator.\n",
    ),
    "Decimals": (
        "Decimals Study Guide.txt",
        "Decimals study guide\n\n"
        "1. Places right of the point: tenths, hundredths, thousandths.\n"
        "2. Compare digit by digit from the left after lining up the points.\n"
        "3. Convert a fraction to a decimal by dividing numerator by denominator.\n"
        "4. Memorize: 1/2 = 0.5, 1/4 = 0.25, 3/4 = 0.75, 1/5 = 0.2.\n",
    ),
    "Percentages": (
        "Percentages Study Guide.txt",
        "Percentages study guide\n\n"
        "1. Percent means per hundred: 37% = 37/100 = 0.37.\n"
        "2. Percent to decimal: move the point two places left.\n"
        "3. To find x% of a quantity, multiply by x/100.\n"
        "4. Estimate first: 20% of 450 is about 450/5 = 90.\n",
    ),
    "Basic Algebra": (
        "Basic Algebra Study Guide.txt",
        "Basic algebra study guide\n\n"
        "1. A variable stands for an unknown number.\n"
        "2. Translate words to symbols: 'twice a number plus three' is 2x + 3.\n"
        "3. Solve with inverse operations, keeping both sides balanced.\n"
        "4. Always check by substituting the answer back.\n",
    ),
}

# (student email, topic title, days ago, mcq1 correct?, mcq2 correct?,
#  tf correct?, short answer text, short answer points, teacher comment)
ATTEMPTS = [
    (
        "ali.raza@student.palms.edu", "Fractions", 12, True, True, True,
        "Multiplying top and bottom by the same number cuts each part into "
        "smaller equal pieces and counts more of them, so the amount stays the same.",
        2, "Clear explanation. Tighten the wording on 'same factor'.",
    ),
    (
        "ali.raza@student.palms.edu", "Fractions", 9, True, True, True,
        "If you multiply the numerator and denominator by k, each original "
        "part is split into k smaller parts and you take k times as many, "
        "so the covered amount is unchanged.",
        3, "Excellent, precise reasoning.",
    ),
    (
        "fatima.noor@student.palms.edu", "Fractions", 11, True, False, False,
        "I do not know.", 0,
        "Please review the worked examples on equivalent fractions.",
    ),
    (
        "fatima.noor@student.palms.edu", "Fractions", 7, True, False, True,
        "Because you multiply both numbers.", 0,
        "This restates the question. Explain why the value stays the same.",
    ),
    (
        "usman.tariq@student.palms.edu", "Decimals", 10, False, False, False,
        "You times both by 8.", 1,
        "Partial credit: you named the factor. Now explain why it works.",
    ),
    (
        "usman.tariq@student.palms.edu", "Decimals", 5, True, True, True,
        "0.125 means 125 thousandths, so 125/1000. Both divide by 125, giving 1/8.",
        1, "Better. Add the diagram argument next time.",
    ),
    (
        "danish.ali@student.palms.edu", "Decimals", 8, True, True, True,
        "0.125 = 125/1000. Divide top and bottom by 125 to get 1/8.", 2,
        "Good steps. Reduce 125/1000 fully to 1/8.",
    ),
]

# (student email, topic title, lesson position, days ago)
LESSON_COMPLETIONS = [
    ("ali.raza@student.palms.edu", "Fractions", 1, 12),
    ("ali.raza@student.palms.edu", "Fractions", 2, 11),
    ("ali.raza@student.palms.edu", "Fractions", 3, 10),
    ("fatima.noor@student.palms.edu", "Fractions", 1, 11),
    ("usman.tariq@student.palms.edu", "Decimals", 1, 10),
    ("usman.tariq@student.palms.edu", "Decimals", 2, 9),
    ("hina.shah@student.palms.edu", "Fractions", 1, 6),
    ("danish.ali@student.palms.edu", "Decimals", 1, 8),
]

# (student email, pre, post, learning period, notes)
RESEARCH = [
    ("ali.raza@student.palms.edu", 68.0, 91.0, "6 weeks",
     "Completed all practice worksheets."),
    ("fatima.noor@student.palms.edu", 31.0, 38.0, "6 weeks",
     "Attended the support sessions."),
    ("usman.tariq@student.palms.edu", 40.0, 58.0, "6 weeks",
     "Retook the Decimals check after review."),
]

def _user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def seed_users(db: Session) -> dict[str, User]:
    users: dict[str, User] = {}
    for name, email, role in USERS:
        user = _user_by_email(db, email)
        if user is None:
            user = User(
                full_name=name,
                email=email,
                password_hash=security.hash_password(DEMO_PASSWORD),
                role=role,
                is_active=True,
            )
            db.add(user)
            db.flush()
            print(f"Seed demo: user {email} created.")
        users[email] = user
    return users


def seed_course_teachers(db: Session, users: dict[str, User]) -> None:
    course = db.scalar(select(Course).where(Course.title == COURSE_TITLE))
    for email in ("sana.malik@palms.edu", "imran.sheikh@palms.edu"):
        teacher = users[email]
        existing = db.scalar(
            select(CourseTeacher).where(
                CourseTeacher.course_id == course.id,
                CourseTeacher.teacher_id == teacher.id,
            )
        )
        if existing is None:
            db.add(CourseTeacher(course_id=course.id, teacher_id=teacher.id))
    db.flush()



def _course_topics(db: Session) -> dict[str, Topic]:
    course = db.scalar(select(Course).where(Course.title == COURSE_TITLE))
    topics = db.scalars(
        select(Topic).where(Topic.course_id == course.id)
    ).all()
    return {t.title: t for t in topics}


def seed_assessments(db: Session) -> None:
    topics = _course_topics(db)
    for topic_title, data in ASSESSMENTS.items():
        topic = topics.get(topic_title)
        if topic is None:
            continue
        existing = db.scalar(
            select(Assessment).where(
                Assessment.topic_id == topic.id,
                Assessment.title == data["title"],
            )
        )
        if existing is not None:
            continue
        questions = []
        for q in data["questions"]:
            question = Question(
                topic_id=topic.id,
                qtype=q["qtype"],
                prompt=q["prompt"],
                options=q.get("options"),
                correct_option=q.get("correct_option"),
                model_answer=q.get("model_answer"),
                points=q["points"],
            )
            db.add(question)
            questions.append(question)
        db.flush()
        assessment = Assessment(
            topic_id=topic.id,
            title=data["title"],
            instructions=data["instructions"],
        )
        db.add(assessment)
        db.flush()
        for position, question in enumerate(questions, start=1):
            db.add(
                AssessmentQuestion(
                    assessment_id=assessment.id,
                    question_id=question.id,
                    position=position,
                )
            )
        assessment.is_published = True
        db.flush()
        print(f"Seed demo: assessment '{data['title']}' created.")


def seed_resources(db: Session) -> None:
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    topics = _course_topics(db)
    for topic_title, (file_name, text) in RESOURCES.items():
        topic = topics.get(topic_title)
        if topic is None:
            continue
        lesson = db.scalar(
            select(Lesson).where(
                Lesson.topic_id == topic.id, Lesson.position == 1
            )
        )
        if lesson is None:
            continue
        existing = db.scalar(
            select(Resource).where(
                Resource.lesson_id == lesson.id,
                Resource.file_name == file_name,
            )
        )
        if existing is not None:
            continue
        stored_name = f"demo-{topic.position}-{file_name.replace(' ', '-').lower()}"
        path = upload_dir / stored_name
        path.write_text(text, encoding="utf-8")
        db.add(
            Resource(
                lesson_id=lesson.id,
                file_name=file_name,
                stored_path=stored_name,
                mime_type="text/plain",
                size_bytes=path.stat().st_size,
            )
        )
        db.flush()
        print(f"Seed demo: resource '{file_name}' attached to '{lesson.title}'.")


def seed_class(db: Session, users: dict[str, User]) -> SchoolClass:
    course = db.scalar(select(Course).where(Course.title == COURSE_TITLE))
    teacher = users["sana.malik@palms.edu"]
    class_ = db.scalar(
        select(SchoolClass).where(
            SchoolClass.name == CLASS_NAME,
            SchoolClass.academic_year == CLASS_YEAR,
        )
    )
    if class_ is None:
        class_ = SchoolClass(
            name=CLASS_NAME,
            academic_year=CLASS_YEAR,
            course_id=course.id,
            teacher_id=teacher.id,
        )
        db.add(class_)
        db.flush()
        print(f"Seed demo: class {CLASS_NAME} created.")
    for name, email, role in USERS:
        if role != UserRole.student:
            continue
        student = users[email]
        existing = db.scalar(
            select(Enrollment).where(
                Enrollment.class_id == class_.id,
                Enrollment.student_id == student.id,
            )
        )
        if existing is None:
            db.add(Enrollment(class_id=class_.id, student_id=student.id))
    db.flush()
    return class_


def _assessment_by_topic(db: Session, topic_title: str) -> Assessment:
    topic = _course_topics(db)[topic_title]
    if topic_title == "Fractions":
        title = "Fractions check"
    else:
        title = ASSESSMENTS[topic_title]["title"]
    return db.scalar(
        select(Assessment).where(
            Assessment.topic_id == topic.id, Assessment.title == title
        )
    )


def seed_attempts(db: Session, users: dict[str, User]) -> None:
    grader = users["sana.malik@palms.edu"]
    # Group rows by student+topic so re-runs only seed the missing attempts.
    groups: dict[tuple[str, str], list[tuple]] = {}
    for row in ATTEMPTS:
        groups.setdefault((row[0], row[1]), []).append(row)
    for (email, topic_title), rows in groups.items():
        student = users[email]
        assessment = _assessment_by_topic(db, topic_title)
        have = db.scalar(
            select(func.count(Attempt.id)).where(
                Attempt.assessment_id == assessment.id,
                Attempt.student_id == student.id,
            )
        )
        for row in rows[have:]:
            _seed_attempt(db, grader, student, assessment, row)


def _seed_attempt(
    db: Session,
    grader: User,
    student: User,
    assessment: Assessment,
    row: tuple,
) -> None:
    (
        _email, _topic, days_ago, mcq1_ok, mcq2_ok, tf_ok,
        sa_text, sa_points, comment,
    ) = row
    questions = [
        link.question
        for link in sorted(
            assessment.questions, key=lambda link: link.position
        )
    ]
    attempt = Attempt(
        assessment_id=assessment.id,
        student_id=student.id,
        status=AttemptStatus.in_progress,
    )
    db.add(attempt)
    db.flush()
    when = datetime.now(timezone.utc) - timedelta(days=days_ago)
    attempt.started_at = when
    closed = [
        q for q in questions if q.qtype != QuestionType.short_answer
    ]
    for question, correct in zip(closed, (mcq1_ok, mcq2_ok, tf_ok)):
        option = (
            question.correct_option
            if correct
            else (question.correct_option + 1) % len(question.options or [0, 1])
        )
        db.add(
            Answer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option=option,
            )
        )
    sa_question = next(
        q for q in questions if q.qtype == QuestionType.short_answer
    )
    db.add(
        Answer(
            attempt_id=attempt.id,
            question_id=sa_question.id,
            student_text=sa_text,
        )
    )
    db.flush()
    # Same path as the application: submit, auto-grade, teacher grades the
    # short answer, finalize, then recalculate mastery (which runs the
    # recommendation engine).
    attempt.status = AttemptStatus.submitted
    attempt.submitted_at = when
    attempt.max_score = sum(q.points for q in questions)
    auto_grade_attempt(db, attempt)
    sa_answer = db.scalar(
        select(Answer).where(
            Answer.attempt_id == attempt.id,
            Answer.question_id == sa_question.id,
        )
    )
    grade_short_answer(db, sa_answer, grader.id, sa_points, comment)
    if finalize_attempt(db, attempt):
        recalculate_mastery(db, student.id, assessment.topic_id)
    db.flush()
    print(
        f"Seed demo: {student.full_name} attempted "
            f"'{assessment.title}' ({attempt.total_score}/{attempt.max_score})."
        )


def seed_lesson_progress(db: Session, users: dict[str, User]) -> None:
    topics = _course_topics(db)
    for email, topic_title, position, days_ago in LESSON_COMPLETIONS:
        student = users[email]
        lesson = db.scalar(
            select(Lesson).where(
                Lesson.topic_id == topics[topic_title].id,
                Lesson.position == position,
            )
        )
        existing = db.scalar(
            select(LessonProgress).where(
                LessonProgress.student_id == student.id,
                LessonProgress.lesson_id == lesson.id,
            )
        )
        if existing is None:
            db.add(
                LessonProgress(
                    student_id=student.id,
                    lesson_id=lesson.id,
                    completed_at=datetime.now(timezone.utc)
                    - timedelta(days=days_ago),
                )
            )
    db.flush()


def seed_research(db: Session, users: dict[str, User], class_: SchoolClass) -> None:
    course = db.scalar(select(Course).where(Course.title == COURSE_TITLE))
    for email, pre, post, period, notes in RESEARCH:
        student = users[email]
        existing = db.scalar(
            select(ResearchSession).where(
                ResearchSession.student_id == student.id,
                ResearchSession.class_id == class_.id,
            )
        )
        if existing is not None:
            continue
        db.add(
            ResearchSession(
                student_id=student.id,
                class_id=class_.id,
                course_id=course.id,
                pre_test_score=pre,
                post_test_score=post,
                learning_period=period,
                notes=notes,
                score_change=compute_score_change(pre, post),
            )
        )
        db.flush()
        print(f"Seed demo: research record for {student.full_name} created.")


def run() -> None:
    db: Session = _session()
    try:
        seed_base()
        users = seed_users(db)
        seed_course_teachers(db, users)
        seed_assessments(db)
        seed_resources(db)
        class_ = seed_class(db, users)
        seed_attempts(db, users)
        seed_lesson_progress(db, users)
        seed_research(db, users, class_)
        db.commit()
        print("Seed demo: complete.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
