PALMS design document. Prepared 2026-10-01 in the Design phase, under the approved plan and the eight approved changes. This document defines the design system, page structure, component hierarchy, and page layouts. Wireframes sit alongside it in wireframes.html. The ER diagram is er-diagram.svg. No code is written at this stage.

Note on language: the project brief bans a specific word from all project material. This document avoids it throughout.

## Design principles

The interface must read as the work of a university software team:

- Content first. The learning material and the student's progress are the interface. Nothing decorative competes with them.
- Tables for data, documents for reading, forms for input. Each context gets the layout that fits its job.
- One restrained palette, used sparingly. Color marks meaning (mastery status, roles), never decoration.
- No gradients, no glass effects, no neon, no decorative blobs, no emojis, no fake statistics, no generic dashboard look. Not every item is a card; rows and tables do most of the work.
- No gamification. No points, streaks, badges, or achievement systems. Progress is shown through mastery bands, scores, and tables. Those patterns mark generated apps; this is a study tool.
- Typography carries the academic tone: a clean sans for the interface, a serif reserved for lesson reading.
- No invented institution. The header carries "PALMS" and the plain expansion "Personalized Adaptive Learning Management System". No fake university name.
- The application resembles a university internal system: quiet chrome, compact panels, neutral controls. Nothing reads as marketing or a startup product page.

## Design system

### Color

- Paper: #ffffff (panels, content surfaces)
- Page: #f5f5f3 (application background; gives panels a light separation)
- Wash: #f6f6f4 (subtle section background, table header row)
- Hover: #f2f2ef (button and row hover)
- Ink: #2b2b2b (primary text, headings, brand, active navigation)
- Muted: #6b6b66 (secondary text, captions)
- Line: #d6d6d1 (borders, table rules)

Accent colors appear only in status indicators, mastery states, and
warnings/errors:
- Success: #2e6b34, wash #e9f1ea (mastered, proficient, active)
- Warning: #96690f, wash #f7f0dc (developing)
- Alert: #a33327, wash #f9e9e6 (needs support, flags, errors)

No accent color is used for navigation, buttons, links, or branding.
Importance is communicated through hierarchy and position, not color blocks.
- Success: #2e6b34 (mastered, proficient accents)
- Warning: #96690f (developing)
- Alert: #a33327 (needs support, flags)
- Focus ring: #1f3a5f at 2px offset for keyboard navigation

### Typography

- Interface text, headings, labels, table data, forms: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif. (In production this maps to Inter or Source Sans; system stack in v1 keeps the build dependency-free.)
- Lesson reading only: Georgia, "Times New Roman", serif, for the lesson title, objectives, body text, and student answer text. Serif stays inside the reading context; it never styles application headings, navigation, tables, or buttons.
- Code and scores in tables: ui-monospace, "SF Mono", Menlo, Consolas, monospace.
- Scale: page title 28px serif, section heading 20px serif, subsection 16px serif semibold, body 15px/1.6 sans (16px/1.7 serif for lesson reading), small labels 13px, captions 12px muted.
- Status badges: 12px uppercase, letter-spacing 0.06em.

### Spacing and shape

- Base unit 8px. Page gutter 24px, section gap 32px.
- Border radius: 4px for buttons and inputs, 6px max for panels. Nothing pill-shaped except badges.
- Shadows: one restrained level only, 0 1px 2px rgba(0,0,0,0.06), used on the header bar and dropdowns. Content panels use borders, not shadows.
- Tables: 1px bottom rules, wash header row, 12px cell padding, left-aligned text, right-aligned numbers.

### Components

- Site header: white bar, 1px bottom border. Left: "PALMS" wordmark in bold sans plus the line "Personalized Adaptive Learning Management System". No invented university name. Center or left: role navigation. Right: user name, role badge, sign out.
- Role navigation: plain text links with a 2px primary underline for the active page. No icon-heavy nav.
- Buttons: no filled color blocks anywhere. Primary action: white background, 1px solid #d6d6d1 border, #2b2b2b text, #f2f2ef hover. Secondary action: transparent background, 1px border, dark text. Danger actions: text or bordered treatment only, never a filled red button, each with a confirm step. Height 36px, radius 4px, weight 500. All future application actions use this same restrained system.
- Links: #2b2b2b text with underline. Navigation: #2b2b2b text; the active page is marked with semibold weight and a 2px ink underline. No colored navigation.
- Status badge: small uppercase label with a tinted background (success/warning/alert wash) and matching text color. Used for mastery bands, attempt status, flag state.
- Mastery bar: thin 6px track in wash, solid fill in the band color, with the numeric score beside it. Used in tables and progress views.
- Data table: wash header, row rules, sortable column headers where useful, row click or an explicit "Open" link for detail. Pagination as "Page 1 of 6" with previous/next.
- Forms: label above the input, 13px muted help text under it where needed, full-width inputs at max 560px, errors in alert color under the field. Position numbers as small numeric inputs.
- Recommendation row: a bordered row, not a card. Left: reason_code badge. Middle: the message and its reason text. Right: the action link ("Open remedial lesson", "Continue to next topic"). Dismiss as a quiet text button.
- Question view (assessment): one question centered in a 720px column. Progress line "Question 3 of 12" with a thin progress track. Options as a plain radio list with generous hit areas. Previous and Next buttons; Submit on the last question with a confirm step listing unanswered questions.
- Lesson reading view: centered document column, 720px max. Serif title, objectives as a numbered list under an "Objectives" heading, body in serif 16px/1.7, resources as a simple file list with sizes, "Related assessment" as a bordered callout at the end.
- Empty states: one plain sentence ("No questions in the bank for this topic yet.") plus the action link. No illustrations.
- Login: small brand mark at top, then a compact bordered panel on the separated page background. Thin border, normal spacing, no hero areas, no oversized branding, no decoration.

