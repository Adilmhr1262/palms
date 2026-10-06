from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from app.models.recommendation import RecommendationStatus


class RecommendationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    topic_id: int
    rule_code: str
    title: str
    message: str
    reason: str
    status: RecommendationStatus
    teacher_note: str | None = None
    created_at: datetime
    updated_at: datetime
    student_name: str = ""
    topic_title: str = ""
    course_title: str = ""


class RecommendationReviewInput(BaseModel):
    teacher_note: str = ""

    @field_validator("teacher_note")
    @classmethod
    def strip_note(cls, v: str) -> str:
        return v.strip()


class PathLesson(BaseModel):
    id: int
    title: str
    position: int
    completed: bool = False


class PathTopic(BaseModel):
    id: int
    title: str
    position: int
    mastery_status: str | None = None
    latest_score: float | None = None
    lessons: list[PathLesson] = []


class LearningPathRead(BaseModel):
    class_id: int
    class_name: str
    course_id: int
    course_title: str
    topics: list[PathTopic] = []
    current_activity: RecommendationRead | None = None
    next_topic_id: int | None = None
