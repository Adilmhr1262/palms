"""Grading: automatic marking of closed questions, teacher marking of
short answers, and attempt finalization.

An attempt becomes "graded" only when every question in the assessment
has a final score. Short answers stay pending until a teacher grades them.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import (
    Answer,
    AssessmentQuestion,
    Attempt,
    AttemptStatus,
    QuestionType,
)


def _answer_for(db: Session, attempt: Attempt, question_id: int) -> Answer | None:
    return db.scalar(
        select(Answer).where(
            Answer.attempt_id == attempt.id,
            Answer.question_id == question_id,
        )
    )


def auto_grade_attempt(db: Session, attempt: Attempt) -> None:
    """Mark multiple choice and true/false answers.

    Every question gets an answer row: unanswered closed questions score
    zero, and short answers are left pending for the teacher. Safe to run
    more than once; already-graded rows keep their scores.
    """
    for link in attempt.assessment.questions:
        question = link.question
        answer = _answer_for(db, attempt, question.id)
        if answer is None:
            answer = Answer(
                attempt_id=attempt.id,
                question_id=question.id,
            )
            db.add(answer)
            db.flush()
        if question.qtype == QuestionType.short_answer:
            continue
        if answer.points_earned is not None:
            continue  # a teacher or earlier run already scored this
        if (
            answer.selected_option is not None
            and answer.selected_option == question.correct_option
        ):
            answer.is_correct = True
            answer.points_earned = question.points
        else:
            answer.is_correct = False
            answer.points_earned = 0
    db.flush()


def finalize_attempt(db: Session, attempt: Attempt) -> bool:
    """Mark the attempt graded when every question has a final score.

    Returns True when the attempt moved to graded.
    """
    total = 0
    for link in attempt.assessment.questions:
        answer = _answer_for(db, attempt, link.question_id)
        if answer is None or answer.points_earned is None:
            return False
        total += answer.points_earned
    attempt.status = AttemptStatus.graded
    attempt.total_score = total
    db.flush()
    return True


def grade_short_answer(
    db: Session,
    answer: Answer,
    teacher_id: int,
    points_earned: int,
    teacher_comment: str | None,
) -> Answer:
    """Record a teacher's grade for a short answer."""
    question = answer.question
    if points_earned < 0 or points_earned > question.points:
        raise ValueError(
            f"Points must be between 0 and {question.points}."
        )
    answer.points_earned = points_earned
    answer.is_correct = points_earned == question.points
    answer.teacher_comment = teacher_comment.strip() if teacher_comment else None
    answer.graded_by = teacher_id
    answer.graded_at = datetime.now(timezone.utc)
    db.flush()
    return answer
