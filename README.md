# PALMS

Personalized Adaptive Learning Management System. A mastery-based learning
platform for education research: teachers build courses, topics, lessons, and
assessments; students follow personalized learning pathways where every
recommendation carries its reason.

## Structure

- `backend/` — FastAPI + SQLAlchemy + Alembic, PostgreSQL
- `frontend/` — Next.js 15 + TypeScript + Tailwind
- `design/` — design system, wireframes, ER diagram (review material)
- `PLAN.md`, `IMPLEMENTATION.md` — architecture and build plan

## Run with Docker

Requirements: Docker and Docker Compose.

```bash
docker compose up --build
```

- Frontend: http://localhost:3000
- Backend: http://localhost:8000
- API health: http://localhost:8000/api/v1/health
- Database: localhost:5432 (user `palms`, password `palms`, database `palms`)

Copy `backend/.env.example` to `backend/.env` and set a real `JWT_SECRET`
before any shared deployment.

## Run the backend locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Run the frontend locally

```bash
cd frontend
npm install
npm run dev
```

## Migrations

```bash
cd backend
alembic upgrade head        # apply
alembic revision --autogenerate -m "describe the change"   # new
```

## Design rules

The interface follows `design/DESIGN.md`: paper background, clean sans for
application chrome, serif reserved for lesson reading, tables and rows instead
of card grids, minimal shadows, one restrained blue, no gamification, no
invented institution branding.