## Page structure (Next.js App Router)

- (auth)/login
- (student)/dashboard: recommendations feed, continue-learning pointer, recent results
- (student)/classes/[id]: enrolled class home, course outline (topics in order, each with mastery status)
- (student)/lessons/[id]: lesson reading view
- (student)/assessments/[id]/take: one-question-per-view assessment
- (student)/assessments/[id]/result: score, per-question review, pending items, new recommendations
- (student)/progress: per-topic mastery table with bars and bands
- (teacher)/courses: course list, create course
- (teacher)/courses/[id]: topics and lessons management (position numbers), co-teachers
- (teacher)/classes: class list, create class, enroll students
- (teacher)/bank/[topicId]: question bank table, add/edit questions
- (teacher)/assessments: assessment list, assemble from bank, publish
- (teacher)/grading: queue of short answers awaiting review
- (teacher)/classes/[id]/matrix: students-by-topics mastery matrix
- (teacher)/flags: repeated-difficulty inbox
- (teacher)/research: pre/post test score recording per student
- (teacher)/research/evaluation: research evaluation table (student identifier, pre-test, learning period, post-test, computed change, notes)
- (teacher)/students/[id]: per-student feedback history
- (admin)/users: user table, create, role assignment, activate/deactivate
- (admin)/courses: read-only course overview

Shared components live in components/: SiteHeader, RoleNav, DataTable, Pagination, StatusBadge, MasteryBar, RecommendationRow, QuestionView, LessonDocument, ResourceList, Form fields (TextInput, TextArea, SelectInput, NumberInput), EmptyState, ConfirmDialog.

Route handlers under app/api proxy to FastAPI and manage the httpOnly auth cookie. No business logic in the frontend beyond presentation.

## Component hierarchy

- App shell: SiteHeader (wordmark, RoleNav, user block) + main content region + footer line (system name, academic year)
- Pages compose: page title block, then one of DataTable / form / document / question view
- DataTable renders rows of StatusBadge, MasteryBar, links
- Dashboard composes RecommendationRow list + continue-learning panel + recent results table
- Assessment take view composes QuestionView per question with local state, then a review/confirm step
- Teacher management pages share a two-column shell: left section nav (plain list), right content

## Page layouts by context

1. Reading lessons: document layout, centered 720px column, serif. Nothing beside the text except a slim "In this topic" lesson list above the footer on wide screens.
2. Assessments: single column, one question per view, progress track on top. Deliberately sparse to hold focus.
3. Teacher management: left section list plus right content area; tables for courses, topics, lessons, questions, users. Forms are plain and labeled.
4. Student progress: tables first (topic, attempts, latest, best, band), thin mastery bars inside the table, then the recommendation feed.
5. Reports: filter row (class, topic), table, "Export CSV" button. No charts in v1; the matrix and tables carry the information.

## Refined user flows

Student:

1. Sign in, land on the dashboard. Active recommendations appear as rows, each showing its reason. A "continue learning" panel points at the current topic.
2. Open the class, then the course outline. Topics list in order with mastery bands. Open a lesson: objectives, text, resources, downloads, related assessment link.
3. Take the assessment one question at a time. Submit once, with a confirm step that lists unanswered questions.
4. Result page: auto-graded score at once, per-question review, short answers marked awaiting teacher review, fresh recommendations with reasons.
5. Progress page: the full per-topic table.

Teacher:

1. Sign in. Courses: create, add topics with order and threshold, add lessons with structured fields, mark the enrichment lesson, add co-teachers.
2. Classes: create a class for an academic year, link the course, enroll students.
3. Question bank per topic: add and edit the three question types.
4. Assessments: assemble from the bank, write instructions, publish.
5. Grading queue: score short answers with points and comments.
6. Class matrix, flags inbox, per-student feedback history, research score recording.

Admin:

1. Sign in. Users table: create accounts, assign roles, activate or deactivate. Course overview list.

## Wireframes

wireframes.html holds nine annotated screens built with this design system: login, student dashboard, lesson reading, assessment taking (one question per view), teacher course management, teacher grading queue, student progress, admin users, and research evaluation. Each screen is labeled with the layout rules it follows. Review these before any build.

## ER diagram

er-diagram.svg shows all 17 tables and their relationships: users, classes, enrollments, courses, course_teachers, topics, lessons, resources, questions, assessments, assessment_questions, attempts, answers, mastery, recommendations, flags, research_sessions.
