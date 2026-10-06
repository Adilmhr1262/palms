"""Row-level access checks for the academic structure.

Role dependencies (require_teacher, require_admin) run first; these helpers
decide whether the authenticated user may see or change a specific course,
class, or piece of content. The backend is the final gate.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.academic import Course, CourseTeacher, Enrollment, SchoolClass
from app.models.user import User, UserRole


def is_admin(user: User) -> bool:
    return user.role == UserRole.admin


def is_course_teacher(db: Session, user: User, course_id: int) -> bool:
    if is_admin(user):
        return True
    return (
        db.scalar(
            select(CourseTeacher).where(
                CourseTeacher.course_id == course_id,
                CourseTeacher.teacher_id == user.id,
            )
        )
        is not None
    )


def student_course_ids(db: Session, student_id: int) -> set[int]:
    rows = db.scalars(
        select(SchoolClass.course_id)
        .join(Enrollment, Enrollment.class_id == SchoolClass.id)
        .where(
            Enrollment.student_id == student_id,
            SchoolClass.course_id.is_not(None),
        )
    ).all()
    return set(rows)


def is_enrolled(db: Session, student_id: int, class_id: int) -> bool:
    return (
        db.scalar(
            select(Enrollment).where(
                Enrollment.student_id == student_id,
                Enrollment.class_id == class_id,
            )
        )
        is not None
    )


def can_view_course(db: Session, user: User, course: Course) -> bool:
    if is_admin(user) or is_course_teacher(db, user, course.id):
        return True
    if user.role == UserRole.student:
        return course.id in student_course_ids(db, user.id)
    return False


def can_manage_course(db: Session, user: User, course_id: int) -> bool:
    return is_course_teacher(db, user, course_id)


def can_view_class(db: Session, user: User, class_: SchoolClass) -> bool:
    if is_admin(user) or class_.teacher_id == user.id:
        return True
    if class_.course_id is not None and is_course_teacher(db, user, class_.course_id):
        return True
    if user.role == UserRole.student:
        return is_enrolled(db, user.id, class_.id)
    return False


def can_manage_class(db: Session, user: User, class_: SchoolClass) -> bool:
    return is_admin(user) or class_.teacher_id == user.id
