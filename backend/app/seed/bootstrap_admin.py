"""Create the first administrator account.

Reads ADMIN_EMAIL and ADMIN_PASSWORD from the environment. Refuses to run
when any user already exists, so it can only bootstrap an empty database.

Usage:
    ADMIN_EMAIL=admin@palms.edu ADMIN_PASSWORD=secret123 \\
        python -m app.seed.bootstrap_admin
"""
import os
import sys

from sqlalchemy import select

from app.core import security
from app.db.session import get_session_factory
from app.models.user import User, UserRole


def main() -> int:
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        print("Set ADMIN_EMAIL and ADMIN_PASSWORD first.", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("ADMIN_PASSWORD must be at least 8 characters.", file=sys.stderr)
        return 1
    db = get_session_factory()()
    try:
        if db.scalar(select(User.id).limit(1)) is not None:
            print("Users already exist; nothing to do.")
            return 0
        admin = User(
            full_name="Administrator",
            email=email,
            password_hash=security.hash_password(password),
            role=UserRole.admin,
        )
        db.add(admin)
        db.commit()
        print(f"Administrator account created for {email}.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
