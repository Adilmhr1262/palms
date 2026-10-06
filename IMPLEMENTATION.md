PALMS implementation plan. Prepared 2026-10-01 after design approval with refinements. This document defines the final component tree, the frontend and backend folder structures, the database migration plan, and the build sequence. No code is written yet; the plan waits for approval before the Build phase.

Note on language: the project brief bans a specific word from all project material. This document avoids it throughout.

## Final component tree (frontend)

AppShell
  SiteHeader (Brand, RoleNav, UserBlock)
  main
    page content (per route below)
  FooterLine

(auth) /login
  LoginPage
    LoginForm (EmailInput, PasswordInput, SubmitButton, FormError)

(student)
  StudentLayout (RoleNav: Dashboard, My classes, Progress)
  /dashboard -> StudentDashboard
    RecommendationList
      RecommendationRow (ReasonBadge, Message, ReasonText, ActionLink, DismissButton)
    ContinueLearning (current topic pointer)
    RecentResultsTable (DataTable)
  /classes/[id] -> ClassHome
    CourseOutline
      TopicRow (TopicLink, StatusBadge, MasteryBar)
  /lessons/[lessonId] -> LessonPage
    Breadcrumb
    LessonDocument (LessonTitle, ObjectivesList, BodyText, ResourceList, RelatedAssessmentCallout)
  /assessments/[id]/take -> AssessmentRunner
    ProgressTrack (QuestionCounter, ProgressBar)
    QuestionView
      MCQOptions | TrueFalseOptions | ShortAnswerInput
    QuestionNav (PreviousButton, NextButton, SubmitButton)
    ConfirmSubmit (UnansweredList)
  /assessments/[id]/result -> ResultPage
    ResultSummary (Score, StatusBadge)
    QuestionReview (per-question: Prompt, StudentAnswer, Correctness, Points)
    PendingNotice (short answers awaiting teacher review)
    NewRecommendations (RecommendationList)
  /progress -> ProgressPage
    MasteryTable (DataTable with MasteryBar + StatusBadge per topic)

(teacher)
  TeacherLayout (RoleNav + SectionNav: Courses, Classes, Question bank, Assessments, Grading, Flags, Research)
  /courses -> CourseListPage (DataTable, NewCourseButton)
  /courses/[id] -> CourseManagePage
    TopicTable (PositionInput, TopicLink, LessonCount, QuestionCount, ThresholdInput)
    LessonTable (PositionInput, LessonLink, EnrichmentBadge)
    CoTeacherList
  /classes -> ClassListPage (DataTable, NewClassButton)
  /classes/[id] -> ClassManagePage
    EnrollmentTable (StudentRow, RemoveButton, AddStudentForm)
    ClassMatrix (students by topics, StatusBadge cells)
  /bank/[topicId] -> QuestionBankPage
    QuestionTable (TypeBadge, Prompt, Points)
    QuestionForm (TypeSelect, PromptInput, OptionsEditor for MCQ, ModelAnswerInput)
  /assessments -> AssessmentListPage (DataTable, PublishToggle)
  /assessments/new -> AssessmentBuilder (QuestionPicker from bank, InstructionsInput, PositionList)
  /grading -> GradingQueuePage
    GradeItem (StudentAnswer, ModelAnswer, PointsInput, CommentInput, SaveGradeButton)
    GradedTable (history)
  /flags -> FlagsPage (FlagTable: Student, Topic, Reason, ResolveButton)
  /research -> ResearchPage
    ResearchTable (StudentIdentifier, PreTest, LearningPeriod, PostTest, Change, Notes)
    ResearchForm (ScoreInputs, PeriodInput, NotesInput)
  /students/[id] -> StudentDetailPage
    FeedbackHistory (AttemptsTable, TeacherComments)

(admin)
  AdminLayout (RoleNav: Users, Courses)
  /users -> UserAdminPage
    UserTable (Name, Email, RoleBadge, StatusBadge, EditLink)
    UserForm (NameInput, EmailInput, RoleSelect, ActiveToggle)
  /courses -> CourseOverviewPage (read-only DataTable)

Shared (components/)
  SiteHeader, RoleNav, DataTable, Pagination, StatusBadge, MasteryBar,
  RecommendationRow, EmptyState, ConfirmDialog,
  Form: TextInput, TextArea, SelectInput, NumberInput, PositionInput,
  LessonDocument, ResourceList, QuestionView

