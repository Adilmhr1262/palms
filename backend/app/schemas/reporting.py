"""Schemas for research evaluation records and academic reports."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResearchSessionCreate(BaseModel):
    student_id: int
    pre_test_score: float | None = None
    post_test_score: float | None = None
    learning_period: str | None = None
    notes: str | None = None


class ResearchSessionUpdate(BaseModel):
    pre_test_score: float | None = None
    post_test_score: float | None = None
    learning_period: str | None = None
    notes: str | None = None


class ResearchSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_name: str
    class_id: int
    class_name: str
    course_id: int
    course_title: str
    pre_test_score: float | None
    post_test_score: float | None
    learning_period: str | None
    score_change: float | None
    notes: str | None
    created_at: datetime


class ClassProgressRow(BaseModel):
    student_id: int
    student_name: str
    topic_id: int
    topic_title: str
    attempts_count: int
    latest_score: float | None
    best_score: float | None
    mastery_status: str | None


class StudentProgressRow(BaseModel):
    topic_id: int
    topic_title: str
    lessons_completed: int
    lessons_total: int
    assessment_attempts: int
    latest_score: float | None
    mastery_status: str | None


class FeedbackHistoryRow(BaseModel):
    date: datetime | None
    course_title: str
    topic_title: str
    assessment_title: str
    score: str
    teacher_comment: str | None
    intervention: str | None


class StudentFeedbackRow(BaseModel):
    date: datetime | None
    topic_title: str
    assessment_title: str
    score: str
    teacher_comment: str | None
    suggestion: str | None
