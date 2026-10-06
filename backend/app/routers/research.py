"""Research evaluation records: pre/post test measurement for education research.

Teachers (and admins) record and read research sessions for the classes they
manage. score_change is always computed server-side as
post_test_score - pre_test_score; the API reports the measured value only and
never claims improvement.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import require_teacher
from app.db.session import get_db
from app.models.academic import SchoolClass
from app.models.research import ResearchSession, compute_score_change
from app.models.user import User
from app.schemas.reporting import (
    ResearchSessionCreate,
    ResearchSessionRead,
    ResearchSessionUpdate,
)

router = APIRouter(tags=["research"])


def _get_class_or_404(db: Session, class_id: int) -> SchoolClass:
    class_ = db.get(SchoolClass, class_id)
    if class_ is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Class not found."
        )
    return class_


def _require_manage_class(db: Session, user: User, class_: SchoolClass) -> None:
    if not access.can_manage_class(db, user, class_):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the class teacher can manage research records.",
        )


def _to_read(db: Session, session: ResearchSession) -> ResearchSessionRead:
    student = db.get(User, session.student_id)
    class_ = db.get(SchoolClass, session.class_id)
    return ResearchSessionRead(
        id=session.id,
        student_id=session.student_id,
        student_name=student.full_name if student else "",
        class_id=session.class_id,
        class_name=class_.name if class_ else "",
        course_id=session.course_id,
        course_title=class_.course.title if class_ and class_.course else "",
        pre_test_score=session.pre_test_score,
        post_test_score=session.post_test_score,
        learning_period=session.learning_period,
        score_change=session.score_change,
        notes=session.notes,
        created_at=session.created_at,
    )


@router.post(
    "/classes/{class_id}/research-sessions",
    response_model=ResearchSessionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_research_session(
    class_id: int,
    data: ResearchSessionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    if class_.course_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This class is not linked to a course.",
        )
    if not access.is_enrolled(db, data.student_id, class_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The student is not enrolled in this class.",
        )
    session = ResearchSession(
        student_id=data.student_id,
        class_id=class_id,
        course_id=class_.course_id,
        pre_test_score=data.pre_test_score,
        post_test_score=data.post_test_score,
        learning_period=data.learning_period.strip() if data.learning_period else None,
        notes=data.notes.strip() if data.notes else None,
        score_change=compute_score_change(data.pre_test_score, data.post_test_score),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return _to_read(db, session)


@router.get(
    "/classes/{class_id}/research-sessions",
    response_model=list[ResearchSessionRead],
)
def list_research_sessions(
    class_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    class_ = _get_class_or_404(db, class_id)
    _require_manage_class(db, user, class_)
    sessions = db.scalars(
        select(ResearchSession)
        .where(ResearchSession.class_id == class_id)
        .order_by(ResearchSession.created_at.desc())
    ).all()
    return [_to_read(db, s) for s in sessions]


@router.patch(
    "/research-sessions/{session_id}",
    response_model=ResearchSessionRead,
)
def update_research_session(
    session_id: int,
    data: ResearchSessionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    session = db.get(ResearchSession, session_id)
    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Research record not found.",
        )
    class_ = _get_class_or_404(db, session.class_id)
    _require_manage_class(db, user, class_)
    provided = data.model_fields_set
    if "pre_test_score" in provided:
        session.pre_test_score = data.pre_test_score
    if "post_test_score" in provided:
        session.post_test_score = data.post_test_score
    if "learning_period" in provided:
        session.learning_period = (
            data.learning_period.strip() or None if data.learning_period else None
        )
    if "notes" in provided:
        session.notes = data.notes.strip() or None if data.notes else None
    session.score_change = compute_score_change(
        session.pre_test_score, session.post_test_score
    )
    db.commit()
    db.refresh(session)
    return _to_read(db, session)
