"""Mastery records: per-student, per-topic scores and status.

Revision ID: 005
Revises: 004
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mastery",
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
        sa.Column(
            "attempts_count", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("latest_score", sa.Float(), nullable=True),
        sa.Column("best_score", sa.Float(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "needs_support",
                "developing",
                "proficient",
                "mastered",
                name="mastery_status",
            ),
            nullable=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_id", "topic_id", name="uq_mastery_student_topic"
        ),
    )
    op.create_index("ix_mastery_student_id", "mastery", ["student_id"])
    op.create_index("ix_mastery_topic_id", "mastery", ["topic_id"])


def downgrade() -> None:
    op.drop_index("ix_mastery_topic_id", table_name="mastery")
    op.drop_index("ix_mastery_student_id", table_name="mastery")
    op.drop_table("mastery")
    # On PostgreSQL the ENUM type must be dropped explicitly; on SQLite
    # this is a no-op.
    sa.Enum(name="mastery_status").drop(op.get_bind(), checkfirst=True)
