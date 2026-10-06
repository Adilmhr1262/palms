from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core import access
from app.core.deps import get_current_user, require_student, require_teacher
from app.db.session import get_db
from app.models.assessment import (
    Answer,
    Assessment,
    AssessmentQuestion,
    Attempt,
    AttemptStatus,
    Question,
    QuestionType,
)
from app.services.grading import auto_grade_attempt, finalize_attempt
from app.services.mastery import recalculate_mastery
from app.models.content import Topic
from app.models.user import User, UserRole
from app.schemas.assessment import (
    AnswerGraded,
    AnswerInput,
    AnswerRead,
    AssessmentCreate,
    AssessmentDetail,
    AssessmentQuestionAdd,
    AssessmentQuestionRead,
    AssessmentQuestionUpdate,
    AssessmentRead,
    AssessmentUpdate,
    AttemptDetail,
    AttemptRead,
    PublishUpdate,
    QuestionPublic,
    QuestionRead,
)

router = APIRouter(tags=["assessments"])


def _get_topic_or_404(db: Session, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found."
        )
    return topic


def _get_assessment_or_404(db: Session, assessment_id: int) -> Assessment:
    assessment = db.get(Assessment, assessment_id)
    if assessment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found."
        )
    return assessment


def _require_manage(db: Session, user: User, assessment: Assessment) -> None:
    if not access.can_manage_course(db, user, assessment.topic.course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can manage assessments.",
        )


def _read_assessment(db: Session, assessment: Assessment) -> AssessmentRead:
    read = AssessmentRead.model_validate(assessment)
    read.question_count = len(assessment.questions)
    read.topic_title = assessment.topic.title
    return read


def _detail_assessment(db: Session, assessment: Assessment) -> AssessmentDetail:
    detail = AssessmentDetail.model_validate(_read_assessment(db, assessment))
    items = []
    for aq in assessment.questions:
        item = AssessmentQuestionRead.model_validate(aq)
        item.question = QuestionRead.model_validate(aq.question)
        items.append(item)
    detail.questions = items
    return detail


