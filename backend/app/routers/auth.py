from time import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import security
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import LoginRequest, TokenResponse, UserRead

router = APIRouter(tags=["auth"])

# Simple in-memory brute-force protection for the login endpoint: after
# MAX_FAILURES failed attempts for one client+email pair inside WINDOW_SECONDS,
# further attempts get 429 until the window passes. A successful login clears
# the counter. This is per-process state, which fits a single-instance
# deployment; a multi-instance setup would move it to shared storage.
_LOGIN_FAILURES: dict[tuple[str, str], list[float]] = {}
MAX_FAILURES = 10
WINDOW_SECONDS = 600


def _client_key(request: Request, email: str) -> tuple[str, str]:
    forwarded = request.headers.get("x-forwarded-for")
    ip = forwarded.split(",")[0].strip() if forwarded else request.client.host
    return (ip, email.strip().lower())


def _check_rate_limit(key: tuple[str, str]) -> None:
    now = time()
    attempts = [t for t in _LOGIN_FAILURES.get(key, []) if now - t < WINDOW_SECONDS]
    _LOGIN_FAILURES[key] = attempts
    if len(attempts) >= MAX_FAILURES:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed sign-in attempts. Try again later.",
        )


def _record_failure(key: tuple[str, str]) -> None:
    _LOGIN_FAILURES.setdefault(key, []).append(time())


@router.post("/auth/login", response_model=TokenResponse)
def login(body: LoginRequest, request: Request, db: Session = Depends(get_db)):
    key = _client_key(request, body.email)
    _check_rate_limit(key)
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None or not security.verify_password(body.password, user.password_hash):
        _record_failure(key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is deactivated."
        )
    _LOGIN_FAILURES.pop(key, None)
    token = security.create_access_token(user.id, user.role.value)
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post("/auth/logout")
def logout():
    # Sessions live in the httpOnly cookie, which the frontend clears.
    return {"status": "logged out"}


@router.get("/auth/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return UserRead.model_validate(user)
