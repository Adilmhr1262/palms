# PALMS Project Overview

## Project overview

PALMS (Personalized Adaptive Learning Management System) is a
mastery-based learning platform built for education research. Teachers
author courses, topics, lessons, and assessments; students study at
their own pace and take assessments; the system tracks mastery per
topic, explains every recommendation it makes, and supports
pre/post research evaluation. It was built as a demonstration platform
for education professors, showing how learning data can drive
personalized pathways without opaque automation.

## Objectives

1. Let teachers build structured courses (topics, lessons, resources,
   question banks, assessments) with minimal tooling.
2. Give students a clear study path: lessons, one-question-per-view
   assessments, results with per-question feedback.
3. Compute topic mastery from graded attempts using transparent,
   adjustable bands.
4. Generate recommendations that always carry their educational reason,
   so students and teachers understand why each one appears.
5. Support education research: pre/post test sessions, measured score
   changes, and class-scoped data exports.

## Technology stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2, Alembic, Pydantic 2,
  PostgreSQL 16 (SQLite works for local demos)
- Frontend: Next.js 15, React 19, TypeScript, Tailwind CSS
- Auth: JWT access tokens (2-hour lifetime) in an httpOnly,
  SameSite=Lax session cookie; bcrypt password hashing
- Deployment: Docker Compose (PostgreSQL + backend + frontend)

## Architecture

The system is a monorepo with a strict client-server split:

- The FastAPI backend owns all business logic and authorization. Every
  route checks the caller's role and their relationship to the
  course or class involved. The frontend never enforces permissions;
  it only hides navigation.
- The Next.js frontend is a thin client. Browser requests go to
  Next.js API routes: `/api/auth/*` handles sign-in and sets the
  session cookie, `/api/proxy/*` forwards calls to the backend with
  the token attached server-side. Tokens never touch browser
  JavaScript.
- Shared services in the backend:
  - `services/grading.py` — auto-grades MCQ and True/False on submit;
    short answers wait for teacher review.
  - `services/mastery.py` — recalculates topic mastery after every
    graded attempt and regenerates recommendations.
  - `services/access.py` — course/class visibility and management
    checks used by every router.

## Database overview

Migrations `001` through `007` (linear, reversible) create:

- `users` — accounts with roles admin, teacher, student
- `courses`, `topics`, `lessons`, `resources` — the content tree;
  resources store uploaded files by UUID name
- `questions` — the bank: MCQ, True/False, Short Answer
- `assessments`, `assessment_questions` — published quizzes assembled
  from the bank
- `attempts`, `answers` — student work and per-answer grading
- `mastery` — per-student, per-topic score, band, and threshold
- `recommendations` — one active row per student, topic, and rule,
  each with its rule code and plain-language reason
- `lesson_progress` — lesson completion tracking
- `classes`, `enrollments` — class rosters linking students to courses
- `research_sessions` — pre/post scores with server-computed change
- `feedback` — teacher comments on graded answers

## User roles

- **Student** — enrolls in classes, reads lessons, takes assessments,
  sees only their own attempts, mastery, recommendations, and
  feedback.
- **Teacher** — builds courses, topics, lessons, resources, question
  banks, and assessments; manages their own classes; grades short
  answers; views interventions, reports, and research pages for the
  courses they teach. Cannot see unrelated courses or classes.
- **Admin** — manages user accounts (create, activate/deactivate;
  cannot demote or deactivate themselves). Full read access.

## Adaptive learning workflow

1. A teacher publishes an assessment for a topic.
2. A student submits it. MCQ and True/False grade immediately;
   short answers enter the teacher's grading queue.
3. On every graded attempt, the system recalculates the student's
   topic mastery and maps it to a band:
   - 0-49 Needs Support
   - 50-69 Developing
   - 70-84 Proficient
   - 85-100 Mastered
   The pass threshold defaults to 70 and is adjustable per topic.
4. Recommendation rules run in fixed order and write one active
   recommendation per student, topic, and rule:
   1. `REPEATED_DIFFICULTY` — the last two graded attempts for the
      topic are below 50%
   2. `LOW_PERFORMANCE` — mastery below the topic threshold
   3. `DEVELOPING` — mastery in the Developing band
   4. `MASTERY_ACHIEVED` — mastery at or above the threshold
   5. `HIGH_ACHIEVEMENT` — mastery in the Mastered band
   Each recommendation stores its rule and a readable educational
   reason; dismissed or completed rows are kept for history.
5. Teachers see intervention flags for struggling students, leave
   feedback on answers, and record research sessions with pre/post
   scores. Score change is computed server-side and reported as a
   measured value.

## Installation

See `docs/INSTALLATION-AND-OPERATIONS.md` for Docker and manual
setup, environment variables, and run commands.

## Demo accounts

All demo accounts use the password `demo1234`:

- Admin: `admin@palms.edu` (Ayesha Khan)
- Teachers: `sana.malik@palms.edu` (Sana Malik),
  `imran.sheikh@palms.edu` (Imran Sheikh)
- Students: `ali.raza@student.palms.edu`,
  `fatima.noor@student.palms.edu`,
  `usman.tariq@student.palms.edu`,
  `hina.shah@student.palms.edu`,
  `danish.ali@student.palms.edu`

Seed with `python -m app.seed.seed_demo` after `alembic upgrade head`.
The seed is idempotent.

## Testing results

- Backend: 84 pytest tests pass — grading, mastery bands and
  recalculation, all five recommendation rules, permissions and data
  isolation, exports, research sessions, seed idempotency, and
  security (rate limiting, secret fail-fast, token lifetime, upload
  backdoor closed).
- Frontend: production build compiles cleanly; browser QA pass over
  all role routes with no console errors; teacher, student, and admin
  journeys verified end to end.
- Full QA record: `QA-RESULTS.md`. Final screenshots: `design/`.
