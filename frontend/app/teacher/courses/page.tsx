"use client";

import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { Field, FormError, TextArea, TextInput } from "@/components/forms";
import {
  ApiError,
  createCourse,
  getCourses,
  type Course,
} from "@/lib/api";

export default function TeacherCoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      setCourses(await getCourses());
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load courses.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      const created = await createCourse(title.trim(), description.trim());
      setCourses((cs) => [...cs, created].sort((a, b) => a.title.localeCompare(b.title)));
      setTitle("");
      setDescription("");
      setShowNew(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create the course.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">Courses</h1>
          <p className="mt-1 text-sm text-muted">
            Courses you teach. Open a course to manage its topics and lessons.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowNew((v) => !v)}>
          New course
        </button>
      </div>

      <FormError message={error} />

      {showNew && (
        <form
          onSubmit={onCreate}
          className="mb-6 rounded border border-line bg-paper p-5"
        >
          <h2 className="mb-4 text-base font-semibold">New course</h2>
          <Field label="Title" htmlFor="course-title">
            <TextInput
              id="course-title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              maxLength={200}
            />
          </Field>
          <Field label="Description" htmlFor="course-description">
            <TextArea
              id="course-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </Field>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Save course"}
            </button>
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowNew(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-muted">Loading...</p>
      ) : (
        <DataTable
          columns={[
            {
              key: "title",
              header: "Title",
              render: (c) => (
                <a href={`/teacher/courses/${c.id}`} className="font-medium">
                  {c.title}
                </a>
              ),
            },
            { key: "topics", header: "Topics", render: (c) => String(c.topic_count) },
            { key: "classes", header: "Classes", render: (c) => String(c.class_count) },
            {
              key: "description",
              header: "Description",
              render: (c) => (
                <span className="text-muted">
                  {c.description ? c.description.slice(0, 80) : "-"}
                </span>
              ),
            },
          ]}
          rows={courses}
          emptyMessage="No courses yet. Create your first course above."
        />
      )}
    </div>
  );
}
