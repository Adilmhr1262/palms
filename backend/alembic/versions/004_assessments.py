"""Assessments: question bank, assessments, attempts, answers.

Revision ID: 004
Revises: 003
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "qtype",
            sa.Enum("mcq", "true_false", "short_answer", name="question_type"),
            nullable=False,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        sa.Column("correct_option", sa.Integer(), nullable=True),
        sa.Column("model_answer", sa.Text(), nullable=True),
        sa.Column("points", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_questions_topic_id", "questions", ["topic_id"])
    op.create_table(
        "assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column(
            "is_published", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_assessments_topic_id", "assessments", ["topic_id"])
    op.create_table(
        "assessment_questions",
        sa.Column(
            "assessment_id",
            sa.Integer(),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
    )
    op.create_table(
        "attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            sa.ForeignKey("assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Enum("in_progress", "submitted", "graded", name="attempt_status"),
            nullable=False,
            server_default="in_progress",
        ),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("max_score", sa.Integer(), nullable=True),
    )
    op.create_index("ix_attempts_assessment_id", "attempts", ["assessment_id"])
    op.create_index("ix_attempts_student_id", "attempts", ["student_id"])
    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "attempt_id",
            sa.Integer(),
            sa.ForeignKey("attempts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("student_text", sa.Text(), nullable=True),
        sa.Column("selected_option", sa.Integer(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("points_earned", sa.Integer(), nullable=True),
        sa.Column("teacher_comment", sa.Text(), nullable=True),
        sa.Column(
            "graded_by",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("graded_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint(
            "attempt_id", "question_id", name="uq_answers_attempt_question"
        ),
    )
    op.create_index("ix_answers_attempt_id", "answers", ["attempt_id"])


def downgrade() -> None:
    op.drop_index("ix_answers_attempt_id", table_name="answers")
    op.drop_table("answers")
    op.drop_index("ix_attempts_student_id", table_name="attempts")
    op.drop_index("ix_attempts_assessment_id", table_name="attempts")
    op.drop_table("attempts")
    op.drop_table("assessment_questions")
    op.drop_index("ix_assessments_topic_id", table_name="assessments")
    op.drop_table("assessments")
    op.drop_index("ix_questions_topic_id", table_name="questions")
    op.drop_table("questions")
    # On PostgreSQL the ENUM types must be dropped explicitly; on SQLite
    # this is a no-op.
    bind = op.get_bind()
    sa.Enum(name="attempt_status").drop(bind, checkfirst=True)
    sa.Enum(name="question_type").drop(bind, checkfirst=True)
