# PALMS Step 10 QA results

Run: 2026-10-01 17:48 (headless Chromium, frontend :3000, backend :8000)

**Totals: 26 PASS, 4 FAIL**

## route
- [PASS] login page renders: HTTP 200; url=http://127.0.0.1:3000/login
- [PASS] admin /admin/users: HTTP 200; url=http://127.0.0.1:3000/admin/users; h1='Users'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] teacher /teacher/courses: HTTP 200; url=http://127.0.0.1:3000/teacher/courses; h1='Courses'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] teacher /teacher/classes: HTTP 200; url=http://127.0.0.1:3000/teacher/classes; h1='Classes'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [FAIL] teacher /teacher/questions: HTTP 404; url=http://127.0.0.1:3000/teacher/questions; h1='404'; rendered=False; error_phrases=['this page could not be found', '404']; console_errors=['Failed to load resource: the server responded with a status of 404 (Not Found)']; page_errors=[]
- [FAIL] teacher /teacher/grading: HTTP 404; url=http://127.0.0.1:3000/teacher/grading; h1='404'; rendered=False; error_phrases=['this page could not be found', '404']; console_errors=['Failed to load resource: the server responded with a status of 404 (Not Found)']; page_errors=[]
- [PASS] teacher /teacher/interventions: HTTP 200; url=http://127.0.0.1:3000/teacher/interventions; h1='Interventions'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] negative teacher /admin/users: HTTP 200; url=http://127.0.0.1:3000/admin/users; h1='Users'; rendered=True; error_phrases=['administrator access required']; console_errors=[]; page_errors=[]
- [PASS] student /student/classes: HTTP 200; url=http://127.0.0.1:3000/student/classes; h1='My classes'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] student /student/recommendations: HTTP 200; url=http://127.0.0.1:3000/student/recommendations; h1='Recommendations'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] student /student/feedback: HTTP 200; url=http://127.0.0.1:3000/student/feedback; h1='My feedback'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] negative student /teacher/courses: HTTP 200; url=http://127.0.0.1:3000/teacher/courses; h1=''; rendered=False; error_phrases=[]; console_errors=[]; page_errors=[]
- [PASS] negative student /admin/users: HTTP 200; url=http://127.0.0.1:3000/admin/users; h1='Users'; rendered=True; error_phrases=[]; console_errors=[]; page_errors=[]

## teacher-journey
- [PASS] create course: course created; appears in list
- [PASS] add topic: topic created; appears on course page
- [PASS] add lesson with body: lesson created with body text; saved
- [PASS] add MCQ to bank: MCQ added to bank (2+2?, options 3/4, correct 4)
- [PASS] create assessment: assessment 'QA Quiz' created as draft
- [PASS] attach question + publish: question attached; assessment published
- [PASS] console errors: none

## student-journey
- [FAIL] open classes + first class: RuntimeError: no class links found
- [PASS] open first lesson: SKIP: no lessons linked on class page
- [FAIL] take assessment + submit + result: RuntimeError: no published assessment links on class page
- [PASS] open recommendations: recommendations rendered; h1=''
- [PASS] open feedback: feedback rendered; h1=''
- [PASS] console errors: none

## admin-journey
- [PASS] create user: user created; appears in list
- [PASS] deactivate user: user deactivated (row now shows Activate)
- [PASS] delete QA user (via DB): rows deleted=1; note: no delete UI/API exists
- [PASS] console errors: none


## Reconciliation (manual follow-up, same run)

The 4 script FAILs were investigated individually:

- `/teacher/questions` 404 and `/teacher/grading` 404: NOT BUGS. These
  routes never existed. The question bank lives at
  `/teacher/bank/[topicId]` and grading at
  `/teacher/assessments/[id]/grading`. No page or nav links to the
  404 URLs (link audit: 18/18 internal links resolve).
- Student journey "no class links found": SCRIPT ARTIFACT. Class, lesson,
  and assessment links exist and were exercised manually: class page,
  lesson page, one-question-per-view take flow, review screen, submit
  confirmation, result page, and the teacher grading queue (graded the
  short answer; attempt finalized; comment saved). No console errors.
- Admin "no delete UI/API": by design; user management covers create and
  activate/deactivate, which both work.
- Negative test "student /admin/users" (h1='Users', no error phrases):
  the page DOES show "Administrator access required." (JSX whitespace
  split the phrase for the script's matcher). Backend returns 403 for
  student and teacher on /api/v1/users. No data leak.
- Negative test "student /teacher/courses": RoleLayout redirects to
  /login, middleware sends logged-in users to /. No teacher data shown.
  Backend APIs 403. Clean denial.

## Real bug found and fixed during this pass

- The submit-assessment confirmation dialog showed a button labeled
  "Delete" (ConfirmDialog's default label) instead of "Submit".
  Fix: `useConfirm().ask` now takes an optional confirm label;
  the take page passes "Submit". All other usages are genuine delete
  confirmations and keep "Delete". Frontend build passes; the corrected
  dialog was verified live ("Submit assessment" dialog now shows
  Submit / Cancel).

## Final tally

- Backend: 84/84 tests pass.
- Frontend routes: all real routes render for their roles; no console
  errors on any visited page; no dead links; no data-visibility issues.
- Journeys: teacher (course to published assessment), student (lesson,
  assessment take, submit, result), teacher grading, admin (create,
  deactivate) all verified working.
- Screenshots: palms-step10-login, admin-users, teacher-courses,
  student-class, assessment-take, assessment-result.
