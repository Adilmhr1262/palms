from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


def _not_blank(value: str | None, field: str) -> str | None:
    if value is not None:
        value = value.strip()
        if not value:
            raise ValueError(f"{field} is required.")
    return value


class TopicCreate(BaseModel):
    title: str
    position: int | None = None
    mastery_threshold: int = 70
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        return _not_blank(v, "Title")  # type: ignore[return-value]

    @field_validator("mastery_threshold")
    @classmethod
    def _threshold_range(cls, v: int) -> int:
        if not 1 <= v <= 100:
            raise ValueError("Mastery threshold must be between 1 and 100.")
        return v

    @field_validator("position")
    @classmethod
    def _position_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Position must be 1 or greater.")
        return v


class TopicUpdate(BaseModel):
    title: str | None = None
    position: int | None = None
    mastery_threshold: int | None = None
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str | None) -> str | None:
        return _not_blank(v, "Title")

    @field_validator("mastery_threshold")
    @classmethod
    def _threshold_range(cls, v: int | None) -> int | None:
        if v is not None and not 1 <= v <= 100:
            raise ValueError("Mastery threshold must be between 1 and 100.")
        return v

    @field_validator("position")
    @classmethod
    def _position_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Position must be 1 or greater.")
        return v


class LessonCreate(BaseModel):
    title: str
    objectives: str | None = None
    body: str | None = None
    position: int | None = None
    is_enrichment: bool = False

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        return _not_blank(v, "Title")  # type: ignore[return-value]

    @field_validator("position")
    @classmethod
    def _position_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Position must be 1 or greater.")
        return v


class LessonUpdate(BaseModel):
    title: str | None = None
    objectives: str | None = None
    body: str | None = None
    position: int | None = None
    is_enrichment: bool | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str | None) -> str | None:
        return _not_blank(v, "Title")

    @field_validator("position")
    @classmethod
    def _position_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Position must be 1 or greater.")
        return v


class ResourceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    lesson_id: int
    file_name: str
    mime_type: str
    size_bytes: int
    uploaded_at: datetime


class LessonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    title: str
    objectives: str | None
    body: str | None
    position: int
    is_enrichment: bool
    created_at: datetime


class LessonDetail(LessonRead):
    resources: list[ResourceRead] = []
    topic_title: str = ""
    course_id: int = 0
    course_title: str = ""


class TopicRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    course_id: int
    title: str
    position: int
    mastery_threshold: int
    description: str | None
    course_title: str = ""
    lessons: list[LessonRead] = []
