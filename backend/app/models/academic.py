from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    teachers: Mapped[list["CourseTeacher"]] = relationship(
        back_populates="course", cascade="all, delete-orphan"
    )
    topics: Mapped[list["Topic"]] = relationship(
        back_populates="course",
        cascade="all, delete-orphan",
        order_by="Topic.position",
    )
    classes: Mapped[list["SchoolClass"]] = relationship(back_populates="course")


class CourseTeacher(Base):
    __tablename__ = "course_teachers"

    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )

    course: Mapped["Course"] = relationship(back_populates="teachers")


class SchoolClass(Base):
    __tablename__ = "classes"
    __table_args__ = (UniqueConstraint("name", "academic_year", name="uq_classes_name_year"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(20), nullable=False)
    course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="RESTRICT"), nullable=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    course: Mapped["Course | None"] = relationship(back_populates="classes")
    enrollments: Mapped[list["Enrollment"]] = relationship(
        back_populates="class_", cascade="all, delete-orphan"
    )


class Enrollment(Base):
    __tablename__ = "enrollments"
    __table_args__ = (
        UniqueConstraint("student_id", "class_id", name="uq_enrollments_student_class"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    class_id: Mapped[int] = mapped_column(
        ForeignKey("classes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    enrolled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    class_: Mapped["SchoolClass"] = relationship(back_populates="enrollments")
