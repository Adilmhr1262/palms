from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.access import (
    can_manage_course,
    can_view_class,
    is_admin,
    student_course_ids,
)
from app.core.deps import get_current_user, get_db, require_teacher
from app.models.academic import Enrollment, SchoolClass
from app.models.assessment import Assessment
from app.models.content import Lesson, Topic
from app.models.mastery import Mastery
from app.models.recommendation import (
    LessonProgress,
    Recommendation,
    RecommendationStatus,
)
from app.models.user import User, UserRole
from app.schemas.recommendation import (
    LearningPathRead,
    PathLesson,
    PathTopic,
    RecommendationRead,
    RecommendationReviewInput,
)
from app.services.recommendations import rule_priority

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _read(rec: Recommendation) -> RecommendationRead:
    read = RecommendationRead.model_validate(rec)
    read.student_name = rec.student.full_name
    read.topic_title = rec.topic.title
    read.course_title = rec.topic.course.title
    return read


def _teacher_course_ids(db: Session, user: User) -> set[int]:
    from app.models.academic import CourseTeacher

    rows = db.scalars(
        select(CourseTeacher.course_id).where(
            CourseTeacher.teacher_id == user.id
        )
    ).all()
    return set(rows)


@router.get("", response_model=list[RecommendationRead])
def list_recommendations(
    course_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Students see their own recommendations. Teachers see the active
    recommendations for the courses they teach, highest priority first."""
    if user.role == UserRole.student:
        stmt = (
            select(Recommendation)
            .where(Recommendation.student_id == user.id)
            .order_by(Recommendation.created_at.desc(), Recommendation.id.desc())
        )
        recs = db.scalars(stmt).all()
    elif user.role == UserRole.teacher or is_admin(user):
        if user.role == UserRole.teacher:
            course_ids = _teacher_course_ids(db, user)
        else:
            course_ids = None
        stmt = (
            select(Recommendation)
            .join(Topic, Topic.id == Recommendation.topic_id)
            .where(Recommendation.status == RecommendationStatus.active)
        )
        if course_ids is not None:
            if course_id is not None and course_id not in course_ids:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not your course.",
                )
            stmt = stmt.where(Topic.course_id.in_(course_ids))
        if course_id is not None:
            stmt = stmt.where(Topic.course_id == course_id)
        stmt = stmt.order_by(
            Recommendation.created_at.desc(), Recommendation.id.desc()
        )
        recs = db.scalars(stmt).all()
        recs.sort(key=lambda r: rule_priority(r.rule_code))
    else:
        recs = []
    return [_read(r) for r in recs]


def _get_visible(
    db: Session, user: User, rec_id: int
) -> Recommendation:
    rec = db.get(Recommendation, rec_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found.",
        )
    course_id = rec.topic.course_id
    if user.role == UserRole.student and rec.student_id == user.id:
        return rec
    if can_manage_course(db, user, course_id):
        return rec
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed."
    )


@router.get("/{rec_id}", response_model=RecommendationRead)
def get_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return _read(_get_visible(db, user, rec_id))


@router.post("/{rec_id}/dismiss", response_model=RecommendationRead)
def dismiss_recommendation(
    rec_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """The owning student dismisses a recommendation. The row stays
    stored with status dismissed."""
    rec = db.get(Recommendation, rec_id)
    if rec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recommendation not found.",
        )
    if not (user.role == UserRole.student and rec.student_id == user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed."
        )
    rec.status = RecommendationStatus.dismissed
    db.commit()
    db.refresh(rec)
    return _read(rec)


@router.post("/{rec_id}/review", response_model=RecommendationRead)
def review_recommendation(
    rec_id: int,
    body: RecommendationReviewInput,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    """A course teacher adds a note and marks the recommendation
    reviewed (completed)."""
    rec = _get_visible(db, user, rec_id)
    if body.teacher_note:
        rec.teacher_note = body.teacher_note
    rec.status = RecommendationStatus.completed
    db.commit()
    db.refresh(rec)
    return _read(rec)


lessons_router = APIRouter(tags=["lessons"])


@lessons_router.post("/lessons/{lesson_id}/complete", status_code=status.HTTP_200_OK)
def complete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """An enrolled student marks a lesson complete. Idempotent."""
    if user.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed."
        )
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found."
        )
    course_id = lesson.topic.course_id
    if course_id not in student_course_ids(db, user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enrolled."
        )
    existing = db.scalar(
        select(LessonProgress).where(
            LessonProgress.student_id == user.id,
            LessonProgress.lesson_id == lesson_id,
        )
    )
    if existing is None:
        db.add(
            LessonProgress(student_id=user.id, lesson_id=lesson_id)
        )
        db.commit()
    return {"lesson_id": lesson_id, "completed": True}


path_router = APIRouter(tags=["learning-path"])


@path_router.get("/classes/{class_id}/learning-path", response_model=LearningPathRead)
def learning_path(
    class_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """Document-style learning path: course -> topics -> lessons, with
    completed lessons, the current recommended activity, and the next
    available topic."""
    class_ = db.get(SchoolClass, class_id)
    if class_ is None or class_.course_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Class or course not found.",
        )
    if not can_view_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed."
        )
    course = class_.course
    student_id = user.id if user.role == UserRole.student else None

    topics = db.scalars(
        select(Topic)
        .where(Topic.course_id == course.id)
        .order_by(Topic.position, Topic.id)
    ).all()

    completed_lesson_ids: set[int] = set()
    mastery_by_topic: dict[int, Mastery] = {}
    active_recs: list[Recommendation] = []
    if student_id is not None:
        completed_lesson_ids = set(
            db.scalars(
                select(LessonProgress.lesson_id).where(
                    LessonProgress.student_id == student_id
                )
            ).all()
        )
        mastery_by_topic = {
            m.topic_id: m
            for m in db.scalars(
                select(Mastery).where(Mastery.student_id == student_id)
            ).all()
        }
        active_recs = db.scalars(
            select(Recommendation).where(
                Recommendation.student_id == student_id,
                Recommendation.status == RecommendationStatus.active,
            )
        ).all()
        active_recs.sort(key=lambda r: rule_priority(r.rule_code))

    path_topics = []
    next_topic_id: int | None = None
    for t in topics:
        lessons = sorted(t.lessons, key=lambda l: (l.position, l.id))
        m = mastery_by_topic.get(t.id)
        mastered = m is not None and m.status is not None and m.status.value in (
            "proficient",
            "mastered",
        )
        if next_topic_id is None and not mastered:
            next_topic_id = t.id
        path_topics.append(
            PathTopic(
                id=t.id,
                title=t.title,
                position=t.position,
                mastery_status=m.status.value if m and m.status else None,
                latest_score=m.latest_score if m else None,
                lessons=[
                    PathLesson(
                        id=l.id,
                        title=l.title,
                        position=l.position,
                        completed=l.id in completed_lesson_ids,
                    )
                    for l in lessons
                ],
            )
        )

    return LearningPathRead(
        class_id=class_.id,
        class_name=class_.name,
        course_id=course.id,
        course_title=course.title,
        topics=path_topics,
        current_activity=_read(active_recs[0]) if active_recs else None,
        next_topic_id=next_topic_id,
    )
