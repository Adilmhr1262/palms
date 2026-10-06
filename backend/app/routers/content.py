import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import access
from app.core.config import settings
from app.core.deps import get_current_user, require_teacher
from app.db.session import get_db
from app.models.academic import Course
from app.models.content import Lesson, Resource, Topic
from app.schemas.content import (
    LessonCreate,
    LessonDetail,
    LessonRead,
    LessonUpdate,
    ResourceRead,
    TopicCreate,
    TopicRead,
    TopicUpdate,
)

router = APIRouter(tags=["content"])

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
}


def _get_course_or_404(db: Session, course_id: int) -> Course:
    course = db.get(Course, course_id)
    if course is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found."
        )
    return course


def _get_topic_or_404(db: Session, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found."
        )
    return topic


def _get_lesson_or_404(db: Session, lesson_id: int) -> Lesson:
    lesson = db.get(Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Lesson not found."
        )
    return lesson


def _require_view(db: Session, user, course: Course) -> None:
    if not access.can_view_course(db, user, course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course.",
        )


def _require_manage(db: Session, user, course_id: int) -> None:
    if not access.can_manage_course(db, user, course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can change its content.",
        )


def _topic_read(db: Session, topic: Topic) -> TopicRead:
    read = TopicRead.model_validate(topic)
    read.course_title = topic.course.title
    read.lessons = [
        LessonRead.model_validate(lesson) for lesson in topic.lessons
    ]
    return read


@router.get("/topics/{topic_id}", response_model=TopicRead)
def get_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    topic = _get_topic_or_404(db, topic_id)
    if not access.can_view_course(db, user, topic.course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course.",
        )
    return _topic_read(db, topic)


def _next_position(db: Session, model, parent_column, parent_id: int) -> int:
    current = (
        db.scalar(
            select(func.max(model.position)).where(parent_column == parent_id)
        )
        or 0
    )
    return current + 1


def _delete_resource_file(resource: Resource) -> None:
    try:
        path = Path(settings.upload_dir) / Path(resource.stored_path).name
        if path.is_file():
            path.unlink()
    except OSError:
        pass


