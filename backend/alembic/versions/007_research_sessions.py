"""Add the research_sessions table for education research evaluation.

Revision ID: 007
Revises: 006
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "research_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "student_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "class_id",
            sa.Integer(),
            sa.ForeignKey("classes.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("pre_test_score", sa.Float(), nullable=True),
        sa.Column("post_test_score", sa.Float(), nullable=True),
        sa.Column("learning_period", sa.Text(), nullable=True),
        sa.Column("score_change", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
    op.create_index("ix_research_student_id", "research_sessions", ["student_id"])
    op.create_index("ix_research_class_id", "research_sessions", ["class_id"])
    op.create_index("ix_research_course_id", "research_sessions", ["course_id"])


def downgrade() -> None:
    op.drop_index("ix_research_course_id", table_name="research_sessions")
    op.drop_index("ix_research_class_id", table_name="research_sessions")
    op.drop_index("ix_research_student_id", table_name="research_sessions")
    op.drop_table("research_sessions")
