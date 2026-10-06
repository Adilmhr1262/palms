from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import get_current_user, require_teacher
from app.db.session import get_db
from app.models.assessment import Question, QuestionType
from app.models.content import Topic
from app.schemas.assessment import QuestionCreate, QuestionRead, QuestionUpdate

router = APIRouter(tags=["question-bank"])


def _get_topic_or_404(db: Session, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found."
        )
    return topic


def _require_manage(db: Session, user, topic: Topic) -> None:
    if not access.can_manage_course(db, user, topic.course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can manage the question bank.",
        )


def _validate_mcq_options(options: list[str] | None, correct_option: int | None) -> list[str]:
    cleaned = [o.strip() for o in (options or []) if o.strip()]
    if len(cleaned) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Multiple choice needs at least two options.",
        )
    if len(cleaned) > 6:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Multiple choice allows at most six options.",
        )
    if correct_option is None or not 0 <= correct_option < len(cleaned):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Choose which option is correct.",
        )
    return cleaned


@router.get("/topics/{topic_id}/questions", response_model=list[QuestionRead])
def list_questions(
    topic_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    topic = _get_topic_or_404(db, topic_id)
    _require_manage(db, user, topic)
    return db.scalars(
        select(Question).where(Question.topic_id == topic.id).order_by(Question.id)
    ).all()


@router.post(
    "/topics/{topic_id}/questions",
    response_model=QuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_question(
    topic_id: int,
    body: QuestionCreate,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    topic = _get_topic_or_404(db, topic_id)
    _require_manage(db, user, topic)
    question = Question(
        topic_id=topic.id,
        qtype=body.qtype,
        prompt=body.prompt,
        options=body.options,
        correct_option=body.correct_option,
        model_answer=body.model_answer,
        points=body.points,
        created_by=user.id,
    )
    db.add(question)
    db.commit()
    db.refresh(question)
    return question


def _get_question_or_404(db: Session, question_id: int) -> Question:
    question = db.get(Question, question_id)
    if question is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found."
        )
    return question


@router.patch("/questions/{question_id}", response_model=QuestionRead)
def update_question(
    question_id: int,
    body: QuestionUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    question = _get_question_or_404(db, question_id)
    _require_manage(db, user, question.topic)
    if body.prompt is not None:
        question.prompt = body.prompt
    if question.qtype == QuestionType.mcq:
        if body.options is not None or body.correct_option is not None:
            options = body.options if body.options is not None else question.options
            correct = (
                body.correct_option
                if body.correct_option is not None
                else question.correct_option
            )
            question.options = _validate_mcq_options(options, correct)
            question.correct_option = correct
    elif question.qtype == QuestionType.true_false:
        if body.correct_option is not None and body.correct_option not in (0, 1):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="True/false needs a correct answer (true or false).",
            )
        if body.correct_option is not None:
            question.correct_option = body.correct_option
    else:
        if body.model_answer is not None:
            question.model_answer = body.model_answer.strip() or None
    if body.points is not None:
        question.points = body.points
    db.commit()
    db.refresh(question)
    return question


@router.delete("/questions/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    question = _get_question_or_404(db, question_id)
    _require_manage(db, user, question.topic)
    db.delete(question)
    db.commit()
