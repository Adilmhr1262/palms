from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class CourseCreate(BaseModel):
    title: str
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title is required.")
        return v


class CourseUpdate(BaseModel):
    title: str | None = None
    description: str | None = None

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Title is required.")
        return v


class CourseTeacherInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    created_at: datetime
    topic_count: int = 0
    class_count: int = 0


class CourseDetail(CourseRead):
    teachers: list[CourseTeacherInfo] = []


class CourseTeacherAdd(BaseModel):
    teacher_id: int


class ClassCreate(BaseModel):
    name: str
    academic_year: str
    course_id: int | None = None
    teacher_id: int | None = None

    @field_validator("name", "academic_year")
    @classmethod
    def _not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("This field is required.")
        return v


class ClassUpdate(BaseModel):
    name: str | None = None
    academic_year: str | None = None
    course_id: int | None = None
    teacher_id: int | None = None


class EnrollmentInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_name: str = ""
    student_email: str = ""
    enrolled_at: datetime


class ClassRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    academic_year: str
    course_id: int | None
    course_title: str | None = None
    teacher_id: int
    teacher_name: str | None = None
    created_at: datetime
    student_count: int = 0


class ClassDetail(ClassRead):
    enrollments: list[EnrollmentInfo] = []


class EnrollmentAdd(BaseModel):
    student_id: int
