"""Idempotent seed of the Mathematics Foundations course.

Creates the course, its four topics, and starter lessons. Attaches the
first teacher account found (or the admin) as a course teacher. Safe to
run repeatedly: it skips when the course already exists.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_session_factory

def _session():
    return get_session_factory()()
from app.models.academic import Course, CourseTeacher
from app.models.assessment import (
    Assessment,
    AssessmentQuestion,
    Question,
    QuestionType,
)
from app.models.content import Lesson, Topic
from app.models.user import User, UserRole

COURSE_TITLE = "Mathematics Foundations"

TOPICS = [
    {
        "title": "Fractions",
        "position": 1,
        "description": "Understanding parts of a whole, equivalence, and basic operations with fractions.",
        "lessons": [
            {
                "title": "What a fraction means",
                "position": 1,
                "objectives": "Define numerator and denominator.\nRepresent fractions with diagrams.\nRead and write simple fractions.",
                "body": (
                    "A fraction describes part of a whole. The bottom number, the denominator, "
                    "tells how many equal parts the whole is divided into. The top number, the "
                    "numerator, tells how many of those parts we are considering.\n\n"
                    "For example, in the fraction 3/4, the whole is divided into 4 equal parts "
                    "and we take 3 of them. If a pizza is cut into 4 equal slices and you eat 3, "
                    "you have eaten 3/4 of the pizza.\n\n"
                    "Fractions appear everywhere: half an hour, a quarter of a tank of fuel, "
                    "three quarters of a class present. Being able to read a fraction quickly "
                    "is the foundation for everything that follows in this topic."
                ),
            },
            {
                "title": "Equivalent fractions",
                "position": 2,
                "objectives": "Explain why multiplying top and bottom by the same number keeps the value.\nFind equivalent fractions.\nSimplify fractions to lowest terms.",
                "body": (
                    "Two fractions are equivalent when they describe the same amount. The "
                    "fractions 1/2 and 2/4 are equivalent: shading one half of a bar covers "
                    "exactly as much as shading two quarters.\n\n"
                    "To find an equivalent fraction, multiply (or divide) the numerator and "
                    "the denominator by the same non-zero number. So 2/3 becomes 4/6 when both "
                    "parts are doubled, and 6/9 becomes 2/3 when both are divided by 3.\n\n"
                    "A fraction is in lowest terms when no number except 1 divides both the "
                    "numerator and the denominator. Always simplify answers: 4/6 should be "
                    "written as 2/3."
                ),
            },
            {
                "title": "Adding and subtracting fractions",
                "position": 3,
                "is_enrichment": True,
                "objectives": "Add fractions with the same denominator.\nFind a common denominator.\nAdd and subtract fractions with different denominators.",
                "body": (
                    "When the denominators match, add or subtract the numerators and keep the "
                    "denominator: 2/7 + 3/7 = 5/7.\n\n"
                    "When they differ, first rewrite both fractions with a common denominator. "
                    "The easiest choice is the product of the two denominators, though the "
                    "smallest common denominator keeps numbers manageable. For 1/4 + 2/3, use "
                    "12: 3/12 + 8/12 = 11/12.\n\n"
                    "Work step by step: find the common denominator, convert each fraction, "
                    "add or subtract the numerators, then simplify the result to lowest terms."
                ),
            },
        ],
    },
    {
        "title": "Decimals",
        "position": 2,
        "description": "Place value, comparing decimals, and the connection between decimals and fractions.",
        "lessons": [
            {
                "title": "Place value and decimals",
                "position": 1,
                "objectives": "Name the place value of each digit after the decimal point.\nRead and write decimal numbers.",
                "body": (
                    "The decimal point separates whole units from parts of a unit. To its right, "
                    "each place is ten times smaller than the one before: tenths, hundredths, "
                    "thousandths.\n\n"
                    "In 4.36, the 3 is in the tenths place (3 tenths) and the 6 is in the "
                    "hundredths place (6 hundredths). Read 4.36 as 'four point three six'.\n\n"
                    "Adding zeros to the right of the last decimal digit does not change the "
                    "value: 0.5, 0.50, and 0.500 are all equal. This fact is useful when "
                    "comparing decimals or lining them up for addition."
                ),
            },
            {
                "title": "Comparing and ordering decimals",
                "position": 2,
                "objectives": "Compare two decimals digit by digit.\nOrder a set of decimals from smallest to largest.",
                "body": (
                    "To compare decimals, line up the decimal points and compare digit by "
                    "digit from the left. The first place where the digits differ decides.\n\n"
                    "Compare 0.47 and 0.5. Write 0.5 as 0.50. The tenths digits are 4 and 5, "
                    "so 0.47 is smaller. A common mistake is thinking 0.47 is larger because "
                    "47 is larger than 5; place value, not digit count, decides.\n\n"
                    "To order several decimals, write them with the same number of decimal "
                    "places first, then compare from the leftmost digit."
                ),
            },
            {
                "title": "Decimals and fractions",
                "position": 3,
                "is_enrichment": True,
                "objectives": "Convert between fractions and decimals.\nRecognize common equivalents such as 1/2 = 0.5.",
                "body": (
                    "Every fraction can be written as a decimal by dividing the numerator by "
                    "the denominator. 3/4 becomes 0.75 because 3 divided by 4 is 0.75.\n\n"
                    "Going the other way, read the decimal as a fraction: 0.25 is 'twenty-five "
                    "hundredths', or 25/100, which simplifies to 1/4.\n\n"
                    "Memorize the common conversions: 1/2 = 0.5, 1/4 = 0.25, 3/4 = 0.75, "
                    "1/5 = 0.2, 1/10 = 0.1. They appear constantly in later work with "
                    "percentages and measurement."
                ),
            },
        ],
    },
    {
        "title": "Percentages",
        "position": 3,
        "description": "Percent as parts per hundred, and finding a percentage of a quantity.",
        "lessons": [
            {
                "title": "Percent as parts of a hundred",
                "position": 1,
                "objectives": "Explain what a percentage means.\nConvert between percentages, fractions, and decimals.",
                "body": (
                    "Percent means 'per hundred'. 37 percent, written 37%, means 37 out of "
                    "every 100, or the fraction 37/100, or the decimal 0.37.\n\n"
                    "To convert a percentage to a decimal, divide by 100: move the decimal "
                    "point two places left. 80% becomes 0.80. To convert a decimal to a "
                    "percentage, multiply by 100: 0.06 becomes 6%.\n\n"
                    "100% of something is the whole thing; more than 100% means more than "
                    "the whole, which makes sense for growth: a 120% increase means the "
                    "quantity more than doubled."
                ),
            },
            {
                "title": "Finding a percent of a quantity",
                "position": 2,
                "is_enrichment": True,
                "objectives": "Calculate a percentage of a number.\nSolve simple discount and increase problems.",
                "body": (
                    "To find a percentage of a quantity, convert the percentage to a decimal "
                    "and multiply. 20% of 450 is 0.20 x 450 = 90.\n\n"
                    "A common application is the discount: a Rs 2,000 item at 15% off costs "
                    "2,000 - (0.15 x 2,000) = 2,000 - 300 = Rs 1,700.\n\n"
                    "Check your answer for sense. 20% is one fifth, so 20% of 450 should be "
                    "close to 450/5 = 90. Estimation catches most arithmetic slips."
                ),
            },
        ],
    },
    {
        "title": "Basic Algebra",
        "position": 4,
        "description": "Variables, expressions, and solving one-step equations.",
        "lessons": [
            {
                "title": "Variables and expressions",
                "position": 1,
                "objectives": "Explain what a variable represents.\nWrite algebraic expressions from word descriptions.\nEvaluate expressions for a given value.",
                "body": (
                    "A variable is a letter that stands for a number we do not know yet, "
                    "usually x. An expression combines numbers, variables, and operations, "
                    "for example 3x + 2.\n\n"
                    "'Three more than twice a number' becomes the expression 2x + 3. "
                    "Translating words into symbols is the central skill of algebra.\n\n"
                    "To evaluate an expression, replace the variable with the given number "
                    "and compute: when x = 4, the value of 3x + 2 is 3(4) + 2 = 14."
                ),
            },
            {
                "title": "Solving one-step equations",
                "position": 2,
                "is_enrichment": True,
                "objectives": "Use inverse operations to isolate the variable.\nCheck a solution by substitution.",
                "body": (
                    "An equation states that two expressions are equal, for example x + 5 = 12. "
                    "Solving it means finding the value of x that makes the statement true.\n\n"
                    "Use the inverse operation to undo what is done to x. In x + 5 = 12, "
                    "subtract 5 from both sides: x = 7. In 4x = 20, divide both sides by 4: "
                    "x = 5.\n\n"
                    "Whatever you do to one side, do to the other; that is what keeps the "
                    "equation balanced. Always check by substituting back: 7 + 5 = 12, correct."
                ),
            },
        ],
    },
]


def run() -> None:
    db: Session = _session()
    try:
        existing = db.scalar(select(Course).where(Course.title == COURSE_TITLE))
        if existing is not None:
            print(f"Seed: course '{COURSE_TITLE}' already exists, skipping.")
            seed_assessment(db)
            return
        owner = db.scalar(
            select(User).where(
                User.role == UserRole.teacher, User.is_active.is_(True)
            )
        )
        if owner is None:
            owner = db.scalar(
                select(User).where(
                    User.role == UserRole.admin, User.is_active.is_(True)
                )
            )
        course = Course(
            title=COURSE_TITLE,
            description="Core numeracy: fractions, decimals, percentages, and basic algebra.",
        )
        db.add(course)
        db.flush()
        if owner is not None:
            db.add(CourseTeacher(course_id=course.id, teacher_id=owner.id))
        for topic_data in TOPICS:
            topic = Topic(
                course_id=course.id,
                title=topic_data["title"],
                position=topic_data["position"],
                mastery_threshold=70,
                description=topic_data["description"],
            )
            db.add(topic)
            db.flush()
            for lesson_data in topic_data["lessons"]:
                db.add(
                    Lesson(
                        topic_id=topic.id,
                        title=lesson_data["title"],
                        objectives=lesson_data["objectives"],
                        body=lesson_data["body"],
                        position=lesson_data["position"],
                        is_enrichment=lesson_data.get("is_enrichment", False),
                    )
                )
        db.commit()
        print(f"Seed: course '{COURSE_TITLE}' created.")
        seed_assessment(db)
    finally:
        db.close()


def seed_assessment(db: Session) -> None:
    """Create a small published assessment for the Fractions topic.

    Idempotent: skips when the assessment already exists.
    """
    topic = db.scalar(
        select(Topic)
        .join(Course, Course.id == Topic.course_id)
        .where(Course.title == COURSE_TITLE, Topic.title == "Fractions")
    )
    if topic is None:
        return
    existing = db.scalar(
        select(Assessment).where(
            Assessment.topic_id == topic.id,
            Assessment.title == "Fractions check",
        )
    )
    if existing is not None:
        return
    questions = [
        Question(
            topic_id=topic.id,
            qtype=QuestionType.mcq,
            prompt="In the fraction 3/4, what does the number 4 tell us?",
            options=[
                "How many parts are taken",
                "How many equal parts the whole is divided into",
                "The total value of the fraction",
                "How many parts remain",
            ],
            correct_option=1,
            points=2,
        ),
        Question(
            topic_id=topic.id,
            qtype=QuestionType.mcq,
            prompt="Which fraction is equivalent to 2/3?",
            options=["3/4", "4/6", "2/6", "6/9 reduced incorrectly"],
            correct_option=1,
            points=2,
        ),
        Question(
            topic_id=topic.id,
            qtype=QuestionType.true_false,
            prompt="The fractions 1/2 and 2/4 describe the same amount.",
            correct_option=0,
            points=1,
        ),
        Question(
            topic_id=topic.id,
            qtype=QuestionType.short_answer,
            prompt="Explain in your own words why multiplying the numerator and denominator by the same number does not change the value of a fraction.",
            model_answer=(
                "Multiplying both parts by the same number splits each part into smaller "
                "equal pieces while increasing the count of pieces by the same factor, "
                "so the total amount covered stays the same."
            ),
            points=3,
        ),
    ]
    db.add_all(questions)
    db.flush()
    assessment = Assessment(
        topic_id=topic.id,
        title="Fractions check",
        instructions=(
            "Answer each question in order. Multiple choice and true/false answers are "
            "saved as you choose them; short answers are saved when you move on. "
            "You may go back and change answers before submitting."
        ),
    )
    db.add(assessment)
    db.flush()
    for position, question in enumerate(questions, start=1):
        db.add(
            AssessmentQuestion(
                assessment_id=assessment.id,
                question_id=question.id,
                position=position,
            )
        )
    assessment.is_published = True
    db.commit()
    print("Seed: published assessment 'Fractions check' created.")


if __name__ == "__main__":
    run()
