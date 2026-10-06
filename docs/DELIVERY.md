# PALMS Final Delivery

## Final review summary

Eleven build steps completed with per-step approval. The final state:

- Backend: FastAPI + SQLAlchemy + Alembic + PostgreSQL. 84 pytest
  tests pass. Seven linear, reversible migrations.
- Frontend: Next.js 15 + TypeScript + Tailwind. Production build
  compiles cleanly.
- Security: unauthenticated file serving closed, login rate limiting,
  production secret fail-fast, 2-hour tokens, per-route authorization.
- QA: browser pass over all role routes with no console errors;
  teacher, student, and admin journeys verified end to end; one UI
  bug found and fixed (mislabeled confirm button).
- Documentation: project overview, installation and operations guide,
  design system, ER diagram, wireframes, QA record.

No new features were added after Step 8. Steps 9-11 were hardening,
verification, and delivery only.

## Run instructions

Docker:

```bash
cd palms
docker compose up --build
# frontend http://localhost:3000, backend http://localhost:8000
```

Manual:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set DATABASE_URL and JWT_SECRET
alembic upgrade head
python -m app.seed.seed_demo   # demo data, idempotent
uvicorn app.main:app --reload

cd ../frontend
npm install
npm run dev
```

Tests:

```bash
cd backend && .venv/bin/python -m pytest tests/ -q
cd ../frontend && npm run build
```

Demo accounts (password `demo1234` for all): `admin@palms.edu`,
`sana.malik@palms.edu`, `imran.sheikh@palms.edu`,
`ali.raza@student.palms.edu`, `fatima.noor@student.palms.edu`,
`usman.tariq@student.palms.edu`, `hina.shah@student.palms.edu`,
`danish.ali@student.palms.edu`.

## Documentation list

- `docs/PROJECT-OVERVIEW.md` — overview, objectives, stack,
  architecture, database, roles, adaptive workflow, demo accounts,
  testing results
- `docs/INSTALLATION-AND-OPERATIONS.md` — install, environment
  variables, demo data, project structure, workflow, testing
- `README.md` — quick start
- `PLAN.md`, `IMPLEMENTATION.md` — architecture and build record
- `design/DESIGN.md` — visual and interaction rules
- `design/er-diagram.svg` — entity-relationship diagram
- `design/wireframes.html` — page wireframes
- `QA-RESULTS.md` — full verification record

## Known limitations

- The login rate limiter is in-memory per process; a multi-instance
  deployment needs shared storage.
- There is no token revocation list. Deactivation is checked on every
  request, but changing a password does not invalidate existing
  tokens before their 2-hour expiry.
- Research score changes are measured values, not causal claims.
- SQLite is fine for demos; production expects PostgreSQL 16.
- The demo seed uses fixed demonstration data; real deployments
  start empty and use `bootstrap_admin` for the first account.

## Final screenshots

In `design/`: palms-step10-login, palms-step10-admin-users,
palms-step10-teacher-courses, palms-step10-student-class,
palms-step10-assessment-take, palms-step10-assessment-result.
Earlier step screenshots (steps 6-8) are alongside them.
