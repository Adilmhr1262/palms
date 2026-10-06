from pathlib import Path

from fastapi import FastAPI

from app.core.config import settings
from app.routers import assessments, auth, bank, classes, content, courses, grading, recommendations, reports, research, users

app = FastAPI(title="PALMS", version="0.1.0")

app.include_router(auth.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")
app.include_router(courses.router, prefix="/api/v1")
app.include_router(classes.router, prefix="/api/v1")
app.include_router(content.router, prefix="/api/v1")
app.include_router(bank.router, prefix="/api/v1")
app.include_router(assessments.router, prefix="/api/v1")
app.include_router(grading.router, prefix="/api/v1")
app.include_router(recommendations.router, prefix="/api/v1")
app.include_router(recommendations.lessons_router, prefix="/api/v1")
app.include_router(recommendations.path_router, prefix="/api/v1")
app.include_router(reports.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")

# Uploaded files are never served statically: every download goes through the
# authenticated /resources/{id}/download endpoint, which checks course access.
upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)


def assert_production_secrets() -> None:
    """Fail fast rather than signing tokens with a placeholder secret."""
    if settings.env == "production" and settings.jwt_secret in (
        "change-me-to-a-long-random-string",
        "change-me-in-production",
    ):
        raise RuntimeError("Refusing to start: set a real JWT_SECRET in production.")


assert_production_secrets()


@app.get("/")
def root():
    return {"service": "palms-backend", "version": "0.1.0"}


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "database_configured": bool(settings.database_url)}