@router.get("/topics/{topic_id}/assessments", response_model=list[AssessmentRead])
def list_assessments(
    topic_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    topic = _get_topic_or_404(db, topic_id)
    if not access.can_view_course(db, user, topic.course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course.",
        )
    query = select(Assessment).where(Assessment.topic_id == topic.id)
    if not access.can_manage_course(db, user, topic.course_id):
        query = query.where(Assessment.is_published.is_(True))
    assessments = db.scalars(query.order_by(Assessment.created_at)).all()
    return [_read_assessment(db, a) for a in assessments]


@router.post(
    "/topics/{topic_id}/assessments",
    response_model=AssessmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_assessment(
    topic_id: int,
    body: AssessmentCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    topic = _get_topic_or_404(db, topic_id)
    if not access.can_manage_course(db, user, topic.course_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a teacher of this course can create assessments.",
        )
    assessment = Assessment(
        topic_id=topic.id,
        title=body.title,
        instructions=body.instructions,
        created_by=user.id,
    )
    db.add(assessment)
    db.commit()
    db.refresh(assessment)
    return _read_assessment(db, assessment)


@router.get("/assessments/{assessment_id}")
def get_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AssessmentDetail | AssessmentRead:
    """Teachers get the full builder view; students get metadata only."""
    assessment = _get_assessment_or_404(db, assessment_id)
    if not access.can_view_course(db, user, assessment.topic.course):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this course.",
        )
    if access.can_manage_course(db, user, assessment.topic.course_id):
        return _detail_assessment(db, assessment)
    if not assessment.is_published:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This assessment is not published.",
        )
    return _read_assessment(db, assessment)


@router.patch("/assessments/{assessment_id}", response_model=AssessmentRead)
def update_assessment(
    assessment_id: int,
    body: AssessmentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    if body.title is not None:
        assessment.title = body.title
    if body.instructions is not None:
        assessment.instructions = body.instructions or None
    db.commit()
    db.refresh(assessment)
    return _read_assessment(db, assessment)


@router.delete("/assessments/{assessment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assessment(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    db.delete(assessment)
    db.commit()


def _next_position(db: Session, assessment_id: int) -> int:
    current = (
        db.scalar(
            select(func.max(AssessmentQuestion.position)).where(
                AssessmentQuestion.assessment_id == assessment_id
            )
        )
        or 0
    )
    return current + 1


def _require_draft(assessment: Assessment) -> None:
    if assessment.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Published assessments cannot be changed. Unpublish first.",
        )


@router.post(
    "/assessments/{assessment_id}/questions",
    response_model=AssessmentQuestionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_assessment_question(
    assessment_id: int,
    body: AssessmentQuestionAdd,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    _require_draft(assessment)
    question = db.get(Question, body.question_id)
    if question is None or question.topic_id != assessment.topic_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Questions must come from this assessment's topic bank.",
        )
    existing = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.question_id == question.id,
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This question is already in the assessment.",
        )
    position = body.position or _next_position(db, assessment.id)
    link = AssessmentQuestion(
        assessment_id=assessment.id, question_id=question.id, position=position
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    item = AssessmentQuestionRead.model_validate(link)
    item.question = QuestionRead.model_validate(question)
    return item


@router.patch(
    "/assessments/{assessment_id}/questions/{question_id}",
    response_model=AssessmentQuestionRead,
)
def move_assessment_question(
    assessment_id: int,
    question_id: int,
    body: AssessmentQuestionUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    _require_draft(assessment)
    link = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.question_id == question_id,
        )
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found."
        )
    link.position = body.position
    db.commit()
    db.refresh(link)
    item = AssessmentQuestionRead.model_validate(link)
    item.question = QuestionRead.model_validate(link.question)
    return item


@router.delete(
    "/assessments/{assessment_id}/questions/{question_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_assessment_question(
    assessment_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    _require_draft(assessment)
    link = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == assessment.id,
            AssessmentQuestion.question_id == question_id,
        )
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Question not found."
        )
    db.delete(link)
    db.commit()


@router.patch("/assessments/{assessment_id}/publish", response_model=AssessmentRead)
def publish_assessment(
    assessment_id: int,
    body: PublishUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    if body.is_published and not assessment.questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An assessment needs at least one question before publishing.",
        )
    assessment.is_published = body.is_published
    db.commit()
    db.refresh(assessment)
    return _read_assessment(db, assessment)


def _can_attempt(db: Session, user: User, assessment: Assessment) -> bool:
    if user.role != UserRole.student:
        return False
    if not assessment.is_published:
        return False
    return assessment.topic.course_id in access.student_course_ids(db, user.id)


def _attempt_detail(db: Session, attempt: Attempt, student: User) -> AttemptDetail:
    detail = AttemptDetail.model_validate(attempt)
    detail.student_name = student.full_name
    detail.assessment_title = attempt.assessment.title
    questions = []
    for aq in attempt.assessment.questions:
        q = QuestionPublic.model_validate(aq.question)
        q.position = aq.position
        questions.append(q)
    detail.questions = questions
    detail.answers = [AnswerGraded.model_validate(a) for a in attempt.answers]
    return detail


@router.post("/assessments/{assessment_id}/attempts", response_model=AttemptDetail)
def start_attempt(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    if not _can_attempt(db, user, assessment):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You cannot take this assessment.",
        )
    existing = db.scalar(
        select(Attempt).where(
            Attempt.assessment_id == assessment.id,
            Attempt.student_id == user.id,
            Attempt.status == AttemptStatus.in_progress,
        )
    )
    if existing is not None:
        return _attempt_detail(db, existing, user)
    attempt = Attempt(assessment_id=assessment.id, student_id=user.id)
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    return _attempt_detail(db, attempt, user)


@router.get("/assessments/{assessment_id}/my-attempts", response_model=list[AttemptRead])
def my_attempts(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    attempts = db.scalars(
        select(Attempt)
        .where(
            Attempt.assessment_id == assessment.id,
            Attempt.student_id == user.id,
        )
        .order_by(Attempt.started_at.desc())
    ).all()
    return [AttemptRead.model_validate(a) for a in attempts]


def _get_attempt_or_404(db: Session, attempt_id: int) -> Attempt:
    attempt = db.get(Attempt, attempt_id)
    if attempt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Attempt not found."
        )
    return attempt


def _require_attempt_access(db: Session, user: User, attempt: Attempt) -> None:
    if user.role == UserRole.student and attempt.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This attempt belongs to another student.",
        )
    if user.role == UserRole.teacher and not access.can_manage_course(
        db, user, attempt.assessment.topic.course_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not teach this course.",
        )


