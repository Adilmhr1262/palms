"""Mastery calculation: one record per student and topic.

Recalculated whenever an attempt becomes graded, whether through
automatic marking or a teacher grading a short answer.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, Attempt, AttemptStatus
from app.models.mastery import Mastery, MasteryStatus


def mastery_status(percent: float, threshold: int) -> MasteryStatus:
    """Map a percentage score to a mastery status.

    The topic's own mastery threshold is the line between developing and
    proficient; the outer bands are fixed. With the default threshold of
    70 this gives 0-49 needs support, 50-69 developing, 70-84 proficient,
    85-100 mastered.
    """
    if percent >= 85:
        return MasteryStatus.mastered
    if percent >= threshold:
        return MasteryStatus.proficient
    if percent >= 50:
        return MasteryStatus.developing
    return MasteryStatus.needs_support


def attempt_percent(attempt: Attempt) -> float | None:
    if attempt.total_score is None or not attempt.max_score:
        return None
    return round(attempt.total_score / attempt.max_score * 100, 1)


def recalculate_mastery(
    db: Session, student_id: int, topic_id: int
) -> Mastery | None:
    """Rebuild the mastery record from the student's graded attempts.

    Returns the record, or None when there are no graded attempts (any
    existing record is removed).
    """
    from app.models.content import Topic

    topic = db.get(Topic, topic_id)
    if topic is None:
        return None
    attempts = db.scalars(
        select(Attempt)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .where(
            Attempt.student_id == student_id,
            Assessment.topic_id == topic_id,
            Attempt.status == AttemptStatus.graded,
        )
        .order_by(Attempt.submitted_at, Attempt.id)
    ).all()
    record = db.scalar(
        select(Mastery).where(
            Mastery.student_id == student_id,
            Mastery.topic_id == topic_id,
        )
    )
    if not attempts:
        if record is not None:
            db.delete(record)
            db.flush()
        return None
    percents = [p for p in (attempt_percent(a) for a in attempts) if p is not None]
    if not percents:
        return record
    latest = percents[-1]
    if record is None:
        record = Mastery(student_id=student_id, topic_id=topic_id)
        db.add(record)
    record.attempts_count = len(attempts)
    record.latest_score = latest
    record.best_score = max(percents)
    record.status = mastery_status(latest, topic.mastery_threshold)
    db.flush()
    # Recommendations follow mastery: the rule engine runs on the fresh
    # record so guidance always matches the latest scores.
    from app.services.recommendations import generate_recommendations

    generate_recommendations(db, student_id, topic_id)
    return record
