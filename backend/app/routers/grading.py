from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import get_current_user, require_teacher
from app.db.session import get_db
from app.models.assessment import (
    Answer,
    Assessment,
    Attempt,
    AttemptStatus,
    QuestionType,
)
from app.models.content import Topic
from app.models.mastery import Mastery
from app.models.user import User, UserRole
from app.schemas.assessment import (
    AnswerGraded,
    GradeAnswerInput,
    GradingQueueItem,
    MasteryRead,
)
from app.services.grading import finalize_attempt, grade_short_answer
from app.services.mastery import recalculate_mastery

router = APIRouter(tags=["grading"])


def _get_assessment_or_404(db: Session, assessment_id: int) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )
    return assessment


def _require_manage(db: Session, user: User, assessment: Assessment) -> None:
    if not access.can_manage_course(db, user, assessment.topic.course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can grade answers.",
        )


@router.get(
    "/assessments/{assessment_id}/grading-queue",
    response_model=list[GradingQueueItem],
)
def grading_queue(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    answers = db.scalars(
        select(Answer)
        .join(Attempt, Attempt.id == Answer.attempt_id)
        .where(
            Attempt.assessment_id == assessment.id,
            Attempt.status.in_(
                [AttemptStatus.submitted, AttemptStatus.graded]
            ),
        )
        .order_by(Attempt.submitted_at, Answer.id)
    ).all()
    items = []
    for answer in answers:
        if answer.question.qtype != QuestionType.short_answer:
            continue
        student = db.get(User, answer.attempt.student_id)
        items.append(
            GradingQueueItem(
                answer_id=answer.id,
                attempt_id=answer.attempt_id,
                student_id=answer.attempt.student_id,
                student_name=student.full_name if student else "",
                question_id=answer.question_id,
                question_prompt=answer.question.prompt,
                question_points=answer.question.points,
                student_text=answer.student_text,
                points_earned=answer.points_earned,
                teacher_comment=answer.teacher_comment,
                submitted_at=answer.attempt.submitted_at,
            )
        )
    return items


@router.post("/answers/{answer_id}/grade", response_model=AnswerGraded)
def grade_answer(
    answer_id: int,
    body: GradeAnswerInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    answer = db.get(Answer, answer_id)
    if answer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Answer not found."
        )
    attempt = answer.attempt
    _require_manage(db, user, attempt.assessment)
    if answer.question.qtype != QuestionType.short_answer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only short answers need teacher grading.",
        )
    if attempt.status == AttemptStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The student has not submitted this attempt yet.",
        )
    try:
        grade_short_answer(
            db,
            answer,
            teacher_id=user.id,
            points_earned=body.points_earned,
            teacher_comment=body.teacher_comment,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e)
        )
    if finalize_attempt(db, attempt):
        recalculate_mastery(db, attempt.student_id, attempt.assessment.topic_id)
    db.commit()
    db.refresh(answer)
    return AnswerGraded.model_validate(answer)


@router.get("/topics/{topic_id}/mastery", response_model=list[MasteryRead])
def topic_mastery(
    topic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found."
        )
    if not access.can_view_course(db, user, topic.course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course.",
        )
    query = select(Mastery).where(Mastery.topic_id == topic.id)
    if user.role == UserRole.student:
        query = query.where(Mastery.student_id == user.id)
    elif not access.can_manage_course(db, user, topic.course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can view mastery records.",
        )
    records = db.scalars(query.order_by(Mastery.updated_at.desc())).all()
    result = []
    for record in records:
        read = MasteryRead.model_validate(record)
        student = db.get(User, record.student_id)
        read.student_name = student.full_name if student else ""
        read.topic_title = topic.title
        result.append(read)
    return result
