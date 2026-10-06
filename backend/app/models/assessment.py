import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class QuestionType(str, enum.Enum):
    mcq = "mcq"
    true_false = "true_false"
    short_answer = "short_answer"


class AttemptStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    graded = "graded"


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    qtype: Mapped[QuestionType] = mapped_column(
        Enum(QuestionType, name="question_type"), nullable=False
    )
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[list | None] = mapped_column(JSON, nullable=True)
    correct_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    points: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    topic: Mapped["Topic"] = relationship()


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    topic_id: Mapped[int] = mapped_column(
        ForeignKey("topics.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    topic: Mapped["Topic"] = relationship()
    questions: Mapped[list["AssessmentQuestion"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.position",
    )


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    assessment: Mapped["Assessment"] = relationship(back_populates="questions")
    question: Mapped["Question"] = relationship()


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    assessment_id: Mapped[int] = mapped_column(
        ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[AttemptStatus] = mapped_column(
        Enum(AttemptStatus, name="attempt_status"),
        nullable=False,
        default=AttemptStatus.in_progress,
    )
    total_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    assessment: Mapped["Assessment"] = relationship()
    answers: Mapped[list["Answer"]] = relationship(
        back_populates="attempt", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_answers_attempt_question"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(
        ForeignKey("attempts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(
        ForeignKey("questions.id", ondelete="CASCADE"), nullable=False
    )
    student_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    selected_option: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    points_earned: Mapped[int | None] = mapped_column(Integer, nullable=True)
    teacher_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    graded_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    attempt: Mapped["Attempt"] = relationship(back_populates="answers")
    question: Mapped["Question"] = relationship()