@router.get("/courses/{course_id}/topics", response_model=list[TopicRead])
def list_topics(
    course_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    course = _get_course_or_404(db, course_id)
    _require_view(db, user, course)
    topics = db.scalars(
        select(Topic).where(Topic.course_id == course.id).order_by(Topic.position)
    ).all()
    return [_topic_read(db, t) for t in topics]


@router.post(
    "/courses/{course_id}/topics",
    response_model=TopicRead,
    status_code=status.HTTP_201_CREATED,
)
def create_topic(
    course_id: int,
    body: TopicCreate,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    course = _get_course_or_404(db, course_id)
    _require_manage(db, user, course.id)
    position = body.position
    if position is None:
        position = _next_position(db, Topic, Topic.course_id, course.id)
    topic = Topic(
        course_id=course.id,
        title=body.title,
        position=position,
        mastery_threshold=body.mastery_threshold,
        description=body.description,
    )
    db.add(topic)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another topic already uses this position.",
        )
    db.refresh(topic)
    return _topic_read(db, topic)


@router.patch("/topics/{topic_id}", response_model=TopicRead)
def update_topic(
    topic_id: int,
    body: TopicUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    topic = _get_topic_or_404(db, topic_id)
    _require_manage(db, user, topic.course_id)
    if body.title is not None:
        topic.title = body.title
    if body.description is not None:
        topic.description = body.description or None
    if body.mastery_threshold is not None:
        topic.mastery_threshold = body.mastery_threshold
    if body.position is not None:
        topic.position = body.position
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another topic already uses this position.",
        )
    db.refresh(topic)
    return _topic_read(db, topic)


@router.delete("/topics/{topic_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_topic(
    topic_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    topic = _get_topic_or_404(db, topic_id)
    _require_manage(db, user, topic.course_id)
    for lesson in topic.lessons:
        for resource in lesson.resources:
            _delete_resource_file(resource)
    db.delete(topic)
    db.commit()


@router.post(
    "/topics/{topic_id}/lessons",
    response_model=LessonRead,
    status_code=status.HTTP_201_CREATED,
)
def create_lesson(
    topic_id: int,
    body: LessonCreate,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    topic = _get_topic_or_404(db, topic_id)
    _require_manage(db, user, topic.course_id)
    position = body.position
    if position is None:
        position = _next_position(db, Lesson, Lesson.topic_id, topic.id)
    lesson = Lesson(
        topic_id=topic.id,
        title=body.title,
        objectives=body.objectives,
        body=body.body,
        position=position,
        is_enrichment=body.is_enrichment,
    )
    db.add(lesson)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another lesson already uses this position.",
        )
    db.refresh(lesson)
    return LessonRead.model_validate(lesson)


@router.get("/lessons/{lesson_id}", response_model=LessonDetail)
def get_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    lesson = _get_lesson_or_404(db, lesson_id)
    topic = lesson.topic
    course = topic.course
    _require_view(db, user, course)
    detail = LessonDetail.model_validate(lesson)
    detail.resources = [ResourceRead.model_validate(r) for r in lesson.resources]
    detail.topic_title = topic.title
    detail.course_id = course.id
    detail.course_title = course.title
    return detail


@router.patch("/lessons/{lesson_id}", response_model=LessonRead)
def update_lesson(
    lesson_id: int,
    body: LessonUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    lesson = _get_lesson_or_404(db, lesson_id)
    _require_manage(db, user, lesson.topic.course_id)
    if body.title is not None:
        lesson.title = body.title
    if body.objectives is not None:
        lesson.objectives = body.objectives or None
    if body.body is not None:
        lesson.body = body.body or None
    if body.is_enrichment is not None:
        lesson.is_enrichment = body.is_enrichment
    if body.position is not None:
        lesson.position = body.position
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Another lesson already uses this position.",
        )
    db.refresh(lesson)
    return LessonRead.model_validate(lesson)


@router.delete("/lessons/{lesson_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lesson(
    lesson_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    lesson = _get_lesson_or_404(db, lesson_id)
    _require_manage(db, user, lesson.topic.course_id)
    for resource in lesson.resources:
        _delete_resource_file(resource)
    db.delete(lesson)
    db.commit()


@router.post(
    "/lessons/{lesson_id}/resources",
    response_model=ResourceRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_resource(
    lesson_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    lesson = _get_lesson_or_404(db, lesson_id)
    _require_manage(db, user, lesson.topic.course_id)
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A file is required.",
        )
    mime_type = file.content_type or "application/octet-stream"
    extension = ALLOWED_MIME_TYPES.get(mime_type)
    if extension is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"File type {mime_type} is not allowed.",
        )
    contents = await file.read()
    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(contents) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is larger than the {settings.max_upload_mb} MB limit.",
        )
    # The stored extension comes from the validated MIME type, never from
    # the client-supplied filename, so a disguised file cannot change how
    # it is served.
    stored_name = f"{uuid.uuid4().hex}{extension}"
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    (upload_dir / stored_name).write_bytes(contents)
    resource = Resource(
        lesson_id=lesson.id,
        file_name=file.filename[:255],
        stored_path=stored_name,
        mime_type=mime_type,
        size_bytes=len(contents),
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return ResourceRead.model_validate(resource)


@router.get("/resources/{resource_id}/download")
def download_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
        )
    _require_view(db, user, resource.lesson.topic.course)
    path = Path(settings.upload_dir) / Path(resource.stored_path).name
    if not path.is_file():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="File not found."
        )
    return FileResponse(
        path, media_type=resource.mime_type, filename=resource.file_name
    )


@router.delete("/resources/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    user=Depends(require_teacher),
):
    resource = db.get(Resource, resource_id)
    if resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found."
        )
    _require_manage(db, user, resource.lesson.topic.course_id)
    _delete_resource_file(resource)
    db.delete(resource)
    db.commit()