Route handlers (app/api/)
  auth/login, auth/logout, auth/me (cookie set/clear/read)
  proxy/[...path] (attaches JWT from httpOnly cookie, forwards to FastAPI)

Rules the tree follows: no gamification components exist anywhere. Tables carry data. RecommendationRow is a row, not a card. Serif styling applies only inside LessonDocument, QuestionView prompts, and student answer text.

## Frontend folder structure

frontend/
  app/
    layout.tsx
    globals.css (design tokens)
    (auth)/login/page.tsx
    admin/
      layout.tsx
      users/page.tsx
    student/ (steps 3+)
      layout.tsx
      dashboard/page.tsx
      classes/[id]/page.tsx
      lessons/[lessonId]/page.tsx
      assessments/[id]/take/page.tsx
      assessments/[id]/result/page.tsx
      progress/page.tsx
    teacher/ (steps 3+)
      layout.tsx
      courses/page.tsx
      courses/[id]/page.tsx
      classes/page.tsx
      classes/[id]/page.tsx
      bank/[topicId]/page.tsx
      assessments/page.tsx
      assessments/new/page.tsx
      grading/page.tsx
      flags/page.tsx
      research/page.tsx
      students/[id]/page.tsx
      courses/page.tsx
    api/
      auth/login/route.ts
      auth/logout/route.ts
      auth/me/route.ts
      proxy/[...path]/route.ts
  components/
    SiteHeader.tsx  RoleNav.tsx  DataTable.tsx  Pagination.tsx
    StatusBadge.tsx  MasteryBar.tsx  RecommendationRow.tsx
    EmptyState.tsx  ConfirmDialog.tsx
    LessonDocument.tsx  ResourceList.tsx  QuestionView.tsx
    forms/ (TextInput, TextArea, SelectInput, NumberInput, PositionInput)
    student/ (ContinueLearning, CourseOutline, TopicRow, AssessmentRunner,
              ResultSummary, QuestionReview, MasteryTable)
    teacher/ (TopicTable, LessonTable, CoTeacherList, EnrollmentTable,
              ClassMatrix, QuestionTable, QuestionForm, AssessmentBuilder,
              GradeItem, FlagTable, ResearchTable, ResearchForm, FeedbackHistory)
    admin/ (UserTable, UserForm)
  lib/
    api.ts (typed fetch helpers through /api/proxy)
    auth.ts (role helpers, route guard utilities)
    format.ts (scores, dates)
  middleware.ts (role-based route protection)
  tailwind.config.ts (tokens mapped from the design system)
  Dockerfile

## Backend folder structure

backend/
  app/
    main.py (FastAPI app, router registration, static mount for uploads)
    core/
      config.py (settings from environment)
      security.py (bcrypt hashing, JWT create/verify)
      deps.py (get_current_user, require_admin, require_teacher,
               require_teacher_or_admin, require_student)
    db/
      session.py (engine, session factory)
      base.py (declarative base, naming conventions)
    models/
      user.py (users)
      academic.py (classes, enrollments, courses, course_teachers)
      content.py (topics, lessons, resources)
      assessment.py (questions, assessments, assessment_questions,
                     attempts, answers)
      progress.py (mastery, recommendations, flags, research_sessions)
    schemas/
      user.py  academic.py  content.py  assessment.py  progress.py
      (Pydantic v2 request/response contracts, one module per domain)
    services/
      grading.py (auto-grade MCQ and true/false; finalize attempt status)
      mastery.py (recompute status band per student/topic)
      recommendations.py (the five rules; dedupe; reason codes)
      reports.py (mastery matrix, CSV export)
    routers/
      auth.py  users.py  classes.py  courses.py  content.py
      bank.py  assessments.py  attempts.py  grading.py
      mastery.py  recommendations.py  flags.py  research.py  reports.py
    seed/
      seed.py (Mathematics Foundations + 4 demo students + scripted histories)
  alembic/
    env.py
    versions/ (migrations below)
  tests/
    unit/ (test_rules.py, test_grading.py, test_mastery.py)
    integration/ (test_auth.py, test_content.py, test_assessments.py,
                  test_grading_flow.py, test_recommendations.py)
  uploads/ (local dev volume, gitignored)
  requirements.txt
  Dockerfile
  .env.example

docker-compose.yml (repo root)
  postgres 16 (volume pgdata)
  backend (build ./backend, uvicorn reload in dev)
  frontend (build ./frontend, dev server in dev)

## Database migration plan (Alembic, in order)

- 001_academic_core: users, courses, course_teachers, classes, enrollments.
  Indexes: users(email). Constraints: enrollments unique(student_id, class_id);
  course_teachers composite PK.
- 002_content: topics, lessons, resources.
  Indexes: topics(course_id, position), lessons(topic_id, position).
- 003_bank: questions, assessments, assessment_questions.
  Indexes: questions(topic_id). Constraints: assessment_questions composite PK.
- 004_attempts: attempts, answers.
  Indexes: attempts(student_id, assessment_id), answers(attempt_id).
  Constraints: answers unique(attempt_id, question_id).
- 005_progress: mastery, recommendations, flags, research_sessions.
  Indexes: mastery(student_id), recommendations(student_id, is_dismissed).
  Constraints: mastery unique(student_id, topic_id); recommendations partial
  unique(student_id, topic_id, rule_key) where is_dismissed is false.

Each migration is reversible (downgrade defined). Seed data is not a migration;
seed/seed.py runs separately and is idempotent (skips when data exists).

## Implementation sequence

Each step ends at a working checkpoint. Steps run in order; a step starts only
after the previous one is reviewed.

1. Scaffolding. Monorepo layout, docker-compose with Postgres, backend
   scaffold (settings, DB session, Alembic init), frontend scaffold
   (Next.js, Tailwind tokens, AppShell). Checkpoint: `docker compose up`
   serves an empty app shell and a FastAPI health check.
2. Auth and users. Migration 001 tables for users; hashing, JWT, RBAC
   dependencies; /auth and /users endpoints; login page, cookie proxy
   handlers, middleware guards, admin user table. Checkpoint: sign in as
   each role, admin creates users.
3. Academic structure and content. Migrations 001 remainder + 002;
   classes, enrollments, courses, course_teachers endpoints; teacher pages
   for courses, topics, lessons (position numbers), resources upload;
   class creation and enrollment. Checkpoint: teacher builds a course with
   topics and lessons and enrolls students in a class.
4. Question bank and assessments. Migration 003; bank CRUD, assessment
   assembly and publish; teacher bank and builder pages; student
   one-question-per-view take flow with confirm submit. Checkpoint:
   student completes an assessment end to end.
5. Grading and attempts. Migration 004; attempt lifecycle, auto-grading
   service, teacher grading queue page with points and comments.
   Checkpoint: MCQ scores at once, short answer graded by teacher.
6. Mastery, recommendations, flags. Migration 005 (mastery,
   recommendations, flags); mastery service, five-rule engine with
   reason codes; student dashboard feed, progress table, teacher matrix
   and flags inbox. Checkpoint: each of the five rules demonstrated
   with the seed histories.
7. Research and reports. Migration 005 (research_sessions); research
   recording and evaluation pages; CSV export. Checkpoint: pre/post
   table with computed change.
8. Seed data. Mathematics Foundations course (Fractions, Decimals,
   Percentages, Basic Algebra), lessons, questions, four demo students
   with scripted attempt histories covering all five rules.
   Checkpoint: fresh database seeds to a fully demonstrable state.
9. Protect. Security review against the secure-coding checklist:
   auth, RBAC, input validation, upload restrictions, error handling.
10. Verify. Unit tests (rules, grading, mastery), API integration tests,
    manual walkthrough of all three roles, fix list cleared.
11. Approve. Final review and delivery with run instructions.

End of implementation plan. Awaiting approval to begin the Build phase.

## Build log

### Step 4 - Question bank and assessments (completed 2026-10-01)

Actual migration numbering differs from the plan above (users already
occupied 001): 002 academic structure, 003 content, 004 assessments.
Migration 004 combines the planned 003_bank and 004_attempts into one
revision: questions, assessments, assessment_questions, attempts, answers.
Reversible; upgrade/downgrade/upgrade cycle verified on SQLite.

Backend (FastAPI):
- app/models/assessment.py: Question (qtype enum mcq/true_false/short_answer,
  options JSON, correct_option, model_answer, points), Assessment
  (title, instructions, is_published), AssessmentQuestion (composite PK,
  position), Attempt (status enum in_progress/submitted/graded, total_score,
  max_score), Answer (unique attempt/question, student_text,
  selected_option, grading fields reserved for step 5).
- app/routers/bank.py: question CRUD per topic, teacher-of-course only,
  per-type validation (mcq 2-6 options with a marked correct option,
  true/false needs a correct answer).
- app/routers/assessments.py: assessment CRUD per topic; question assembly
  with positions (draft only, same-topic questions, duplicates rejected);
  publish toggle (requires at least one question; question set locked while
  published); attempt start/resume (one in-progress attempt per student);
  per-question answer save with type-appropriate validation; submit
  (computes max_score, leaves total_score null for step 5 grading).
- Correct answers never reach students: QuestionPublic excludes
  correct_option/model_answer; student assessment GET returns metadata only.
- Seed: published "Fractions check" assessment (2 mcq, 1 true/false,
  1 short answer) on the Fractions topic, idempotent.
- New endpoint: GET /api/v1/topics/{topic_id} (topic with course title,
  visible to anyone with course access).

Frontend (Next.js):
- Teacher: /teacher/bank/[topicId] (question bank table, per-type
  create/edit form), /teacher/topics/[topicId]/assessments (assessment
  list, draft/published status), /teacher/assessments/[id] (builder:
  details edit, question picker from bank, position editing, publish
  toggle, attempts list). Course manage page links each topic to its
  bank and assessments.
- Student: class outline lists published assessments per topic with
  Start/Continue/Submitted state; /student/assessments/[id]/take
  (instructions intro, one-question-per-view, progress indicator,
  answers saved per question, review screen with unanswered warnings,
  submit confirmation); /student/assessments/[id]/result (submission
  receipt, honest note that grading arrives in the next step).
- No timers, no gamification, no quiz cards; serif prompts, neutral
  buttons, table management.

Verification: 41 pytest tests pass (13 auth + 16 academic/content +
12 assessment, covering bank RBAC, publish rules, attempt lifecycle,
answer validation, attempt isolation, and correct-answer non-leakage).
Frontend production build passes (19 routes). Browser walkthrough with
screenshots in design/.

Step 5 (grading) not started; awaiting review.

### Step 5 - Grading, mastery foundation, teacher feedback (completed 2026-10-01)

Migration 005_mastery: mastery table (student_id, topic_id unique pair;
attempts_count, latest_score, best_score, status enum
needs_support/developing/proficient/mastered, updated_at). Reversible;
upgrade/downgrade/upgrade cycle verified on SQLite.

Backend (FastAPI):
- app/services/grading.py: auto_grade_attempt (mcq/true_false compared
  against correct_option, full points or zero; every question gets an
  answer row so unanswered closed questions score zero and attempts
  cannot stall; short answers untouched), finalize_attempt (attempt
  becomes graded only when every question has a final score),
  grade_short_answer (points bounded 0..question points, comment,
  graded_by/at).
- app/services/mastery.py: mastery_status maps a percentage to a
  status using the topic's own mastery_threshold as the
  developing/proficient line (default 70 reproduces the 0-49/50-69/
  70-84/85-100 bands); recalculate_mastery rebuilds attempts_count,
  latest_score, best_score from graded attempts.
- app/routers/grading.py: GET /assessments/{id}/grading-queue (pending
  and reviewed short answers, teacher of the course only),
  POST /answers/{id}/grade (points + comment, re-finalizes the attempt
  and recalculates mastery), GET /topics/{id}/mastery (teacher sees
  all, student sees own).
- submit_attempt now auto-grades closed questions at submit time;
  short answers keep the attempt in "submitted" until a teacher grades
  them. AttemptDetail answers now carry teacher_comment (AnswerGraded).

Frontend (Next.js):
- Teacher: /teacher/assessments/[id]/grading (Awaiting review table
  with per-row points input, comment box, save; Reviewed table);
  builder header links the queue with a pending count; topic
  assessments page gains a Student mastery table.
- Student: result page rewritten (score with percentage when graded,
  per-question review with own answer, Correct/Incorrect and points
  for marked questions, teacher comments, "Short answer responses are
  awaiting teacher review." notice; correct options never shown).
  Class outline shows a per-topic mastery line (status, latest, best,
  graded attempts).
- Academic visual identity kept: tables, neutral buttons, serif for
  reading content, no gamification or decoration.

Verification: 50 pytest tests pass (13 auth + 16 academic/content +
12 assessment + 9 grading, covering auto-grading accuracy, pending
state, teacher workflow, unauthorized access, mastery recalculation,
and the 49/50/69/70/84/85 boundary cases plus threshold variation).
Frontend production build passes. Browser walkthrough with screenshots
in design/ (grading queue, result, mastery student + teacher views).

Step 6 (recommendations, flags, research) not started; awaiting review.


## Step 6 (2026-10-01) - Recommendation engine and personalized learning path
- Migration 006 (reversible, cycle-tested): `recommendations` (id, student_id, topic_id, rule_code, title, message, reason, status, teacher_note, created_at, updated_at) and `lesson_progress` (id, student_id, lesson_id, completed_at). Partial unique index `uq_recommendations_active` enforces at most one active recommendation per student + topic + rule_code; dismissed and completed rows stay stored. (Note: an initial draft carried a redundant full (student_id, topic_id) unique constraint; it was removed and the migration re-verified up/down/up.)
- Rule engine (`backend/app/services/recommendations.py`): five transparent rules in fixed priority order - REPEATED_DIFFICULTY (two latest attempts below 50%), LOW_PERFORMANCE (below 50%), DEVELOPING (50% to below topic threshold), MASTERY_ACHIEVED (reached threshold, unlocks next topic), HIGH_ACHIEVEMENT (85% or above, enrichment; coexists with mastery). Each stores an educational reason. Re-running with unchanged state is idempotent; a changed band completes the previous band's active recommendation. Runs automatically after every graded attempt via `recalculate_mastery`.
- APIs: GET /recommendations (student: own; teacher: own courses active, priority order), GET /recommendations/{id}, POST dismiss (owning student only), POST review (course teacher adds note, marks completed), POST /lessons/{id}/complete (enrolled students), GET /classes/{id}/learning-path (structure + completed lessons + highest-priority current activity + next available topic).
- Frontend: /student/recommendations (table: Topic, Recommendation, Reason, Status, Action; Open lesson, Start practice, Dismiss), /teacher/interventions (Student, Topic, Current mastery, Recommendation reason, Action; inline note + Mark reviewed), /student/classes/[id]/path (course -> topics -> lessons document hierarchy, completed lessons, current recommended activity, next available topic). Lesson pages have a "Mark as complete" button.
- Tests: 10 new recommendation tests (generation, duplicate prevention, dismissed persistence, rule priority, teacher/student visibility, mastery threshold change, repeated failure) - 60 backend tests pass total. No banned term found in new code. Production frontend build passes.
- Screenshots: palms-step6-student-recommendations.png, palms-step6-teacher-interventions.png, palms-step6-learning-path.png.


## Step 7 (2026-10-01) - Feedback, reports, and research evaluation
- Migration 007 (reversible, cycle-tested): `research_sessions` (id, student_id, class_id, course_id, pre_test_score, post_test_score, learning_period, score_change, notes, created_at, updated_at). lesson_progress already had completed_at, no change needed.
- Reports router: GET /classes/{id}/reports/class-progress (Student, Topic, Attempts, Latest score, Best score, Mastery status), GET /classes/{id}/reports/student-progress (Topic, Lessons completed, Assessment attempts, Latest score, Mastery status; students may view only their own), GET /classes/{id}/feedback-history (Date, Course, Topic, Assessment, Score, Teacher comment, Intervention), GET /feedback/my (own assessment feedback, teacher comments, improvement suggestions; private teacher notes never exposed).
- CSV exports (teacher/admin only, class-scoped, students get 403): /exports/mastery.csv, /exports/assessments.csv, /exports/research.csv; formula-injection guard on string cells.
- Research router: POST /classes/{id}/research-sessions (student must be enrolled), GET list, PATCH (explicit null clearing supported). score_change always computed server-side as post - pre (None when either missing); reported as a measured value only, never claimed as improvement.
- Frontend: /teacher/classes/[id]/feedback (student selector + history table), /student/feedback (own feedback table), /teacher/classes/[id]/reports (class progress table, per-student progress table, three CSV export buttons), /teacher/classes/[id]/research (add/edit form + records table with all requested fields). Class manage page links to all three. DataTable key constraint relaxed for id-less report rows.
- Tests: 8 new Step 7 tests (feedback visibility, student privacy, report filtering, CSV export permissions, research score calculation, unauthorized access) - 68 backend tests pass total. No banned term found in new code. Production frontend build passes.
- Screenshots: palms-step7-teacher-feedback.png, palms-step7-student-feedback.png, palms-step7-teacher-reports.png, palms-step7-research-evaluation.png.


## Step 8 (2026-10-01) - Seed data and demonstration scenarios
- New `backend/app/seed/seed_demo.py` (`python -m app.seed.seed_demo`): idempotent demo seed on a fresh database. 1 admin (Ayesha Khan), 2 teachers (Sana Malik, Imran Sheikh), 5 students, all with password demo1234. Builds on the base course seed: published assessments for Decimals, Percentages, Basic Algebra (MCQ + True/False + short answer each), one study-guide resource per topic, class 7-A (2026) with all 5 students enrolled, 3 research records.
- Attempts run through the real grading services (auto_grade_attempt, grade_short_answer, finalize_attempt, recalculate_mastery -> recommendation engine), with staggered dates and realistic teacher comments.
- Five scenarios: Ali Raza 7/8 -> 8/8 Fractions (Mastered, MASTERY_ACHIEVED + HIGH_ACHIEVEMENT); Fatima Noor 2/8 -> 3/8 Fractions (Needs Support, LOW_PERFORMANCE + REPEATED_DIFFICULTY); Usman Tariq 1/6 -> 4/6 Decimals (Developing, DEVELOPING after completing LOW_PERFORMANCE); Hina Shah one lesson, no attempts (incomplete learner); Danish Ali 5/6 Decimals (Proficient, MASTERY_ACHIEVED only). All five recommendation rules demonstrated. Research: 68->91 (+23), 31->38 (+7), 40->58 (+18), measured values only.
- Tests: 8 new seed tests (accounts/roles, all-role logins, course structure, scenarios, all five rules, research records, full workflow via API, idempotency) - 76 backend tests pass total. Fixed a latent import-time engine build in both seed modules (now lazy) and course-scoped all topic lookups.
- Screenshots: palms-step8-demo-class-report.png, palms-step8-demo-high-performer.png, palms-step8-demo-needs-support.png.


## Step 9 (2026-10-01) - Security review and hardening (no new features)
- HIGH fixed: `/uploads` was mounted as unauthenticated StaticFiles, bypassing the course-access check on resource downloads. Removed the mount and the frontend proxy's uploads branch; all downloads go through the authenticated `/resources/{id}/download` endpoint.
- MEDIUM fixed: no login rate limiting. Added in-memory brute-force protection on /auth/login: 10 failed attempts per client+email within 10 minutes -> 429; success clears the counter.
- MEDIUM fixed: placeholder JWT secret usable in production. Added `ENV` setting; the app refuses to start when `ENV=production` with a placeholder secret.
- LOW fixed: 8-hour access tokens. Reduced to 2 hours (backend setting + frontend cookie maxAge).
- Audited with no changes needed: bcrypt passwords (min 8), generic login errors (no enumeration), JWT expiry verified with DB-loaded roles and deactivation checks, httpOnly + SameSite=Lax cookies with Secure flag via env, upload MIME allowlist with UUID filenames and 10 MB cap, ORM-only queries (no SQLi), no dangerouslySetInnerHTML (no XSS), no CORS middleware (same-origin proxy), no debug mode, admin self-demote/deactivate protection, per-route authorization (students own-only, teachers own courses/classes, admins controlled).
- Tests: 8 new security tests (static backdoor closed, authenticated download isolation, rate limiting, secret fail-fast, token lifetime, admin self-protection, unrelated-course denial, attempt isolation) - 84 backend tests pass total. Frontend production build passes.

## Step 10 (2026-10-01) - Final testing and verification (no new features)
- Backend: 84/84 tests pass (unit, API, permissions, grading, mastery, recommendations, seed, security).
- Frontend: production build passes. Link audit: all 18 internal link patterns resolve to real routes.
- Browser QA (headless Chromium, local dev servers, demo data): all role routes render without console errors; teacher journey (course -> topic -> lesson -> question bank -> published assessment) works; student journey (class -> lesson -> one-question-per-view take -> review -> submit -> result) works; teacher grading queue grades short answers and finalizes attempts; admin user create/deactivate works.
- Bug found and fixed: the submit-assessment confirmation dialog showed "Delete" instead of "Submit" (ConfirmDialog default label). useConfirm().ask now takes an optional label; take page passes "Submit". Verified live.
- Non-issues confirmed: /teacher/questions and /teacher/grading 404s are not real routes (bank and grading live under /teacher/bank/[topicId] and /teacher/assessments/[id]/grading; nothing links to the 404 URLs); role-denied pages show denial messages or redirect with no data leak (backend 403s verified).
- Docs: docs/INSTALLATION-AND-OPERATIONS.md (install, env setup, demo accounts, structure, workflow); .env.example corrected.
- Screenshots: palms-step10-login, admin-users, teacher-courses, student-class, assessment-take, assessment-result in design/.
