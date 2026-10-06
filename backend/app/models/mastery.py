import enum
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class MasteryStatus(str, enum.Enum):
    needs_support = "needs_support"
    developing = "developing"
    proficient = "proficient"
    mastered = "mastered"


class Mastery(Base):
    __tablename__ = "mastery"
    __table_args__ = (
        UniqueConstraint(
            "student_id", "topic_id", name="uq_mastery_student_topic"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    attempts_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    latest_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    best_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[MasteryStatus | None] = mapped_column(
        Enum(MasteryStatus, name="mastery_status"), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    student: Mapped["User"] = relationship()
    topic: Mapped["Topic"] = relationship()
