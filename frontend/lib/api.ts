export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Typed helper for calls that go through the /api/proxy route, which
// attaches the httpOnly auth cookie as a Bearer token server-side.
export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/proxy${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers || {}) },
  });
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
    } catch {
      /* keep raw text */
    }
    throw new ApiError(res.status, detail);
  }
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

export type UserRole = "admin" | "teacher" | "student";

export type User = {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  created_at: string;
};

export type Me = {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
};

// Sends multipart form data through the proxy (used for resource uploads).
export async function apiForm<T>(path: string, form: FormData): Promise<T> {
  const res = await fetch(`/api/proxy${path}`, { method: "POST", body: form });
  const text = await res.text();
  if (!res.ok) {
    let detail = text;
    try {
      detail = JSON.parse(text).detail || text;
    } catch {
      /* keep raw text */
    }
    throw new ApiError(res.status, detail);
  }
  return text ? (JSON.parse(text) as T) : (undefined as T);
}

export async function getMe(): Promise<Me> {
  return api<Me>("/auth/me");
}

export type DirectoryEntry = {
  id: number;
  full_name: string;
  email: string;
  role: UserRole;
};

export async function getDirectory(role: "teacher" | "student") {
  return api<DirectoryEntry[]>(`/users/directory?role=${role}`);
}

export type Course = {
  id: number;
  title: string;
  description: string | null;
  created_at: string;
  topic_count: number;
  class_count: number;
};

export type CourseTeacherInfo = {
  id: number;
  full_name: string;
  email: string;
};

export type CourseDetail = Course & { teachers: CourseTeacherInfo[] };

export async function getCourses() {
  return api<Course[]>("/courses");
}

export async function getCourse(id: number) {
  return api<CourseDetail>(`/courses/${id}`);
}

export async function createCourse(title: string, description?: string) {
  return api<CourseDetail>("/courses", {
    method: "POST",
    body: JSON.stringify({ title, description: description || null }),
  });
}

