"use client";

import { use, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import DataTable from "@/components/DataTable";
import { useConfirm } from "@/components/ConfirmDialog";
import { Field, FormError, SelectInput, TextInput } from "@/components/forms";
import {
  ApiError,
  addEnrollment,
  deleteClass,
  getClass,
  getCourses,
  getDirectory,
  removeEnrollment,
  updateClass,
  type ClassDetail,
  type Course,
  type DirectoryEntry,
} from "@/lib/api";

export default function ClassManagePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const classId = parseInt(id, 10);
  const router = useRouter();
  const { ask, dialog } = useConfirm();
  const [class_, setClass_] = useState<ClassDetail | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [students, setStudents] = useState<DirectoryEntry[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [ename, setEname] = useState("");
  const [eyear, setEyear] = useState("");
  const [addStudentId, setAddStudentId] = useState("");

  async function load() {
    try {
      const [c, cs, dir] = await Promise.all([
        getClass(classId),
        getCourses(),
        getDirectory("student"),
      ]);
      setClass_(c);
      setCourses(cs);
      setStudents(dir.filter((d) => !c.enrollments.some((e) => e.student_id === d.id)));
      setEname(c.name);
      setEyear(c.academic_year);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the class.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [classId]);

  async function onSave(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await updateClass(classId, { name: ename.trim(), academic_year: eyear.trim() });
      setEditing(false);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save the class.");
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading...</p>;
  if (!class_) return <FormError message={error || "Class not found."} />;

  return (
    <div>
      <a href="/teacher/classes" className="text-sm no-underline">
        ← Classes
      </a>
      <div className="mb-6 mt-2 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">
            {class_.name} <span className="font-normal text-muted">· {class_.academic_year}</span>
          </h1>
          <p className="mt-1 text-sm text-muted">
            {class_.course_title ? `Follows ${class_.course_title}` : "No course linked"} ·{" "}
            {class_.teacher_name}
          </p>
          <p className="mt-2 text-sm">
            <a href={`/teacher/classes/${classId}/reports`} className="no-underline">
              Reports
            </a>
            {" · "}
            <a href={`/teacher/classes/${classId}/feedback`} className="no-underline">
              Feedback history
            </a>
            {" · "}
            <a href={`/teacher/classes/${classId}/research`} className="no-underline">
              Research evaluation
            </a>
          </p>
        </div>
        <div className="flex gap-2">
          <button className="btn-secondary" onClick={() => setEditing((v) => !v)}>
            Edit
          </button>
          <button
            className="btn-secondary"
            onClick={() =>
              ask(
                "Delete class",
                `Delete class "${class_.name}" and all its enrollments?`,
                async () => {
                  try {
                    await deleteClass(classId);
                    router.push("/teacher/classes");
                  } catch (e) {
                    setError(e instanceof ApiError ? e.message : "Could not delete the class.");
                  }
                }
              )
            }
          >
            Delete
          </button>
        </div>
      </div>

      <FormError message={error} />

      {editing && (
        <form onSubmit={onSave} className="mb-6 rounded border border-line p-5">
          <div className="grid gap-4 md:grid-cols-2">
            <Field label="Class name" htmlFor="ec-name">
              <TextInput
                id="ec-name"
                value={ename}
                onChange={(e) => setEname(e.target.value)}
                required
              />
            </Field>
            <Field label="Academic year" htmlFor="ec-year">
              <TextInput
                id="ec-year"
                value={eyear}
                onChange={(e) => setEyear(e.target.value)}
                required
              />
            </Field>
          </div>
          <button type="submit" className="btn-primary">
            Save changes
          </button>
        </form>
      )}

      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold">
          Enrollments ({class_.enrollments.length})
        </h2>
      </div>

      {students.length > 0 && (
        <form
          className="mb-4 flex items-end gap-2"
          onSubmit={async (e) => {
            e.preventDefault();
            if (!addStudentId) return;
            setError(null);
            try {
              await addEnrollment(classId, parseInt(addStudentId, 10));
              setAddStudentId("");
              await load();
            } catch (err) {
              setError(err instanceof ApiError ? err.message : "Could not enroll the student.");
            }
          }}
        >
          <div className="w-80">
            <Field label="Enroll a student" htmlFor="add-student">
              <SelectInput
                id="add-student"
                value={addStudentId}
                onChange={(e) => setAddStudentId(e.target.value)}
              >
                <option value="">Select a student...</option>
                {students.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name} ({s.email})
                  </option>
                ))}
              </SelectInput>
            </Field>
          </div>
          <button type="submit" className="btn-primary mb-4">
            Enroll
          </button>
        </form>
      )}

      <DataTable
        columns={[
          { key: "name", header: "Student", render: (e) => e.student_name },
          { key: "email", header: "Email", render: (e) => e.student_email },
          {
            key: "actions",
            header: "",
            render: (e) => (
              <button
                className="text-alert underline"
                onClick={() =>
                  ask(
                    "Remove enrollment",
                    `Remove ${e.student_name} from this class?`,
                    async () => {
                      await removeEnrollment(classId, e.id);
                      await load();
                    }
                  )
                }
              >
                Remove
              </button>
            ),
          },
        ]}
        rows={class_.enrollments}
        emptyMessage="No students enrolled yet."
      />
      {dialog}
    </div>
  );
}
