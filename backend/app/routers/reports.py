"""Academic reports, feedback history, and CSV exports.

- Teachers (and admins) read class progress, student progress, and a
  student's feedback history for classes they manage.
- Students read only their own feedback; private teacher notes and other
  students' data are never exposed.
- CSV exports are teacher/admin only; students receive 403.
"""
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import get_current_user, require_teacher
from app.db.session import get_db
from app.models.academic import Enrollment, SchoolClass
from app.models.assessment import Answer, Assessment, Attempt, AttemptStatus
from app.models.content import Lesson, Topic
from app.models.mastery import Mastery
from app.models.recommendation import LessonProgress, Recommendation
from app.models.user import User
from app.schemas.reporting import (
    ClassProgressRow,
    FeedbackHistoryRow,
    StudentFeedbackRow,
    StudentProgressRow,
)

router = APIRouter(tags=["reports"])


def _get_class_or_404(db: Session, class_id: int) -> SchoolClass:
    class_ = db.get(SchoolClass, class_id)
    if class_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found."
        )
    return class_


def _require_manage_class(db: Session, user: User, class_: SchoolClass) -> None:
    if not access.can_manage_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the class teacher can access these reports.",
        )


def _class_topics(db: Session, class_: SchoolClass):
    if class_.course_id is None:
        return []
    return db.scalars(
        select(Topic)
        .where(Topic.course_id == class_.course_id)
        .order_by(Topic.position)
    ).all()


def _class_students(db: Session, class_id: int):
    return db.scalars(
        select(User)
        .join(Enrollment, Enrollment.student_id == User.id)
        .where(Enrollment.class_id == class_id)
        .order_by(User.full_name)
    ).all()


def _score_text(attempt: Attempt) -> str:
    if attempt.total_score is None or not attempt.max_score:
        return "-"
    pct = round(100 * attempt.total_score / attempt.max_score)
    return f"{attempt.total_score} / {attempt.max_score} ({pct}%)"


def _teacher_comments(db: Session, attempt_id: int) -> str | None:
    rows = db.scalars(
        select(Answer.teacher_comment)
        .where(Answer.attempt_id == attempt_id, Answer.teacher_comment.is_not(None))
        .order_by(Answer.id)
    ).all()
    comments = [c for c in rows if c and c.strip()]
    return "; ".join(comments) if comments else None


