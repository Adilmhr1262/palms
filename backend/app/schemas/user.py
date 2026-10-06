from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.user import UserRole


def _check_email(v: str) -> str:
    v = v.strip().lower()
    if "@" not in v or "." not in v.split("@")[-1]:
        raise ValueError("Enter a valid email address.")
    return v


class UserCreate(BaseModel):
    full_name: str
    email: str
    password: str
    role: UserRole = UserRole.student

    _email = field_validator("email")(_check_email)

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = None

    @field_validator("password")
    @classmethod
    def _password_length(cls, v: str | None) -> str | None:
        if v is not None and len(v) < 8:
            raise ValueError("Password must be at least 8 characters.")
        return v


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime


class LoginRequest(BaseModel):
    email: str
    password: str

    _email = field_validator("email")(_check_email)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead
