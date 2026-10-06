PALMS build plan. Prepared 2026-10-01 under the approved project decisions. This document covers architecture, modules, schema, user flows, API structure, and the roadmap. No code is written at this stage. The plan waits for approval before Design begins.

Note on language: the project brief bans a specific word from all project material. This plan avoids it throughout.

## Approved changes (2026-10-01, before Design)

1. Academic structure added: classes, enrollments, and course_teachers tables (below).
2. Course ownership changed from courses.teacher_id to a course_teachers join table, so several teachers can teach one course.
3. recommendations gains a reason_code column (LOW_SCORE, DEVELOPING, MASTERY_COMPLETE, REPEATED_FAILURE, ENRICHMENT_AVAILABLE) for research evaluation.
4. research_sessions table added for the Master's research layer (pre/post test scores per student).
5. Assessment layout fixed: one question per view.
6. Ordering fixed: position numbers in v1, no drag-and-drop.
7. Lesson editor stays structured (title, objectives, text, resources). No rich-text editor, no CMS scope creep.
8. Architect's addition, flagged for approval: classes.course_id links a class to the course it follows, so enrollments connect students to course content through their class.

## System architecture

Monorepo with three parts:

- frontend/: Next.js 15 + TypeScript (App Router). Tailwind used only for structured styling, not template-style design.
- backend/: Python FastAPI + SQLAlchemy 2.0 + Alembic migrations, Pydantic v2 schemas.
- docker-compose.yml: PostgreSQL 16, backend, frontend services. Local development first, cloud-ready structure.

Backend layering, in strict order:

1. Routers handle HTTP only (parse input, call services, return schemas).
2. Services hold business logic, including grading, mastery computation, and the recommendation engine.
3. Models are SQLAlchemy tables.
4. Schemas are Pydantic request/response contracts.

Authentication and authorization:

- FastAPI issues JWT access tokens on login. Passwords hashed with bcrypt.
- The frontend never holds the token in localStorage. A Next.js route handler proxies the login call to FastAPI and stores the token in an httpOnly cookie, then attaches it to proxied API calls.
- Role checks run in FastAPI dependencies on every request (require_admin, require_teacher, require_student_or_teacher, and so on). Next.js middleware guards route groups by role, but the backend is the real gate.
- Admin creates accounts and assigns roles. There is no public self-registration in v1.

Data flow for the central action (assessment submit):

1. Student submits answers to FastAPI.
2. Backend checks the attempt belongs to that student and is still open.
3. Grading service scores MCQ and true/false at once; short answers stay pending.
4. Mastery service recomputes the student's status for the topic.
5. Recommendation engine runs the five approved rules and stores new recommendations with their reason text.
6. Response returns the score, per-question results, pending items, and fresh recommendations.

File uploads: lesson resources are stored on a local disk volume (uploads/) in development and served through a FastAPI static mount; the database stores the path. MIME type allowlist and a 10 MB per-file cap.

## Module breakdown

1. Authentication and user management. Login, logout, JWT, three roles. Admin creates users, sets roles, activates and deactivates accounts.
2. Course management. Teachers create courses. Topics sit inside a course in a fixed order, each with an adjustable mastery threshold (default 70). Lessons sit inside a topic in a fixed order.
3. Lesson delivery. The student reading view shows title, learning objectives, text body, images and resources, downloadable files, and a link to the related assessment.
4. Question bank. Teacher creates, edits, and deletes questions per topic. Types: multiple choice (four options, one correct), true/false, short answer (with a model answer kept for the teacher's reference). Questions can be reused across assessments.
5. Assessments. The teacher assembles an assessment from bank questions for one topic, writes instructions, and publishes it. The student takes it in one sitting.
6. Grading. MCQ and true/false are graded on submit. Short answers go to the teacher grading queue with the student's text; the teacher assigns points and a comment. An attempt becomes fully graded once every item has a score.
7. Mastery tracking. Per student per topic: attempt count, latest score, best score, and a status band (needs_support, developing, proficient, mastered). Recomputed on every grading event.
8. Recommendation engine. The five approved rules run after each grading event. Each recommendation stores its rule, its message, and its target lesson. One active recommendation per student, topic, and rule; dismissed ones are not recreated until a new grading event.
9. Teacher feedback. Feedback history per student: scores, teacher comments on short answers, and flags. The student sees teacher comments on their own answers.
10. Reports. Student progress page (per-topic table with status). Teacher class view (students by topics matrix). Flags inbox for repeated-difficulty cases. CSV export of the mastery table.

## Database schema

PostgreSQL tables:

- users: id PK, full_name, email unique, password_hash, role (admin, teacher, student), is_active, created_at
- classes: id PK, name, academic_year, course_id FK to courses (nullable), teacher_id FK to users (class teacher), created_at
- enrollments: id PK, student_id FK to users, class_id FK to classes, enrolled_at; unique (student_id, class_id)
- courses: id PK, title, description, created_at
- course_teachers: course_id FK to courses, teacher_id FK to users; composite PK (course_id, teacher_id)
- research_sessions: id PK, student_id FK to users, class_id FK to classes (nullable), course_id FK to courses (nullable), pre_test_score, post_test_score, participation_period, notes, created_at
- topics: id PK, course_id FK, title, position, mastery_threshold (default 70), description
- lessons: id PK, topic_id FK, title, objectives (text), body (text), position, is_enrichment (boolean, used by the high-achievement rule), created_at
- resources: id PK, lesson_id FK, file_name, stored_path, mime_type, size_bytes, uploaded_at
- questions: id PK, topic_id FK, qtype (mcq, true_false, short_answer), prompt, options JSONB (for mcq), correct_option (for mcq and true_false), model_answer (for short answer), points, created_by FK to users
- assessments: id PK, topic_id FK, title, instructions, is_published, created_by FK to users, created_at
- assessment_questions: assessment_id FK, question_id FK, position; composite PK (assessment_id, question_id)
- attempts: id PK, assessment_id FK, student_id FK to users, started_at, submitted_at, status (in_progress, submitted, graded), total_score, max_score
- answers: id PK, attempt_id FK, question_id FK, student_text, selected_option, is_correct, points_earned, teacher_comment, graded_by FK to users (nullable), graded_at (nullable); unique (attempt_id, question_id)
- mastery: id PK, student_id FK, topic_id FK, attempts_count, latest_score, best_score, status (needs_support, developing, proficient, mastered), updated_at; unique (student_id, topic_id)
- recommendations: id PK, student_id FK, topic_id FK, rule_key, reason_code (LOW_SCORE, DEVELOPING, MASTERY_COMPLETE, REPEATED_FAILURE, ENRICHMENT_AVAILABLE), message, teacher_note (text, nullable), target_lesson_id FK to lessons (nullable), is_dismissed, created_at; partial unique index on (student_id, topic_id, rule_key) where is_dismissed is false
- flags: id PK, student_id FK, topic_id FK, reason, is_resolved, created_at

Indexes: users(email), topics(course_id, position), lessons(topic_id, position), questions(topic_id), attempts(student_id, assessment_id), answers(attempt_id), mastery(student_id), recommendations(student_id, is_dismissed).

Migrations run through Alembic from the first commit. A seed script inserts the Mathematics Foundations course (Fractions, Decimals, Percentages, Basic Algebra), lessons and questions for each topic, and four demo students with scripted attempt histories that demonstrate each of the five rules: a high performer, a student weak in Fractions, a student improving after remedial work, and a student who triggers the teacher flag.

## User flows

Student:

1. Log in. The dashboard shows active recommendations, each with its reason, and a "continue learning" pointer to the current topic.
2. Open the course, then the topic, then the lesson. Read objectives, text, and resources; download files; follow the link to the related assessment.
3. Take the assessment and submit once.
4. Result page shows the auto-graded score at once; short answers show as "awaiting teacher review". New recommendations appear with their reasons.
5. Progress page shows a table of topics with score, attempts, and status band.

Teacher:

1. Log in. "My courses": create a course, add topics (order and threshold), add lessons (objectives, text, uploads), mark one lesson per topic as enrichment. Invite co-teachers through course_teachers.
2. "My classes": create a class for an academic year, link it to a course, enroll students.
3. Question bank per topic: add multiple choice, true/false, and short answer questions.
4. Assemble an assessment: pick questions, write instructions, publish.
5. Grading queue: review short answers, assign points, write comments.
6. Class view: students-by-topics matrix with status bands. Flags inbox for repeated-difficulty cases. Per-student feedback history.
7. Research: record pre-test and post-test scores per student to evaluate improvement after the personalized pathway.

Admin:

1. Log in. Users table: create user, set role, activate or deactivate. Courses overview as a read-only list.

## API structure

Base path /api/v1. JSON throughout. Auth header: Authorization: Bearer <jwt>. Errors return {"detail": "..."} with proper HTTP status codes. Input validation through Pydantic (422 on bad input).

- POST /auth/login, POST /auth/logout, GET /auth/me
- GET /auth/me, POST /users, GET /users, PATCH /users/{id}, POST /users/{id}/deactivate (admin only)
- GET /classes, POST /classes, GET /classes/{id}, PATCH /classes/{id} (teacher; class teacher or admin)
- POST /classes/{id}/enrollments, DELETE /enrollments/{id} (teacher)
- POST /courses/{id}/teachers, DELETE /courses/{id}/teachers/{teacher_id} (admin or existing course teacher)
- GET /research/sessions, POST /research/sessions, PATCH /research/sessions/{id} (teacher)
- GET /courses, POST /courses, GET /courses/{id}, PATCH /courses/{id}, DELETE /courses/{id}
- GET /courses/{id}/topics, POST /courses/{id}/topics, PATCH /topics/{id}, DELETE /topics/{id}
- GET /topics/{id}/lessons, POST /topics/{id}/lessons, PATCH /lessons/{id}, DELETE /lessons/{id}
- POST /lessons/{id}/resources (multipart upload), DELETE /resources/{id}
- GET /topics/{id}/questions, POST /topics/{id}/questions, PATCH /questions/{id}, DELETE /questions/{id}
- GET /topics/{id}/assessments, POST /topics/{id}/assessments, PATCH /assessments/{id}/publish
- POST /assessments/{id}/attempts (start attempt), GET /attempts/{id}, POST /attempts/{id}/submit
- GET /grading/queue, PATCH /answers/{id}/grade (points plus comment)
- GET /mastery/me, GET /mastery/course/{course_id} (teacher matrix)
- GET /recommendations/me, POST /recommendations/{id}/dismiss
- GET /flags, POST /flags/{id}/resolve
- GET /reports/mastery.csv

## Development roadmap

Each phase ends with a working checkpoint. No phase starts until the previous one is reviewed.

1. Design. Lock the schema above, then lay out the five page contexts (lesson reading, assessment taking, teacher management, student progress, reports) under the academic design rules from the brief. Approval before build.
2. Backend foundation. Scaffold, Docker Compose, Alembic, auth with RBAC, user management.
3. Content modules. Courses, topics, lessons, resources, question bank.
4. Assessment and grading. Attempt lifecycle, auto-grading, teacher grading queue.
5. Mastery and recommendations. Status computation, five-rule engine, flags.
6. Feedback and reports. Comments, feedback history, progress pages, CSV export.
7. Seed data. Mathematics Foundations course and the four demo student profiles with scripted histories.
8. Frontend. Next.js pages for all three roles, wired to the API, styled to the academic brief.
9. Protect. Security review against the secure-coding checklist.
10. Verify. Tests: unit tests for the rules engine and grading, API integration tests, and a manual walkthrough of all three roles with a fix list.
11. Approve. Final review and delivery with run instructions.

## Risks

- Scope creep on the lesson editor. Controlled: structured fields only, no rich-text editor in v1, per the approved decisions.
- Auth bridging between Next.js and FastAPI. Controlled: token in an httpOnly cookie, attached by Next.js route handlers; FastAPI re-checks the role on every call.
- Short-answer grading bottleneck. Controlled: the queue is per teacher, auto-graded items score at once, and pending items are labeled honestly as awaiting review.
- Recommendation spam. Controlled: one active recommendation per student, topic, and rule; dismissal is respected until a new grading event.

## Resolved design decisions (2026-10-01)

- Assessment taking layout: one question per view, with a progress indicator and previous/next navigation.
- Reordering: position numbers in v1. No drag-and-drop.

End of plan. Awaiting approval to move to Design.
