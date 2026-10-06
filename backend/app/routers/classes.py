from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import get_current_user, require_teacher
from app.db.session import get_db
from app.models.academic import Course, Enrollment, SchoolClass
from app.models.user import User, UserRole
from app.schemas.academic import (
    ClassCreate,
    ClassDetail,
    ClassRead,
    ClassUpdate,
    EnrollmentAdd,
    EnrollmentInfo,
)

router = APIRouter(tags=["classes"])


def _read_with_counts(db: Session, class_: SchoolClass) -> ClassRead:
    student_count = (
        db.scalar(
            select(func.count())
            .select_from(Enrollment)
            .where(Enrollment.class_id == class_.id)
        )
        or 0
    )
    read = ClassRead.model_validate(class_)
    read.student_count = student_count
    if class_.course is not None:
        read.course_title = class_.course.title
    teacher = db.get(User, class_.teacher_id)
    if teacher is not None:
        read.teacher_name = teacher.full_name
    return read


def _detail(db: Session, class_: SchoolClass, include_enrollments: bool) -> ClassDetail:
    read = _read_with_counts(db, class_)
    detail = ClassDetail.model_validate(read)
    if include_enrollments:
        rows = db.scalars(
            select(Enrollment).where(Enrollment.class_id == class_.id).order_by(Enrollment.enrolled_at)
        ).all()
        items = []
        for row in rows:
            student = db.get(User, row.student_id)
            item = EnrollmentInfo.model_validate(row)
            if student is not None:
                item.student_name = student.full_name
                item.student_email = student.email
            items.append(item)
        detail.enrollments = items
    return detail


def _get_class_or_404(db: Session, class_id: int) -> SchoolClass:
    class_ = db.get(SchoolClass, class_id)
    if class_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found."
        )
    return class_


@router.get("/classes", response_model=list[ClassRead])
def list_classes(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    if user.role == UserRole.admin:
        classes = db.scalars(select(SchoolClass).order_by(SchoolClass.name)).all()
    elif user.role == UserRole.teacher:
        classes = db.scalars(
            select(SchoolClass)
            .where(SchoolClass.teacher_id == user.id)
            .order_by(SchoolClass.name)
        ).all()
    else:
        classes = db.scalars(
            select(SchoolClass)
            .join(Enrollment, Enrollment.class_id == SchoolClass.id)
            .where(Enrollment.student_id == user.id)
            .order_by(SchoolClass.name)
        ).all()
    return [_read_with_counts(db, c) for c in classes]


@router.post("/classes", response_model=ClassDetail, status_code=status.HTTP_201_CREATED)
def create_class(
    body: ClassCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    teacher_id = body.teacher_id
    if teacher_id is None:
        if user.role == UserRole.teacher:
            teacher_id = user.id
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="teacher_id is required when an administrator creates a class.",
            )
    teacher = db.get(User, teacher_id)
    if teacher is None or not teacher.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class teacher not found."
        )
    if teacher.role not in (UserRole.teacher, UserRole.admin):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The class teacher must be a teacher account.",
        )
    if user.role == UserRole.teacher and teacher_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers can only create classes for themselves.",
        )
    course = None
    if body.course_id is not None:
        course = db.get(Course, body.course_id)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
            )
        if not access.can_view_course(db, user, course):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this course.",
            )
    class_ = SchoolClass(
        name=body.name,
        academic_year=body.academic_year,
        course_id=course.id if course else None,
        teacher_id=teacher_id,
    )
    db.add(class_)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A class with this name already exists for the academic year.",
        )
    db.refresh(class_)
    return _detail(db, class_, include_enrollments=True)


@router.get("/classes/{class_id}", response_model=ClassDetail)
def get_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    class_ = _get_class_or_404(db, class_id)
    if not access.can_view_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this class.",
        )
    manager = access.can_manage_class(db, user, class_)
    return _detail(db, class_, include_enrollments=manager)


@router.patch("/classes/{class_id}", response_model=ClassDetail)
def update_class(
    class_id: int,
    body: ClassUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    if not access.can_manage_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the class teacher can change this class.",
        )
    if body.name is not None:
        class_.name = body.name.strip()
    if body.academic_year is not None:
        class_.academic_year = body.academic_year.strip()
    if body.course_id is not None:
        course = db.get(Course, body.course_id)
        if course is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
            )
        class_.course_id = course.id
    if body.teacher_id is not None:
        teacher = db.get(User, body.teacher_id)
        if teacher is None or not teacher.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Class teacher not found."
            )
        if teacher.role not in (UserRole.teacher, UserRole.admin):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="The class teacher must be a teacher account.",
            )
        class_.teacher_id = teacher.id
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A class with this name already exists for the academic year.",
        )
    db.refresh(class_)
    return _detail(db, class_, include_enrollments=True)


@router.delete("/classes/{class_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_class(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    if not access.can_manage_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the class teacher can delete this class.",
        )
    db.delete(class_)
    db.commit()


@router.post(
    "/classes/{class_id}/enrollments",
    response_model=EnrollmentInfo,
    status_code=status.HTTP_201_CREATED,
)
def add_enrollment(
    class_id: int,
    body: EnrollmentAdd,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    if not access.can_manage_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the class teacher can enroll students.",
        )
    student = db.get(User, body.student_id)
    if student is None or not student.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Student not found."
        )
    if student.role != UserRole.student:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Only student accounts can be enrolled.",
        )
    if access.is_enrolled(db, student.id, class_.id):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This student is already enrolled in the class.",
        )
    enrollment = Enrollment(student_id=student.id, class_id=class_.id)
    db.add(enrollment)
    db.commit()
    db.refresh(enrollment)
    info = EnrollmentInfo.model_validate(enrollment)
    info.student_name = student.full_name
    info.student_email = student.email
    return info


@router.delete(
    "/classes/{class_id}/enrollments/{enrollment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_enrollment(
    class_id: int,
    enrollment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    if not access.can_manage_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the class teacher can remove students.",
        )
    enrollment = db.get(Enrollment, enrollment_id)
    if enrollment is None or enrollment.class_id != class_.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Enrollment not found."
        )
    db.delete(enrollment)
    db.commit()
