from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.assessment import AttemptStatus, QuestionType
from app.models.mastery import MasteryStatus


class QuestionCreate(BaseModel):
    qtype: QuestionType
    prompt: str
    options: list[str] | None = None
    correct_option: int | None = None
    model_answer: str | None = None
    points: int = 1

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("The question prompt is required.")
        return v

    @field_validator("points")
    @classmethod
    def _points_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Points must be 1 or greater.")
        return v

    @model_validator(mode="after")
    def _check_type_fields(self):
        if self.qtype == QuestionType.mcq:
            options = [o.strip() for o in (self.options or []) if o.strip()]
            if len(options) < 2:
                raise ValueError("Multiple choice needs at least two options.")
            if len(options) > 6:
                raise ValueError("Multiple choice allows at most six options.")
            if self.correct_option is None or not 0 <= self.correct_option < len(options):
                raise ValueError("Choose which option is correct.")
            self.options = options
        elif self.qtype == QuestionType.true_false:
            if self.correct_option not in (0, 1):
                raise ValueError("True/false needs a correct answer (true or false).")
            self.options = None
        else:
            self.options = None
            self.correct_option = None
            if self.model_answer is not None:
                self.model_answer = self.model_answer.strip() or None
        return self


class QuestionUpdate(BaseModel):
    prompt: str | None = None
    options: list[str] | None = None
    correct_option: int | None = None
    model_answer: str | None = None
    points: int | None = None

    @field_validator("prompt")
    @classmethod
    def _prompt_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("The question prompt is required.")
        return v

    @field_validator("points")
    @classmethod
    def _points_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Points must be 1 or greater.")
        return v


class QuestionRead(BaseModel):
    """Full question view for teachers (includes correct answers)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    qtype: QuestionType
    prompt: str
    options: list[str] | None
    correct_option: int | None
    model_answer: str | None
    points: int
    created_at: datetime


class QuestionPublic(BaseModel):
    """Student-safe question view. Never carries correct answers."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    qtype: QuestionType
    prompt: str
    options: list[str] | None
    points: int
    position: int = 0


class AssessmentCreate(BaseModel):
    title: str
    instructions: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title is required.")
        return v


class AssessmentUpdate(BaseModel):
    title: str | None = None
    instructions: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title is required.")
        return v


class AssessmentQuestionAdd(BaseModel):
    question_id: int
    position: int | None = None

    @field_validator("position")
    @classmethod
    def _position_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("Position must be 1 or greater.")
        return v


class AssessmentQuestionUpdate(BaseModel):
    position: int

    @field_validator("position")
    @classmethod
    def _position_positive(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Position must be 1 or greater.")
        return v


class AssessmentQuestionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    question_id: int
    position: int
    question: QuestionRead | None = None


class AssessmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    topic_id: int
    title: str
    instructions: str | None
    is_published: bool
    created_at: datetime
    question_count: int = 0
    topic_title: str = ""


class AssessmentDetail(AssessmentRead):
    questions: list[AssessmentQuestionRead] = []


class PublishUpdate(BaseModel):
    is_published: bool


class AnswerInput(BaseModel):
    question_id: int
    selected_option: int | None = None
    student_text: str | None = None

    @field_validator("student_text")
    @classmethod
    def _text_trimmed(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            return v or None
        return v


class AnswerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_id: int
    student_text: str | None
    selected_option: int | None
    # Grading fields are filled in step 5; present but null for now.
    is_correct: bool | None = None
    points_earned: int | None = None


class AttemptRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    assessment_id: int
    student_id: int
    status: AttemptStatus
    started_at: datetime
    submitted_at: datetime | None
    total_score: int | None = None
    max_score: int | None = None


class AnswerGraded(AnswerRead):
    """Answer view with teacher grading fields."""

    teacher_comment: str | None = None
    graded_by: int | None = None
    graded_at: datetime | None = None


class AttemptDetail(AttemptRead):
    questions: list[QuestionPublic] = []
    answers: list[AnswerGraded] = []
    assessment_title: str = ""
    student_name: str = ""


class GradingQueueItem(BaseModel):
    """One short answer awaiting (or having received) teacher review."""

    model_config = ConfigDict(from_attributes=True)

    answer_id: int
    attempt_id: int
    student_id: int
    student_name: str = ""
    question_id: int
    question_prompt: str = ""
    question_points: int = 0
    student_text: str | None = None
    points_earned: int | None = None
    teacher_comment: str | None = None
    submitted_at: datetime | None = None


class GradeAnswerInput(BaseModel):
    points_earned: int
    teacher_comment: str | None = None

    @field_validator("points_earned")
    @classmethod
    def _points_not_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Points cannot be negative.")
        return v

    @field_validator("teacher_comment")
    @classmethod
    def _comment_trimmed(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            return v or None
        return v


class MasteryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    topic_id: int
    attempts_count: int
    latest_score: float | None
    best_score: float | None
    status: MasteryStatus | None
    updated_at: datetime
    student_name: str = ""
    topic_title: str = ""
