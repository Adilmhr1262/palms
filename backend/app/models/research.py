"""Research evaluation records for education research analysis.

A research session captures one student's pre/post test measurement within a
class: the two scores, the learning period between them, and free-text notes.
score_change is always computed server-side as post_test_score - pre_test_score
and never claimed as improvement; it is a measured value only.
"""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.db.base import Base


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pre_test_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    post_test_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    learning_period: Mapped[str | None] = mapped_column(Text, nullable=True)
    score_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(),
        nullable=False,
    )


def compute_score_change(
    pre: float | None, post: float | None
) -> float | None:
    """Measured change between the two scores, or None when incomplete."""
    if pre is None or post is None:
        return None
    return round(post - pre, 2)


def get_research_sessions(db: Session, class_id: int):
    return db.scalars(
        select(ResearchSession)
        .where(ResearchSession.class_id == class_id)
        .order_by(ResearchSession.created_at.desc())
    ).all()
