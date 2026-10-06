"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DataTable from "@/components/DataTable";
import { useConfirm } from "@/components/ConfirmDialog";
import {
  CheckboxInput,
  Field,
  FormError,
  NumberInput,
  SelectInput,
  TextArea,
  TextInput,
} from "@/components/forms";
import { ResourceList } from "@/components/LessonDocument";
import {
  ApiError,
  addCourseTeacher,
  createLesson,
  createTopic,
  deleteCourse,
  deleteLesson,
  deleteResource,
  deleteTopic,
  getClassList,
  getCourse,
  getDirectory,
  getTopics,
  removeCourseTeacher,
  updateCourse,
  updateLesson,
  updateTopic,
  uploadResource,
  type ClassItem,
  type CourseDetail,
  type DirectoryEntry,
  type LessonSummary,
  type ResourceItem,
  type Topic,
} from "@/lib/api";

function PositionCell({
  value,
  onSave,
}: {
  value: number;
  onSave: (v: number) => Promise<void>;
}) {
  const [draft, setDraft] = useState(String(value));
  useEffect(() => setDraft(String(value)), [value]);
  return (
    <input
      type="number"
      min={1}
      value={draft}
      onChange={(e) => setDraft(e.target.value)}
      onBlur={() => {
        const v = parseInt(draft, 10);
        if (!Number.isNaN(v) && v !== value) onSave(v).catch(() => setDraft(String(value)));
        else setDraft(String(value));
      }}
      className="field-input w-20"
      aria-label="Position"
    />
  );
}