@router.get("/attempts/{attempt_id}", response_model=AttemptDetail)
def get_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = _get_attempt_or_404(db, attempt_id)
    _require_attempt_access(db, user, attempt)
    student = db.get(User, attempt.student_id)
    return _attempt_detail(db, attempt, student)


@router.get("/assessments/{assessment_id}/attempts", response_model=list[AttemptDetail])
def list_attempts(
    assessment_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_teacher),
):
    assessment = _get_assessment_or_404(db, assessment_id)
    _require_manage(db, user, assessment)
    attempts = db.scalars(
        select(Attempt)
        .where(Attempt.assessment_id == assessment.id)
        .order_by(Attempt.started_at.desc())
    ).all()
    result = []
    for attempt in attempts:
        detail = AttemptDetail.model_validate(attempt)
        student = db.get(User, attempt.student_id)
        detail.student_name = student.full_name if student else ""
        detail.assessment_title = assessment.title
        result.append(detail)
    return result


@router.put("/attempts/{attempt_id}/answers", response_model=AnswerRead)
def save_answer(
    attempt_id: int,
    body: AnswerInput,
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
):
    attempt = _get_attempt_or_404(db, attempt_id)
    if attempt.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This attempt belongs to another student.",
        )
    if attempt.status != AttemptStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This attempt is already submitted.",
        )
    link = db.scalar(
        select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_id == attempt.assessment_id,
            AssessmentQuestion.question_id == body.question_id,
        )
    )
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This question is not part of the assessment.",
        )
    question = link.question
    if question.qtype == QuestionType.short_answer:
        if not body.student_text:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Write an answer before saving.",
            )
        selected, text = None, body.student_text
    elif question.qtype == QuestionType.true_false:
        if body.selected_option not in (0, 1):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Choose true or false.",
            )
        selected, text = body.selected_option, None
    else:
        options = question.options or []
        if body.selected_option is None or not 0 <= body.selected_option < len(options):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Choose one of the given options.",
            )
        selected, text = body.selected_option, None
    answer = db.scalar(
        select(Answer).where(
            Answer.attempt_id == attempt.id,
            Answer.question_id == question.id,
        )
    )
    if answer is None:
        answer = Answer(
            attempt_id=attempt.id,
            question_id=question.id,
            selected_option=selected,
            student_text=text,
        )
        db.add(answer)
    else:
        answer.selected_option = selected
        answer.student_text = text
    db.commit()
    db.refresh(answer)
    return AnswerRead.model_validate(answer)


@router.post("/attempts/{attempt_id}/submit", response_model=AttemptRead)
def submit_attempt(
    attempt_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_student),
):
    attempt = _get_attempt_or_404(db, attempt_id)
    if attempt.student_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This attempt belongs to another student.",
        )
    if attempt.status != AttemptStatus.in_progress:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This attempt is already submitted.",
        )
    attempt.status = AttemptStatus.submitted
    attempt.submitted_at = datetime.now(timezone.utc)
    attempt.max_score = sum(q.question.points for q in attempt.assessment.questions)
    # Automatic marking for closed questions runs at submit time. Short
    # answers stay pending until a teacher grades them.
    auto_grade_attempt(db, attempt)
    if finalize_attempt(db, attempt):
        recalculate_mastery(db, attempt.student_id, attempt.assessment.topic_id)
    db.commit()
    db.refresh(attempt)
    return AttemptRead.model_validate(attempt)