@router.get(
    "/classes/{class_id}/reports/class-progress",
    response_model=list[ClassProgressRow],
)
def class_progress(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    topics = _class_topics(db, class_)
    students = _class_students(db, class_id)
    mastery_map = {
        (m.student_id, m.topic_id): m
        for m in db.scalars(
            select(Mastery).where(
                Mastery.student_id.in_([s.id for s in students]),
                Mastery.topic_id.in_([t.id for t in topics]),
            )
        ).all()
    }
    rows = []
    for student in students:
        for topic in topics:
            m = mastery_map.get((student.id, topic.id))
            rows.append(
                ClassProgressRow(
                    student_id=student.id,
                    student_name=student.full_name,
                    topic_id=topic.id,
                    topic_title=topic.title,
                    attempts_count=m.attempts_count if m else 0,
                    latest_score=m.latest_score if m else None,
                    best_score=m.best_score if m else None,
                    mastery_status=m.status.value if m and m.status else None,
                )
            )
    return rows


@router.get(
    "/classes/{class_id}/reports/student-progress",
    response_model=list[StudentProgressRow],
)
def student_progress(
    class_id: int,
    student_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    class_ = _get_class_or_404(db, class_id)
    if user.role == "student" and user.id != student_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Students can only view their own progress.",
        )
    if user.role != "student":
        _require_manage_class(db, user, class_)
    if not access.is_enrolled(db, student_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student is not enrolled in this class.",
        )
    topics = _class_topics(db, class_)
    rows = []
    for topic in topics:
        lesson_ids = db.scalars(
            select(Lesson.id).where(Lesson.topic_id == topic.id)
        ).all()
        completed = (
            db.scalar(
                select(func.count(LessonProgress.id)).where(
                    LessonProgress.student_id == student_id,
                    LessonProgress.lesson_id.in_(lesson_ids),
                )
            )
            if lesson_ids
            else 0
        )
        attempt_ids = db.scalars(
            select(Attempt.id)
            .join(Assessment, Assessment.id == Attempt.assessment_id)
            .where(
                Attempt.student_id == student_id,
                Assessment.topic_id == topic.id,
                Attempt.status == AttemptStatus.graded,
            )
        ).all()
        mastery = db.scalar(
            select(Mastery).where(
                Mastery.student_id == student_id, Mastery.topic_id == topic.id
            )
        )
        rows.append(
            StudentProgressRow(
                topic_id=topic.id,
                topic_title=topic.title,
                lessons_completed=completed or 0,
                lessons_total=len(lesson_ids),
                assessment_attempts=len(attempt_ids),
                latest_score=mastery.latest_score if mastery else None,
                mastery_status=(
                    mastery.status.value if mastery and mastery.status else None
                ),
            )
        )
    return rows


def _graded_attempts(db: Session, student_id: int, topic_ids: list[int]):
    return db.scalars(
        select(Attempt)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .where(
            Attempt.student_id == student_id,
            Assessment.topic_id.in_(topic_ids),
            Attempt.status == AttemptStatus.graded,
        )
        .order_by(Attempt.submitted_at.desc())
    ).all()


@router.get(
    "/classes/{class_id}/feedback-history",
    response_model=list[FeedbackHistoryRow],
)
def feedback_history(
    class_id: int,
    student_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    topics = _class_topics(db, class_)
    topic_map = {t.id: t for t in topics}
    course_title = class_.course.title if class_.course else ""
    attempts = _graded_attempts(db, student_id, list(topic_map))
    interventions = {
        r.topic_id: r
        for r in db.scalars(
            select(Recommendation)
            .where(
                Recommendation.student_id == student_id,
                Recommendation.topic_id.in_(list(topic_map)),
            )
            .order_by(Recommendation.created_at)
        ).all()
    }
    rows = []
    for attempt in attempts:
        assessment = attempt.assessment
        topic = topic_map.get(assessment.topic_id)
        rec = interventions.get(assessment.topic_id)
        rows.append(
            FeedbackHistoryRow(
                date=attempt.submitted_at,
                course_title=course_title,
                topic_title=topic.title if topic else "",
                assessment_title=assessment.title,
                score=_score_text(attempt),
                teacher_comment=_teacher_comments(db, attempt.id),
                intervention=rec.title if rec else None,
            )
        )
    return rows


@router.get("/feedback/my", response_model=list[StudentFeedbackRow])
def my_feedback(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic_ids = list(access.student_course_ids(db, user.id))
    topics = db.scalars(
        select(Topic).where(Topic.course_id.in_(topic_ids)) if topic_ids else select(Topic).where(False)
    ).all()
    topic_map = {t.id: t for t in topics}
    attempts = _graded_attempts(db, user.id, list(topic_map))
    suggestions = {}
    for r in db.scalars(
        select(Recommendation)
        .where(
            Recommendation.student_id == user.id,
            Recommendation.status == "active",
        )
        .order_by(Recommendation.created_at.desc())
    ).all():
        suggestions.setdefault(r.topic_id, r.message)
    rows = []
    for attempt in attempts:
        assessment = attempt.assessment
        topic = topic_map.get(assessment.topic_id)
        rows.append(
            StudentFeedbackRow(
                date=attempt.submitted_at,
                topic_title=topic.title if topic else "",
                assessment_title=assessment.title,
                score=_score_text(attempt),
                teacher_comment=_teacher_comments(db, attempt.id),
                suggestion=suggestions.get(assessment.topic_id),
            )
        )
    return rows


def _safe_cell(value: str) -> str:
    """Neutralize CSV formula injection: values starting with = + - @."""
    if value and value[0] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def _csv_response(filename: str, headers: list[str], rows: list[list]) -> Response:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(headers)
    for row in rows:
        writer.writerow([_safe_cell(c) if isinstance(c, str) else c for c in row])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _fmt_score(value: float | None) -> str:
    return "" if value is None else str(round(value, 2))


@router.get("/exports/mastery.csv")
def export_mastery_csv(
    class_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    progress = class_progress(class_id, db, user)
    rows = [
        [
            r.student_name,
            r.topic_title,
            r.attempts_count,
            _fmt_score(r.latest_score),
            _fmt_score(r.best_score),
            r.mastery_status or "",
        ]
        for r in progress
    ]
    return _csv_response(
        f"mastery-class-{class_id}.csv",
        ["Student", "Topic", "Attempts", "Latest score", "Best score", "Mastery status"],
        rows,
    )


@router.get("/exports/assessments.csv")
def export_assessments_csv(
    class_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    topics = _class_topics(db, class_)
    students = _class_students(db, class_id)
    topic_ids = [t.id for t in topics]
    student_ids = [s.id for s in students]
    attempts = db.scalars(
        select(Attempt)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .where(
            Attempt.student_id.in_(student_ids),
            Assessment.topic_id.in_(topic_ids),
            Attempt.status == AttemptStatus.graded,
        )
        .order_by(Attempt.submitted_at)
    ).all()
    name_map = {s.id: s.full_name for s in students}
    rows = [
        [
            name_map.get(a.student_id, ""),
            a.assessment.title,
            a.assessment.topic.title if a.assessment.topic else "",
            a.submitted_at.isoformat() if a.submitted_at else "",
            a.total_score if a.total_score is not None else "",
            a.max_score if a.max_score is not None else "",
            _teacher_comments(db, a.id) or "",
        ]
        for a in attempts
    ]
    return _csv_response(
        f"assessments-class-{class_id}.csv",
        ["Student", "Assessment", "Topic", "Submitted", "Score", "Max score", "Teacher comment"],
        rows,
    )


@router.get("/exports/research.csv")
def export_research_csv(
    class_id: int = Query(...),
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    from app.models.research import ResearchSession

    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    sessions = db.scalars(
        select(ResearchSession)
        .where(ResearchSession.class_id == class_id)
        .order_by(ResearchSession.created_at)
    ).all()
    name_map = {s.id: s.full_name for s in _class_students(db, class_id)}
    rows = [
        [
            s.student_id,
            name_map.get(s.student_id, ""),
            _fmt_score(s.pre_test_score),
            _fmt_score(s.post_test_score),
            s.learning_period or "",
            _fmt_score(s.score_change),
            (s.notes or "").replace("\n", " "),
        ]
        for s in sessions
    ]
    return _csv_response(
        f"research-class-{class_id}.csv",
        ["Student ID", "Student", "Pre-test score", "Post-test score",
         "Learning period", "Score change", "Notes"],
        rows,
    )
