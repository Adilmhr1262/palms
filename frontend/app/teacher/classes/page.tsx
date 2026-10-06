"use client";

import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { Field, FormError, SelectInput, TextInput } from "@/components/forms";
import {
  ApiError,
  createClass,
  getClassList,
  getCourses,
  getDirectory,
  getMe,
  type ClassItem,
  type Course,
  type DirectoryEntry,
  type Me,
} from "@/lib/api";

export default function TeacherClassesPage() {
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [courses, setCourses] = useState<Course[]>([]);
  const [teachers, setTeachers] = useState<DirectoryEntry[]>([]);
  const [me, setMe] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState("");
  const [year, setYear] = useState("2026");
  const [courseId, setCourseId] = useState("");
  const [teacherId, setTeacherId] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function load() {
    try {
      const [cls, cs, u, t] = await Promise.all([
        getClassList(),
        getCourses(),
        getMe(),
        getDirectory("teacher"),
      ]);
      setClasses(cls);
      setCourses(cs);
      setMe(u);
      setTeachers(t);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load classes.");
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
      const created = await createClass({
        name: name.trim(),
        academic_year: year.trim(),
        course_id: courseId ? parseInt(courseId, 10) : null,
        teacher_id:
          me?.role === "admin" && teacherId ? parseInt(teacherId, 10) : null,
      });
      setClasses((cs) => [...cs, created]);
      setName("");
      setYear("2026");
      setCourseId("");
      setTeacherId("");
      setShowNew(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not create the class.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">Classes</h1>
          <p className="mt-1 text-sm text-muted">
            Classes link students to a course. Open a class to manage enrollments.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowNew((v) => !v)}>
          New class
        </button>
      </div>

      <FormError message={error} />

      {showNew && (
        <form onSubmit={onCreate} className="mb-6 rounded border border-line p-5">
          <h2 className="mb-4 text-base font-semibold">New class</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Class name" htmlFor="cc-name">
              <TextInput
                id="cc-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={120}
                placeholder="7-A"
              />
            </Field>
            <Field label="Academic year" htmlFor="cc-year">
              <TextInput
                id="cc-year"
                value={year}
                onChange={(e) => setYear(e.target.value)}
                required
                maxLength={20}
              />
            </Field>
            <Field label="Course (optional)" htmlFor="cc-course">
              <SelectInput
                id="cc-course"
                value={courseId}
                onChange={(e) => setCourseId(e.target.value)}
              >
                <option value="">No course linked</option>
                {courses.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </SelectInput>
            </Field>
            {me?.role === "admin" && (
              <Field label="Class teacher" htmlFor="cc-teacher">
                <SelectInput
                  id="cc-teacher"
                  value={teacherId}
                  onChange={(e) => setTeacherId(e.target.value)}
                  required
                >
                  <option value="">Select a teacher...</option>
                  {teachers.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.full_name} ({t.email})
                    </option>
                  ))}
                </SelectInput>
              </Field>
            )}
          </div>
          <div className="flex gap-2">
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving..." : "Save class"}
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
              key: "name",
              header: "Class",
              render: (c) => (
                <a href={`/teacher/classes/${c.id}`} className="font-medium">
                  {c.name}
                </a>
              ),
            },
            { key: "year", header: "Year", render: (c) => c.academic_year },
            {
              key: "course",
              header: "Course",
              render: (c) => c.course_title || <span className="text-muted">-</span>,
            },
            {
              key: "teacher",
              header: "Teacher",
              render: (c) => c.teacher_name || "-",
            },
            {
              key: "students",
              header: "Students",
              render: (c) => String(c.student_count),
            },
          ]}
          rows={classes}
          emptyMessage="No classes yet. Create your first class above."
        />
      )}
    </div>
  );
}
