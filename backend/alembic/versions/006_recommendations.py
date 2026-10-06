"""Recommendations and lesson progress.

Revision ID: 006
Revises: 005
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "recommendations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_code", sa.String(40), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "active",
                "dismissed",
                "completed",
                name="recommendation_status",
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("teacher_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_recommendations_student_id", "recommendations", ["student_id"]
    )
    op.create_index(
        "ix_recommendations_topic_id", "recommendations", ["topic_id"]
    )
    op.create_index(
        "ix_recommendations_rule_code", "recommendations", ["rule_code"]
    )
    op.create_index("ix_recommendations_status", "recommendations", ["status"])
    # Only one active recommendation per student + topic + rule code.
    # Dismissed and completed rows remain stored without blocking a
    # future active recommendation for the same rule.
    op.create_index(
        "uq_recommendations_active",
        "recommendations",
        ["student_id", "topic_id", "rule_code"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    op.create_table(
        "lesson_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_id",
            "lesson_id",
            name="uq_lesson_progress_student_lesson",
        ),
    )
    op.create_index(
        "ix_lesson_progress_student_id", "lesson_progress", ["student_id"]
    )
    op.create_index(
        "ix_lesson_progress_lesson_id", "lesson_progress", ["lesson_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_lesson_progress_lesson_id", table_name="lesson_progress")
    op.drop_index(
        "ix_lesson_progress_student_id", table_name="lesson_progress"
    )
    op.drop_table("lesson_progress")
    op.drop_index("uq_recommendations_active", table_name="recommendations")
    op.drop_index("ix_recommendations_status", table_name="recommendations")
    op.drop_index("ix_recommendations_rule_code", table_name="recommendations")
    op.drop_index("ix_recommendations_topic_id", table_name="recommendations")
    op.drop_index("ix_recommendations_student_id", table_name="recommendations")
    op.drop_table("recommendations")
    # On PostgreSQL the ENUM type must be dropped explicitly; on SQLite
    # this is a no-op.
    sa.Enum(name="recommendation_status").drop(op.get_bind(), checkfirst=True)