export async function updateCourse(
  id: number,
  data: { title?: string; description?: string | null }
) {
  return api<CourseDetail>(`/courses/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteCourse(id: number) {
  await api<undefined>(`/courses/${id}`, { method: "DELETE" });
}

export async function addCourseTeacher(courseId: number, teacher_id: number) {
  return api<CourseTeacherInfo>(`/courses/${courseId}/teachers`, {
    method: "POST",
    body: JSON.stringify({ teacher_id }),
  });
}

export async function removeCourseTeacher(courseId: number, teacherId: number) {
  await api<undefined>(`/courses/${courseId}/teachers/${teacherId}`, {
    method: "DELETE",
  });
}

export type LessonSummary = {
  id: number;
  topic_id: number;
  title: string;
  objectives: string | null;
  body: string | null;
  position: number;
  is_enrichment: boolean;
  created_at: string;
};

export type Topic = {
  id: number;
  course_id: number;
  title: string;
  position: number;
  mastery_threshold: number;
  description: string | null;
  lessons: LessonSummary[];
};

export async function getTopics(courseId: number) {
  return api<Topic[]>(`/courses/${courseId}/topics`);
}

export async function createTopic(
  courseId: number,
  data: { title: string; position?: number; mastery_threshold?: number; description?: string }
) {
  return api<Topic>(`/courses/${courseId}/topics`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateTopic(
  id: number,
  data: { title?: string; position?: number; mastery_threshold?: number; description?: string | null }
) {
  return api<Topic>(`/topics/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteTopic(id: number) {
  await api<undefined>(`/topics/${id}`, { method: "DELETE" });
}

export async function createLesson(
  topicId: number,
  data: {
    title: string;
    objectives?: string;
    body?: string;
    position?: number;
    is_enrichment?: boolean;
  }
) {
  return api<LessonSummary>(`/topics/${topicId}/lessons`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateLesson(
  id: number,
  data: {
    title?: string;
    objectives?: string | null;
    body?: string | null;
    position?: number;
    is_enrichment?: boolean;
  }
) {
  return api<LessonSummary>(`/lessons/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteLesson(id: number) {
  await api<undefined>(`/lessons/${id}`, { method: "DELETE" });
}

export type ResourceItem = {
  id: number;
  lesson_id: number;
  file_name: string;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
};

export type LessonDetail = LessonSummary & {
  resources: ResourceItem[];
  topic_title: string;
  course_id: number;
  course_title: string;
};

export async function getLesson(id: number) {
  return api<LessonDetail>(`/lessons/${id}`);
}

export async function uploadResource(lessonId: number, file: File) {
  const form = new FormData();
  form.append("file", file);
  return apiForm<ResourceItem>(`/lessons/${lessonId}/resources`, form);
}

export async function deleteResource(id: number) {
  await api<undefined>(`/resources/${id}`, { method: "DELETE" });
}

export async function getClassList() {
  return api<ClassItem[]>("/classes");
}

export type ClassItem = {
  id: number;
  name: string;
  academic_year: string;
  course_id: number | null;
  course_title: string | null;
  teacher_id: number;
  teacher_name: string | null;
  created_at: string;
  student_count: number;
};

export type Enrollment = {
  id: number;
  student_id: number;
  student_name: string;
  student_email: string;
  enrolled_at: string;
};

export type ClassDetail = ClassItem & { enrollments: Enrollment[] };

export async function getClass(id: number) {
  return api<ClassDetail>(`/classes/${id}`);
}

export async function createClass(data: {
  name: string;
  academic_year: string;
  course_id?: number | null;
  teacher_id?: number | null;
}) {
  return api<ClassDetail>("/classes", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateClass(
  id: number,
  data: { name?: string; academic_year?: string; course_id?: number | null; teacher_id?: number | null }
) {
  return api<ClassDetail>(`/classes/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteClass(id: number) {
  await api<undefined>(`/classes/${id}`, { method: "DELETE" });
}

export async function addEnrollment(classId: number, student_id: number) {
  return api<Enrollment>(`/classes/${classId}/enrollments`, {
    method: "POST",
    body: JSON.stringify({ student_id }),
  });
}

export async function removeEnrollment(classId: number, enrollmentId: number) {
  await api<undefined>(`/classes/${classId}/enrollments/${enrollmentId}`, {
    method: "DELETE",
  });
}

// --- Question bank and assessments ---

export type QuestionType = "mcq" | "true_false" | "short_answer";

export type Question = {
  id: number;
  topic_id: number;
  qtype: QuestionType;
  prompt: string;
  options: string[] | null;
  correct_option: number | null;
  model_answer: string | null;
  points: number;
  created_at: string;
};

export type QuestionPublic = {
  id: number;
  qtype: QuestionType;
  prompt: string;
  options: string[] | null;
  points: number;
  position: number;
};

export type AssessmentItem = {
  question_id: number;
  position: number;
  question: Question | null;
};

export type Assessment = {
  id: number;
  topic_id: number;
  title: string;
  instructions: string | null;
  is_published: boolean;
  created_at: string;
  question_count: number;
  topic_title: string;
};

export type AssessmentDetail = Assessment & { questions: AssessmentItem[] };

export type Answer = {
  id: number;
  question_id: number;
  student_text: string | null;
  selected_option: number | null;
  is_correct: boolean | null;
  points_earned: number | null;
  teacher_comment?: string | null;
  graded_at?: string | null;
};

export type AttemptStatus = "in_progress" | "submitted" | "graded";

export type Attempt = {
  id: number;
  assessment_id: number;
  student_id: number;
  status: AttemptStatus;
  started_at: string;
  submitted_at: string | null;
  total_score: number | null;
  max_score: number | null;
};

export type AttemptDetail = Attempt & {
  questions: QuestionPublic[];
  answers: Answer[];
  assessment_title: string;
  student_name: string;
};

export async function getQuestions(topicId: number) {
  return api<Question[]>(`/topics/${topicId}/questions`);
}

export async function createQuestion(
  topicId: number,
  data: {
    qtype: QuestionType;
    prompt: string;
    options?: string[] | null;
    correct_option?: number | null;
    model_answer?: string | null;
    points: number;
  }
) {
  return api<Question>(`/topics/${topicId}/questions`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateQuestion(
  id: number,
  data: {
    prompt?: string;
    options?: string[] | null;
    correct_option?: number | null;
    model_answer?: string | null;
    points?: number;
  }
) {
  return api<Question>(`/questions/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteQuestion(id: number) {
  await api<undefined>(`/questions/${id}`, { method: "DELETE" });
}

export async function getAssessments(topicId: number) {
  return api<Assessment[]>(`/topics/${topicId}/assessments`);
}

export async function createAssessment(
  topicId: number,
  data: { title: string; instructions?: string }
) {
  return api<Assessment>(`/topics/${topicId}/assessments`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getAssessment(id: number) {
  return api<AssessmentDetail>(`/assessments/${id}`);
}

export async function updateAssessment(
  id: number,
  data: { title?: string; instructions?: string | null }
) {
  return api<Assessment>(`/assessments/${id}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function deleteAssessment(id: number) {
  await api<undefined>(`/assessments/${id}`, { method: "DELETE" });
}

export async function addAssessmentQuestion(
  assessmentId: number,
  data: { question_id: number; position?: number }
) {
  return api<AssessmentItem>(`/assessments/${assessmentId}/questions`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function moveAssessmentQuestion(
  assessmentId: number,
  questionId: number,
  position: number
) {
  return api<AssessmentItem>(
    `/assessments/${assessmentId}/questions/${questionId}`,
    { method: "PATCH", body: JSON.stringify({ position }) }
  );
}

export async function removeAssessmentQuestion(
  assessmentId: number,
  questionId: number
) {
  await api<undefined>(`/assessments/${assessmentId}/questions/${questionId}`, {
    method: "DELETE",
  });
}

export async function publishAssessment(id: number, is_published: boolean) {
  return api<Assessment>(`/assessments/${id}/publish`, {
    method: "PATCH",
    body: JSON.stringify({ is_published }),
  });
}

export async function startAttempt(assessmentId: number) {
  return api<AttemptDetail>(`/assessments/${assessmentId}/attempts`, {
    method: "POST",
  });
}

export async function getMyAttempts(assessmentId: number) {
  return api<Attempt[]>(`/assessments/${assessmentId}/my-attempts`);
}

export async function getAttempt(id: number) {
  return api<AttemptDetail>(`/attempts/${id}`);
}

export async function getAssessmentAttempts(assessmentId: number) {
  return api<AttemptDetail[]>(`/assessments/${assessmentId}/attempts`);
}

export async function saveAnswer(
  attemptId: number,
  data: { question_id: number; selected_option?: number | null; student_text?: string | null }
) {
  return api<Answer>(`/attempts/${attemptId}/answers`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function submitAttempt(id: number) {
  return api<Attempt>(`/attempts/${id}/submit`, { method: "POST" });
}

export const QUESTION_TYPE_LABELS: Record<QuestionType, string> = {
  mcq: "Multiple choice",
  true_false: "True / False",
  short_answer: "Short answer",
};

export type TopicDetail = Topic & { course_title: string; lessons: LessonSummary[] };

export async function getTopic(id: number) {
  return api<TopicDetail>(`/topics/${id}`);
}

// --- Grading and mastery ---

export type AnswerGraded = Answer & {
  teacher_comment: string | null;
  graded_by: number | null;
  graded_at: string | null;
};

export type GradingQueueItem = {
  answer_id: number;
  attempt_id: number;
  student_id: number;
  student_name: string;
  question_id: number;
  question_prompt: string;
  question_points: number;
  student_text: string | null;
  points_earned: number | null;
  teacher_comment: string | null;
  submitted_at: string | null;
};

export type MasteryStatus =
  | "needs_support"
  | "developing"
  | "proficient"
  | "mastered";

export type MasteryRecord = {
  id: number;
  student_id: number;
  topic_id: number;
  attempts_count: number;
  latest_score: number | null;
  best_score: number | null;
  status: MasteryStatus | null;
  updated_at: string;
  student_name: string;
  topic_title: string;
};

export const MASTERY_STATUS_LABELS: Record<MasteryStatus, string> = {
  needs_support: "Needs support",
  developing: "Developing",
  proficient: "Proficient",
  mastered: "Mastered",
};

export async function getGradingQueue(assessmentId: number) {
  return api<GradingQueueItem[]>(`/assessments/${assessmentId}/grading-queue`);
}

export async function gradeAnswer(
  answerId: number,
  data: { points_earned: number; teacher_comment?: string | null }
) {
  return api<AnswerGraded>(`/answers/${answerId}/grade`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function getTopicMastery(topicId: number) {
  return api<MasteryRecord[]>(`/topics/${topicId}/mastery`);
}

export type RecommendationStatus = "active" | "dismissed" | "completed";

export type Recommendation = {
  id: number;
  student_id: number;
  topic_id: number;
  rule_code: string;
  title: string;
  message: string;
  reason: string;
  status: RecommendationStatus;
  teacher_note: string | null;
  created_at: string;
  updated_at: string;
  student_name: string;
  topic_title: string;
  course_title: string;
};

export const RULE_PRIORITY_ORDER = [
  "REPEATED_DIFFICULTY",
  "LOW_PERFORMANCE",
  "DEVELOPING",
  "MASTERY_ACHIEVED",
  "HIGH_ACHIEVEMENT",
];

export const RULE_LABELS: Record<string, string> = {
  REPEATED_DIFFICULTY: "Repeated difficulty",
  LOW_PERFORMANCE: "Low performance",
  DEVELOPING: "Developing",
  MASTERY_ACHIEVED: "Mastery achieved",
  HIGH_ACHIEVEMENT: "High achievement",
};

export const RECOMMENDATION_STATUS_LABELS: Record<RecommendationStatus, string> = {
  active: "Active",
  dismissed: "Dismissed",
  completed: "Completed",
};

export type PathLesson = {
  id: number;
  title: string;
  position: number;
  completed: boolean;
};

export type PathTopic = {
  id: number;
  title: string;
  position: number;
  mastery_status: MasteryStatus | null;
  latest_score: number | null;
  lessons: PathLesson[];
};

export type LearningPath = {
  class_id: number;
  class_name: string;
  course_id: number;
  course_title: string;
  topics: PathTopic[];
  current_activity: Recommendation | null;
  next_topic_id: number | null;
};

export async function listRecommendations(courseId?: number) {
  const q = courseId ? `?course_id=${courseId}` : "";
  return api<Recommendation[]>(`/recommendations${q}`);
}

export async function dismissRecommendation(id: number) {
  return api<Recommendation>(`/recommendations/${id}/dismiss`, { method: "POST" });
}

export async function reviewRecommendation(id: number, teacher_note: string) {
  return api<Recommendation>(`/recommendations/${id}/review`, {
    method: "POST",
    body: JSON.stringify({ teacher_note }),
  });
}

export async function completeLesson(lessonId: number) {
  return api<{ lesson_id: number; completed: boolean }>(
    `/lessons/${lessonId}/complete`,
    { method: "POST" }
  );
}

export async function getLearningPath(classId: number) {
  return api<LearningPath>(`/classes/${classId}/learning-path`);
}

// --- Step 7: feedback, reports, research evaluation ---

export type ResearchSession = {
  id: number;
  student_id: number;
  student_name: string;
  class_id: number;
  class_name: string;
  course_id: number;
  course_title: string;
  pre_test_score: number | null;
  post_test_score: number | null;
  learning_period: string | null;
  score_change: number | null;
  notes: string | null;
  created_at: string;
};

export type ClassProgressRow = {
  student_id: number;
  student_name: string;
  topic_id: number;
  topic_title: string;
  attempts_count: number;
  latest_score: number | null;
  best_score: number | null;
  mastery_status: string | null;
};

export type StudentProgressRow = {
  topic_id: number;
  topic_title: string;
  lessons_completed: number;
  lessons_total: number;
  assessment_attempts: number;
  latest_score: number | null;
  mastery_status: string | null;
};

export type FeedbackHistoryRow = {
  date: string | null;
  course_title: string;
  topic_title: string;
  assessment_title: string;
  score: string;
  teacher_comment: string | null;
  intervention: string | null;
};

export type StudentFeedbackRow = {
  date: string | null;
  topic_title: string;
  assessment_title: string;
  score: string;
  teacher_comment: string | null;
  suggestion: string | null;
};

export async function getClassProgress(classId: number) {
  return api<ClassProgressRow[]>(`/classes/${classId}/reports/class-progress`);
}

export async function getStudentProgress(classId: number, studentId: number) {
  return api<StudentProgressRow[]>(
    `/classes/${classId}/reports/student-progress?student_id=${studentId}`
  );
}

export async function getFeedbackHistory(classId: number, studentId: number) {
  return api<FeedbackHistoryRow[]>(
    `/classes/${classId}/feedback-history?student_id=${studentId}`
  );
}

export async function getMyFeedback() {
  return api<StudentFeedbackRow[]>("/feedback/my");
}

export async function listResearchSessions(classId: number) {
  return api<ResearchSession[]>(`/classes/${classId}/research-sessions`);
}

export async function createResearchSession(
  classId: number,
  data: {
    student_id: number;
    pre_test_score?: number | null;
    post_test_score?: number | null;
    learning_period?: string | null;
    notes?: string | null;
  }
) {
  return api<ResearchSession>(`/classes/${classId}/research-sessions`, {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function updateResearchSession(
  sessionId: number,
  data: {
    pre_test_score?: number | null;
    post_test_score?: number | null;
    learning_period?: string | null;
    notes?: string | null;
  }
) {
  return api<ResearchSession>(`/research-sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify(data),
  });
}

export async function downloadCsv(path: string, filename: string) {
  const res = await fetch(`/api/proxy${path}`);
  if (!res.ok) throw new ApiError(res.status, "Could not download the file.");
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
