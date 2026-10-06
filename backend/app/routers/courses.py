from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import get_current_user, require_teacher
from app.db.session import get_db
from app.models.academic import Course, CourseTeacher, SchoolClass
from app.models.content import Topic
from app.models.user import User, UserRole
from app.schemas.academic import (
    CourseCreate,
    CourseDetail,
    CourseRead,
    CourseTeacherAdd,
    CourseTeacherInfo,
    CourseUpdate,
)

router = APIRouter(tags=["courses"])


def _read_with_counts(db: Session, course: Course) -> CourseRead:
    topic_count = (
        db.scalar(
            select(func.count()).select_from(Topic).where(Topic.course_id == course.id)
        )
        or 0
    )
    class_count = (
        db.scalar(
            select(func.count())
            .select_from(SchoolClass)
            .where(SchoolClass.course_id == course.id)
        )
        or 0
    )
    read = CourseRead.model_validate(course)
    read.topic_count = topic_count
    read.class_count = class_count
    return read


def _detail(db: Session, course: Course) -> CourseDetail:
    read = _read_with_counts(db, course)
    detail = CourseDetail.model_validate(read)
    teachers = db.scalars(
        select(User)
        .join(CourseTeacher, CourseTeacher.teacher_id == User.id)
        .where(CourseTeacher.course_id == course.id)
        .order_by(User.full_name)
    ).all()
    detail.teachers = [CourseTeacherInfo.model_validate(t) for t in teachers]
    return detail


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    return course


@router.get("/courses", response_model=list[CourseRead])
def list_courses(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if user.role == UserRole.admin:
        courses = db.scalars(select(Course).order_by(Course.title)).all()
    elif user.role == UserRole.teacher:
        courses = db.scalars(
            select(Course)
            .join(CourseTeacher, CourseTeacher.course_id == Course.id)
            .where(CourseTeacher.teacher_id == user.id)
            .order_by(Course.title)
        ).all()
    else:
        ids = access.student_course_ids(db, user.id)
        if not ids:
            return []
        courses = db.scalars(
            select(Course).where(Course.id.in_(ids)).order_by(Course.title)
        ).all()
    return [_read_with_counts(db, c) for c in courses]


@router.post("/courses", response_model=CourseDetail, status_code=status.HTTP_201_CREATED)
def create_course(
    body: CourseCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = Course(title=body.title, description=body.description)
    db.add(course)
    db.flush()
    if user.role == UserRole.teacher:
        db.add(CourseTeacher(course_id=course.id, teacher_id=user.id))
    db.commit()
    db.refresh(course)
    return _detail(db, course)


@router.get("/courses/{course_id}", response_model=CourseDetail)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    course = _get_course_or_404(db, course_id)
    if not access.can_view_course(db, user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course.",
        )
    return _detail(db, course)


@router.patch("/courses/{course_id}", response_model=CourseDetail)
def update_course(
    course_id: int,
    body: CourseUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _get_course_or_404(db, course_id)
    if not access.can_manage_course(db, user, course.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can change it.",
        )
    if body.title is not None:
        course.title = body.title
    if body.description is not None:
        course.description = body.description or None
    db.commit()
    db.refresh(course)
    return _detail(db, course)


@router.delete("/courses/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _get_course_or_404(db, course_id)
    if not access.can_manage_course(db, user, course.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can delete it.",
        )
    linked = (
        db.scalar(
            select(func.count())
            .select_from(SchoolClass)
            .where(SchoolClass.course_id == course.id)
        )
        or 0
    )
    if linked:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This course is used by one or more classes. Unlink the classes first.",
        )
    db.delete(course)
    db.commit()


@router.post(
    "/courses/{course_id}/teachers",
    response_model=CourseTeacherInfo,
    status_code=status.HTTP_201_CREATED,
)
def add_course_teacher(
    course_id: int,
    body: CourseTeacherAdd,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _get_course_or_404(db, course_id)
    if not access.can_manage_course(db, user, course.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can invite co-teachers.",
        )
    teacher = db.get(User, body.teacher_id)
    if teacher is None or not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found."
        )
    if teacher.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only teacher accounts can teach a course.",
        )
    existing = db.scalar(
        select(CourseTeacher).where(
            CourseTeacher.course_id == course.id,
            CourseTeacher.teacher_id == teacher.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This teacher is already on the course.",
        )
    db.add(CourseTeacher(course_id=course.id, teacher_id=teacher.id))
    db.commit()
    return CourseTeacherInfo.model_validate(teacher)


@router.delete(
    "/courses/{course_id}/teachers/{teacher_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_course_teacher(
    course_id: int,
    teacher_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    course = _get_course_or_404(db, course_id)
    if not access.can_manage_course(db, user, course.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can remove co-teachers.",
        )
    link = db.scalar(
        select(CourseTeacher).where(
            CourseTeacher.course_id == course.id,
            CourseTeacher.teacher_id == teacher_id,
        )
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Co-teacher not found."
        )
    remaining = (
        db.scalar(
            select(func.count())
            .select_from(CourseTeacher)
            .where(CourseTeacher.course_id == course.id)
        )
        or 0
    )
    if remaining <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A course must keep at least one teacher.",
        )
    db.delete(link)
    db.commit()