function LessonEditor({
  lesson,
  onChanged,
  onDeleted,
}: {
  lesson: LessonSummary;
  onChanged: () => void;
  onDeleted: () => void;
}) {
  const { ask, dialog } = useConfirm();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState(lesson.title);
  const [objectives, setObjectives] = useState(lesson.objectives || "");
  const [body, setBody] = useState(lesson.body || "");
  const [enrichment, setEnrichment] = useState(lesson.is_enrichment);
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);

  async function loadResources() {
    const { getLesson } = await import("@/lib/api");
    const detail = await getLesson(lesson.id);
    setResources(detail.resources);
  }

  useEffect(() => {
    if (open) {
      setTitle(lesson.title);
      setObjectives(lesson.objectives || "");
      setBody(lesson.body || "");
      setEnrichment(lesson.is_enrichment);
      loadResources().catch(() => {});
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await updateLesson(lesson.id, {
        title: title.trim(),
        objectives: objectives.trim() || null,
        body: body.trim() || null,
        is_enrichment: enrichment,
      });
      onChanged();
      setOpen(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save the lesson.");
    } finally {
      setSaving(false);
    }
  }

  async function onUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setUploading(true);
    try {
      await uploadResource(lesson.id, file);
      await loadResources();
      onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Upload failed.");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  }

  return (
    <div className="border-t border-line">
      <div className="flex items-center justify-between py-2">
        <div className="flex items-center gap-3">
          <PositionCell
            value={lesson.position}
            onSave={async (v) => {
              await updateLesson(lesson.id, { position: v });
              onChanged();
            }}
          />
          <span className="font-medium">{lesson.title}</span>
          {lesson.is_enrichment && (
            <span className="badge bg-wash text-muted">Enrichment</span>
          )}
        </div>
        <div className="flex gap-4 text-sm">
          <button className="text-ink underline" onClick={() => setOpen((v) => !v)}>
            {open ? "Close" : "Edit"}
          </button>
          <button
            className="text-alert underline"
            onClick={() =>
              ask("Delete lesson", `Delete "${lesson.title}" and its resources?`, onDeleted)
            }
          >
            Delete
          </button>
        </div>
      </div>
      {open && (
        <div className="mb-4 rounded border border-line bg-wash p-5">
          <FormError message={error} />
          <form onSubmit={onSave}>
            <Field label="Title" htmlFor={`lt-${lesson.id}`}>
              <TextInput
                id={`lt-${lesson.id}`}
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
              />
            </Field>
            <Field label="Learning objectives" htmlFor={`lo-${lesson.id}`}>
              <TextArea
                id={`lo-${lesson.id}`}
                value={objectives}
                onChange={(e) => setObjectives(e.target.value)}
              />
            </Field>
            <Field label="Body text" htmlFor={`lb-${lesson.id}`}>
              <TextArea
                id={`lb-${lesson.id}`}
                value={body}
                onChange={(e) => setBody(e.target.value)}
                className="min-h-[160px]"
              />
            </Field>
            <div className="mb-4">
              <CheckboxInput
                label="Enrichment lesson (for high-achieving students)"
                checked={enrichment}
                onChange={(e) => setEnrichment(e.target.checked)}
              />
            </div>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Save lesson"}
            </button>
          </form>
          <div className="mt-6">
            <h4 className="mb-3 text-sm font-semibold">Resources</h4>
            <ResourceList resources={resources} />
            <div className="mt-3 flex items-center gap-3">
              <label className="btn-secondary cursor-pointer">
                {uploading ? "Uploading..." : "Upload file"}
                <input
                  type="file"
                  className="hidden"
                  onChange={onUpload}
                  disabled={uploading}
                />
              </label>
              <span className="text-xs text-muted">
                PDF, images, Office documents, text. Max 10 MB.
              </span>
            </div>
            {resources.length > 0 && (
              <ul className="mt-3 space-y-1">
                {resources.map((r) => (
                  <li key={r.id} className="flex items-center justify-between text-sm">
                    <span>{r.file_name}</span>
                    <button
                      className="text-alert underline"
                      onClick={() =>
                        ask("Delete resource", `Delete "${r.file_name}"?`, async () => {
                          await deleteResource(r.id);
                          await loadResources();
                          onChanged();
                        })
                      }
                    >
                      Delete
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      )}
      {dialog}
    </div>
  );
}

function TopicSection({
  topic,
  onChanged,
}: {
  topic: Topic;
  onChanged: () => void;
}) {
  const { ask, dialog } = useConfirm();
  const [showLessonForm, setShowLessonForm] = useState(false);
  const [ltitle, setLtitle] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function onAddLesson(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createLesson(topic.id, { title: ltitle.trim() });
      setLtitle("");
      setShowLessonForm(false);
      onChanged();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add the lesson.");
    }
  }

  return (
    <section className="mb-8 rounded border border-line bg-paper">
      <div className="flex items-center justify-between border-b border-line px-5 py-3">
        <div className="flex items-center gap-3">
          <PositionCell
            value={topic.position}
            onSave={async (v) => {
              await updateTopic(topic.id, { position: v });
              onChanged();
            }}
          />
          <h2 className="text-base font-semibold">{topic.title}</h2>
          <span className="text-xs text-muted">
            Threshold {topic.mastery_threshold}%
          </span>
        </div>
        <div className="flex gap-4 text-sm">
          <Link href={`/teacher/bank/${topic.id}`}>Question bank</Link>
          <Link href={`/teacher/topics/${topic.id}/assessments`}>
            Assessments
          </Link>
          <button
            className="text-ink underline"
            onClick={() => setShowLessonForm((v) => !v)}
          >
            Add lesson
          </button>
          <button
            className="text-alert underline"
            onClick={() =>
              ask(
                "Delete topic",
                `Delete "${topic.title}" with all its lessons and resources?`,
                async () => {
                  await deleteTopic(topic.id);
                  onChanged();
                }
              )
            }
          >
            Delete
          </button>
        </div>
      </div>
      <div className="px-5 py-2">
        <FormError message={error} />
        {showLessonForm && (
          <form onSubmit={onAddLesson} className="mb-3 flex items-end gap-2 py-2">
            <div className="flex-1">
              <Field label="Lesson title" htmlFor={`nl-${topic.id}`}>
                <TextInput
                  id={`nl-${topic.id}`}
                  value={ltitle}
                  onChange={(e) => setLtitle(e.target.value)}
                  required
                />
              </Field>
            </div>
            <button type="submit" className="btn-primary mb-4">
              Add
            </button>
          </form>
        )}
        {topic.lessons.length === 0 && !showLessonForm && (
          <p className="py-4 text-sm text-muted">No lessons yet.</p>
        )}
        {topic.lessons.map((lesson) => (
          <LessonEditor
            key={lesson.id}
            lesson={lesson}
            onChanged={onChanged}
            onDeleted={async () => {
              await deleteLesson(lesson.id);
              onChanged();
            }}
          />
        ))}
      </div>
      {dialog}
    </section>
  );
}

export default function CourseManagePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const courseId = parseInt(id, 10);
  const router = useRouter();
  const { ask, dialog } = useConfirm();
  const [course, setCourse] = useState<CourseDetail | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [teachers, setTeachers] = useState<DirectoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [etitle, setEtitle] = useState("");
  const [edesc, setEdesc] = useState("");
  const [showTopicForm, setShowTopicForm] = useState(false);
  const [ttitle, setTtitle] = useState("");
  const [tthreshold, setTthreshold] = useState("70");
  const [addTeacherId, setAddTeacherId] = useState("");

  async function load() {
    try {
      const [c, t, cls, dir] = await Promise.all([
        getCourse(courseId),
        getTopics(courseId),
        getClassList(),
        getDirectory("teacher"),
      ]);
      setCourse(c);
      setTopics(t);
      setClasses(cls.filter((k) => k.course_id === courseId));
      setTeachers(dir.filter((d) => !c.teachers.some((x) => x.id === d.id)));
      setEtitle(c.title);
      setEdesc(c.description || "");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the course.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [courseId]);

  async function onSaveCourse(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await updateCourse(courseId, {
        title: etitle.trim(),
        description: edesc.trim() || null,
      });
      setEditing(false);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save the course.");
    }
  }

  async function onAddTopic(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createTopic(courseId, {
        title: ttitle.trim(),
        mastery_threshold: parseInt(tthreshold, 10) || 70,
      });
      setTtitle("");
      setTthreshold("70");
      setShowTopicForm(false);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add the topic.");
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading...</p>;
  if (!course) return <FormError message={error || "Course not found."} />;

  return (
    <div>
      <div className="mb-6">
        <a href="/teacher/courses" className="text-sm no-underline">
          ← Courses
        </a>
        <div className="mt-2 flex items-start justify-between">
          <div>
            <h1 className="text-xl font-semibold">{course.title}</h1>
            {course.description && (
              <p className="mt-1 max-w-2xl text-sm text-muted">{course.description}</p>
            )}
          </div>
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => setEditing((v) => !v)}>
              Edit
            </button>
            <button
              className="btn-secondary"
              onClick={() =>
                ask(
                  "Delete course",
                  `Delete "${course.title}" with all topics and lessons?`,
                  async () => {
                    try {
                      await deleteCourse(courseId);
                      router.push("/teacher/courses");
                    } catch (e) {
                      setError(
                        e instanceof ApiError ? e.message : "Could not delete the course."
                      );
                    }
                  }
                )
              }
            >
              Delete
            </button>
          </div>
        </div>
      </div>

      <FormError message={error} />

      {editing && (
        <form onSubmit={onSaveCourse} className="mb-6 rounded border border-line p-5">
          <Field label="Title" htmlFor="ec-title">
            <TextInput
              id="ec-title"
              value={etitle}
              onChange={(e) => setEtitle(e.target.value)}
              required
            />
          </Field>
          <Field label="Description" htmlFor="ec-desc">
            <TextArea id="ec-desc" value={edesc} onChange={(e) => setEdesc(e.target.value)} />
          </Field>
          <button type="submit" className="btn-primary">
            Save changes
          </button>
        </form>
      )}

      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-base font-semibold">Topics and lessons</h2>
        <button className="btn-primary" onClick={() => setShowTopicForm((v) => !v)}>
          Add topic
        </button>
      </div>

      {showTopicForm && (
        <form onSubmit={onAddTopic} className="mb-6 rounded border border-line p-5">
          <div className="grid gap-4 md:grid-cols-[1fr_140px]">
            <Field label="Topic title" htmlFor="nt-title">
              <TextInput
                id="nt-title"
                value={ttitle}
                onChange={(e) => setTtitle(e.target.value)}
                required
              />
            </Field>
            <Field label="Mastery threshold %" htmlFor="nt-threshold">
              <NumberInput
                id="nt-threshold"
                value={tthreshold}
                min={1}
                max={100}
                onChange={(e) => setTthreshold(e.target.value)}
              />
            </Field>
          </div>
          <button type="submit" className="btn-primary">
            Add topic
          </button>
        </form>
      )}

      {topics.length === 0 && !showTopicForm && (
        <p className="mb-6 text-sm text-muted">No topics yet.</p>
      )}
      {topics.map((t) => (
        <TopicSection key={t.id} topic={t} onChanged={load} />
      ))}

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold">Co-teachers</h2>
        <DataTable
          columns={[
            { key: "name", header: "Name", render: (t) => t.full_name },
            { key: "email", header: "Email", render: (t) => t.email },
            {
              key: "actions",
              header: "",
              render: (t) => (
                <button
                  className="text-alert underline"
                  onClick={() =>
                    ask("Remove co-teacher", `Remove ${t.full_name} from this course?`, async () => {
                      try {
                        await removeCourseTeacher(courseId, t.id);
                        await load();
                      } catch (e) {
                        setError(e instanceof ApiError ? e.message : "Could not remove the teacher.");
                      }
                    })
                  }
                >
                  Remove
                </button>
              ),
            },
          ]}
          rows={course.teachers}
          emptyMessage="No teachers assigned."
        />
        {teachers.length > 0 && (
          <form
            className="mt-3 flex items-end gap-2"
            onSubmit={async (e) => {
              e.preventDefault();
              if (!addTeacherId) return;
              try {
                await addCourseTeacher(courseId, parseInt(addTeacherId, 10));
                setAddTeacherId("");
                await load();
              } catch (err) {
                setError(err instanceof ApiError ? err.message : "Could not add the teacher.");
              }
            }}
          >
            <div className="w-72">
              <Field label="Add co-teacher" htmlFor="add-teacher">
                <SelectInput
                  id="add-teacher"
                  value={addTeacherId}
                  onChange={(e) => setAddTeacherId(e.target.value)}
                >
                  <option value="">Select a teacher...</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name} ({t.email})
                    </option>
                  ))}
                </SelectInput>
              </Field>
            </div>
            <button type="submit" className="btn-secondary mb-4">
              Add
            </button>
          </form>
        )}
      </section>

      <section>
        <h2 className="mb-3 text-base font-semibold">Classes using this course</h2>
        <DataTable
          columns={[
            {
              key: "name",
              header: "Class",
              render: (c) => (
                <a href={`/teacher/classes/${c.id}`} className="font-medium">
                  {c.name}
                </a>
              ),
            },
            { key: "year", header: "Year", render: (c) => c.academic_year },
            { key: "students", header: "Students", render: (c) => String(c.student_count) },
          ]}
          rows={classes}
          emptyMessage="No classes use this course yet."
        />
      </section>
      {dialog}
    </div>
  );
}
