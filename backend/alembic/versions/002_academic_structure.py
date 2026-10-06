"""Academic structure: courses, course_teachers, classes, enrollments.

Revision ID: 002
Revises: 001
Create Date: 2026-10-01

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "course_teachers",
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "teacher_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_table(
        "classes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("academic_year", sa.String(20), nullable=False),
        sa.Column(
            "course_id",
            sa.Integer(),
            sa.ForeignKey("courses.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column(
            "teacher_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("name", "academic_year", name="uq_classes_name_year"),
    )
    op.create_index("ix_classes_course_id", "classes", ["course_id"])
    op.create_index("ix_classes_teacher_id", "classes", ["teacher_id"])
    op.create_table(
        "enrollments",
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
            "enrolled_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "student_id", "class_id", name="uq_enrollments_student_class"
        ),
    )
    op.create_index("ix_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("ix_enrollments_class_id", "enrollments", ["class_id"])


def downgrade() -> None:
    op.drop_index("ix_enrollments_class_id", table_name="enrollments")
    op.drop_index("ix_enrollments_student_id", table_name="enrollments")
    op.drop_table("enrollments")
    op.drop_index("ix_classes_teacher_id", table_name="classes")
    op.drop_index("ix_classes_course_id", table_name="classes")
    op.drop_table("classes")
    op.drop_table("course_teachers")
    op.drop_table("courses")
