# PALMS Installation and Operations Guide

Personalized Adaptive Learning Management System: a mastery-based learning
platform for education research. Teachers build courses, topics, lessons, and
assessments; students study, take assessments, and receive recommendations
that carry their reason; researchers measure learning over time.

## Requirements

- Docker and Docker Compose (for the packaged setup), or
- Python 3.12+, Node.js 20+, and PostgreSQL 16 (for a manual setup)

## Option 1: Run with Docker (recommended)

```bash
cd palms
docker compose up --build
```

The backend container runs migrations and loads the demo data
automatically on first start, so sign-in works right away.

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API health: http://localhost:8000/api/v1/health
- Database: localhost:5432 (user `palms`, password `palms`, database `palms`)

Before any shared deployment, copy `backend/.env.example` to `backend/.env`
and set a real `JWT_SECRET`. The backend refuses to start with a placeholder
secret when `ENV=production`.

## Option 2: Run manually

Backend:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # then edit DATABASE_URL and JWT_SECRET
alembic upgrade head         # create the tables
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev                  # serves http://localhost:3000
```

The frontend proxies API calls to the backend. Set `BACKEND_URL` if the
backend is not at `http://localhost:8000`.

## Environment variables

Backend (`backend/.env`):

| Variable | Default | Purpose |
|----------|---------|---------|
| `ENV` | `development` | Set to `production` for deployments; enables the JWT secret check |
| `DATABASE_URL` | `postgresql+psycopg://palms:palms@localhost:5432/palms` | SQLAlchemy database URL |
| `JWT_SECRET` | `change-me-to-a-long-random-string` | Secret for signing access tokens; must be replaced in production |
| `JWT_ALGORITHM` | `HS256` | Token signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `120` | Access token lifetime |
| `UPLOAD_DIR` | `uploads` | Directory for lesson resource files |
| `MAX_UPLOAD_MB` | `10` | Maximum resource file size |

Frontend:

| Variable | Default | Purpose |
|----------|---------|---------|
| `BACKEND_URL` | `http://localhost:8000` | Backend base URL for the API proxy |
| `COOKIE_SECURE` | unset | Set to `true` to mark the session cookie Secure (HTTPS deployments) |

## Demo data

The demonstration dataset shows the complete workflow: one administrator,
two teachers, five students, the Mathematics Foundations course with four
topics, published assessments, graded attempts, feedback, recommendations
covering all five rules, and research records. All demo accounts use the
password `demo1234`.

```bash
cd backend
alembic upgrade head
python -m app.seed.seed_demo
```

The seed is idempotent and safe to rerun. On a database that already has
the seed, rerunning does not duplicate attempts.

Demo accounts (password `demo1234` for all):

- Administrator: Ayesha Khan, `admin@palms.edu`
- Teachers: Sana Malik, `sana.malik@palms.edu`; Imran Sheikh, `imran.sheikh@palms.edu`
- Students: Ali Raza (`ali.raza@student.palms.edu`), Fatima Noor (`fatima.noor@student.palms.edu`), Usman Tariq (`usman.tariq@student.palms.edu`), Hina Shah (`hina.shah@student.palms.edu`), Danish Ali (`danish.ali@student.palms.edu`)

Demonstration cases:

- Ali Raza: high performer, Fractions 7/8 then 8/8, mastery 100 percent, enrichment recommendations
- Fatima Noor: needs support, Fractions 2/8 then 3/8, mastery 37.5 percent, intervention recommendations
- Usman Tariq: improving, Decimals 1/6 then 4/6, mastery 66.7 percent, Developing
- Hina Shah: enrolled, one lesson completed, no attempt yet
- Danish Ali: Decimals 5/6, mastery 83.3 percent, Proficient

## Project structure

```
palms/
  backend/
    app/
      main.py            # FastAPI app, router registration
      core/
        config.py        # settings (environment variables)
        security.py      # password hashing, JWT issue/verify
        deps.py          # get_current_user, require_admin/teacher/student
      db/
        session.py       # engine and session factory
        base.py          # declarative base and model imports
      models/            # SQLAlchemy models: user, course, topic, lesson,
                         # resource, question, assessment, attempt, answer,
                         # mastery, recommendation, enrollment, class,
                         # lesson_progress, research_session, feedback
      schemas/           # Pydantic request/response schemas
      routers/           # auth, users, courses, classes, content, bank,
                         # assessments, grading, recommendations, reports,
                         # research
      services/          # grading.py (auto-grading), mastery.py
                         # (recalculation + recommendation generation),
                         # access.py (course/class visibility checks)
      seed/              # seed_content.py, seed_demo.py
    alembic/             # migrations 001-007 (reversible)
    tests/               # pytest suite (84 tests)
  frontend/
    app/                 # Next.js app router pages
      login/             # sign-in
      admin/users/       # user management
      teacher/           # courses, classes, questions, grading,
                         # interventions, feedback, reports, research
      student/           # classes, lessons, assessments, results,
                         # recommendations, progress, feedback
      api/
        auth/            # login/logout (sets the httpOnly session cookie)
        proxy/           # forwards API calls with the session token
    components/          # shared UI: tables, forms, document pages
    lib/                 # API client, auth cookie helpers
  design/
    DESIGN.md            # visual and interaction rules
    er-diagram.svg       # entity-relationship diagram
    wireframes.html      # page wireframes
  docker-compose.yml
  PLAN.md / IMPLEMENTATION.md  # architecture and build record
```

## System workflow

1. An administrator creates accounts and assigns roles (admin, teacher, student).
2. A teacher builds a course: topics, lessons (title, objectives, text,
   downloadable resources), and a question bank of MCQ, True/False, and
   Short Answer items.
3. A teacher assembles assessments from the bank and publishes them; a
   teacher creates a class, assigns it a course, and enrolls students.
4. A student studies lessons, marks them complete, and takes assessments
   one question per view.
5. MCQ and True/False answers grade automatically on submit; Short Answer
   answers go to the teacher's grading queue with a rubric field.
6. Every graded attempt recalculates topic mastery (bands: 0-49 Needs
   Support, 50-69 Developing, 70-84 Proficient, 85-100 Mastered; per-topic
   threshold, default 70) and regenerates recommendations. Each
   recommendation stores its rule and a plain-language educational reason.
   Five rules run in order: repeated difficulty, low performance,
   developing, mastery achieved, high achievement.
7. Teachers review per-student and per-class progress on the reports pages,
   read intervention flags, leave feedback on graded answers, and record
   research sessions with pre/post scores; score change is computed
   server-side as a measured value.
8. Teachers and admins can export mastery, assessment, and research data
   as CSV (class-scoped, teacher/admin only).

## Roles and access summary

- Students see only their own attempts, mastery, recommendations, and
  feedback, and only the courses and classes they are enrolled in.
- Teachers manage only the courses they teach and the classes they own;
  admins manage everything.
- Uploaded resource files are served only through the authenticated
  download endpoint, which checks course access.
- Sign-in uses an httpOnly, SameSite=Lax session cookie; failed sign-in
  attempts are rate-limited.

## Testing

```bash
cd backend
.venv/bin/python -m pytest tests/ -q
```

The suite covers grading, mastery, recommendations, permissions,
exports, research sessions, seed idempotency, and security (84 tests).

```bash
cd frontend
npm run build
```

The production build must compile with no type errors.
