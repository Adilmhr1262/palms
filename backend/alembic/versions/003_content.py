"""Content: topics, lessons, resources.

Revision ID: 003
Revises: 002
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "mastery_threshold",
            sa.Integer(),
            nullable=False,
            server_default="70",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.UniqueConstraint(
            "course_id", "position", name="uq_topics_course_position"
        ),
    )
    op.create_index("ix_topics_course_id", "topics", ["course_id"])
    op.create_table(
        "lessons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "topic_id",
            sa.Integer(),
            sa.ForeignKey("topics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("objectives", sa.Text(), nullable=True),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "is_enrichment", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "topic_id", "position", name="uq_lessons_topic_position"
        ),
    )
    op.create_index("ix_lessons_topic_id", "lessons", ["topic_id"])
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "lesson_id",
            sa.Integer(),
            sa.ForeignKey("lessons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("stored_path", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_resources_lesson_id", "resources", ["lesson_id"])


def downgrade() -> None:
    op.drop_index("ix_resources_lesson_id", table_name="resources")
    op.drop_table("resources")
    op.drop_index("ix_lessons_topic_id", table_name="lessons")
    op.drop_table("lessons")
    op.drop_index("ix_topics_course_id", table_name="topics")
    op.drop_table("topics")
