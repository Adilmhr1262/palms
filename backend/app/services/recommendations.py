"""Rule-based recommendations linked to mastery results.

Every rule is explicit: the reason shown to the student and teacher is
stored on the recommendation row, and the priority order below is the
only ordering logic. There is no hidden scoring.

Priority (highest first): REPEATED_DIFFICULTY, LOW_PERFORMANCE,
DEVELOPING, MASTERY_ACHIEVED, HIGH_ACHIEVEMENT.

Only one active recommendation exists per student + topic + rule code
(enforced by a partial unique index); dismissed and completed rows stay
stored. The band rules (LOW_PERFORMANCE, DEVELOPING, MASTERY_ACHIEVED)
are mutually exclusive: when a new band applies, the previous band's
active recommendation is marked completed.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.assessment import Assessment, Attempt, AttemptStatus
from app.models.recommendation import Recommendation, RecommendationStatus

RULE_PRIORITY = [
    "REPEATED_DIFFICULTY",
    "LOW_PERFORMANCE",
    "DEVELOPING",
    "MASTERY_ACHIEVED",
    "HIGH_ACHIEVEMENT",
]

BAND_RULES = ("LOW_PERFORMANCE", "DEVELOPING", "MASTERY_ACHIEVED")

RULES = {
    "LOW_PERFORMANCE": {
        "title": "Additional practice recommended",
        "message": (
            "Your latest score is below 50%. Review the topic lessons "
            "and attempt the assessment again."
        ),
        "reason": "Your performance is below the required level for this topic.",
    },
    "DEVELOPING": {
        "title": "More practice recommended",
        "message": (
            "Work through the topic lessons and reassess before moving "
            "on to the next topic."
        ),
        "reason": "More practice is recommended before moving to the next topic.",
    },
    "MASTERY_ACHIEVED": {
        "title": "Topic mastered",
        "message": (
            "You reached the required mastery level. The next topic in "
            "the course is available to you."
        ),
        "reason": "You have achieved the required mastery level for this topic.",
    },
    "REPEATED_DIFFICULTY": {
        "title": "Teacher support requested",
        "message": (
            "This topic has been difficult in repeated attempts. Your "
            "teacher has been notified and will follow up."
        ),
        "reason": "This topic may require additional teacher support.",
    },
    "HIGH_ACHIEVEMENT": {
        "title": "Enrichment available",
        "message": (
            "Try the enrichment lessons for this topic to extend what "
            "you have learned."
        ),
        "reason": "Your strong performance allows you to explore additional activities.",
    },
}

LOW_SCORE_LINE = 50
HIGH_SCORE_LINE = 85


def rule_priority(rule_code: str) -> int:
    """Lower number means higher priority."""
    return RULE_PRIORITY.index(rule_code)


def _active(
    db: Session, student_id: int, topic_id: int, rule_code: str
) -> Recommendation | None:
    return db.scalar(
        select(Recommendation).where(
            Recommendation.student_id == student_id,
            Recommendation.topic_id == topic_id,
            Recommendation.rule_code == rule_code,
            Recommendation.status == RecommendationStatus.active,
        )
    )


def _ensure_active(
    db: Session, student_id: int, topic_id: int, rule_code: str
) -> Recommendation:
    existing = _active(db, student_id, topic_id, rule_code)
    if existing is not None:
        return existing
    spec = RULES[rule_code]
    rec = Recommendation(
        student_id=student_id,
        topic_id=topic_id,
        rule_code=rule_code,
        title=spec["title"],
        message=spec["message"],
        reason=spec["reason"],
        status=RecommendationStatus.active,
    )
    db.add(rec)
    db.flush()
    return rec


def _complete_active(
    db: Session, student_id: int, topic_id: int, rule_code: str
) -> None:
    existing = _active(db, student_id, topic_id, rule_code)
    if existing is not None:
        existing.status = RecommendationStatus.completed


def _repeated_difficulty(db: Session, student_id: int, topic_id: int) -> bool:
    """True when the last two graded attempts both scored below 50%."""
    from app.services.mastery import attempt_percent

    attempts = db.scalars(
        select(Attempt)
        .join(Assessment, Assessment.id == Attempt.assessment_id)
        .where(
            Attempt.student_id == student_id,
            Assessment.topic_id == topic_id,
            Attempt.status == AttemptStatus.graded,
        )
        .order_by(Attempt.submitted_at.desc(), Attempt.id.desc())
        .limit(2)
    ).all()
    if len(attempts) < 2:
        return False
    percents = [attempt_percent(a) for a in attempts]
    return all(p is not None and p < LOW_SCORE_LINE for p in percents)


def generate_recommendations(
    db: Session, student_id: int, topic_id: int
) -> list[Recommendation]:
    """Evaluate every rule for the student's current mastery state.

    Called after mastery recalculation. Idempotent: running it again
    with the same state creates nothing new.
    """
    from app.models.content import Topic
    from app.models.mastery import Mastery

    topic = db.get(Topic, topic_id)
    mastery = db.scalar(
        select(Mastery).where(
            Mastery.student_id == student_id,
            Mastery.topic_id == topic_id,
        )
    )
    if topic is None or mastery is None or mastery.latest_score is None:
        return []

    score = mastery.latest_score
    threshold = topic.mastery_threshold
    touched: list[Recommendation] = []

    if score < LOW_SCORE_LINE:
        band = "LOW_PERFORMANCE"
    elif score < threshold:
        band = "DEVELOPING"
    else:
        band = "MASTERY_ACHIEVED"

    for code in BAND_RULES:
        if code == band:
            touched.append(_ensure_active(db, student_id, topic_id, code))
        else:
            _complete_active(db, student_id, topic_id, code)

    if _repeated_difficulty(db, student_id, topic_id):
        touched.append(
            _ensure_active(db, student_id, topic_id, "REPEATED_DIFFICULTY")
        )
    else:
        _complete_active(db, student_id, topic_id, "REPEATED_DIFFICULTY")

    if score >= HIGH_SCORE_LINE:
        touched.append(
            _ensure_active(db, student_id, topic_id, "HIGH_ACHIEVEMENT")
        )
    else:
        _complete_active(db, student_id, topic_id, "HIGH_ACHIEVEMENT")

    db.flush()
    return touched
