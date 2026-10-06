from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from pydantic import BaseModel, ConfigDict

from app.core import security
from app.core.deps import require_admin, require_teacher
from app.db.session import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter(tags=["users"])


class DirectoryEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole


@router.get("/users/directory", response_model=list[DirectoryEntry])
def user_directory(
    role: UserRole = Query(...),
    db: Session = Depends(get_db),
    _user: User = Depends(require_teacher),
):
    """Minimal active-user listing so teachers can pick students or
    co-teachers. Full user management stays admin-only."""
    if role == UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The directory lists teachers and students only.",
        )
    users = db.scalars(
        select(User)
        .where(User.role == role, User.is_active.is_(True))
        .order_by(User.full_name)
    ).all()
    return [DirectoryEntry.model_validate(u) for u in users]


@router.get("/users", response_model=list[UserRead])
def list_users(
    db: Session = Depends(get_db), _admin: User = Depends(require_admin)
):
    return db.scalars(select(User).order_by(User.created_at)).all()


@router.post("/users", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    existing = db.scalar(select(User).where(User.email == body.email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    user = User(
        full_name=body.full_name.strip(),
        email=body.email,
        password_hash=security.hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    return user


@router.patch("/users/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found."
        )
    if user.id == admin.id:
        if body.role is not None and body.role != admin.role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot change your own role.",
            )
        if body.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account.",
            )
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.password_hash = security.hash_password(body.password)
    db.commit()
    db.refresh(user)
    return user
