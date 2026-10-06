"use client";

import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { Field, FormError, NumberInput, SelectInput, TextArea, TextInput } from "@/components/forms";
import {
  ApiError,
  createResearchSession,
  getClass,
  listResearchSessions,
  updateResearchSession,
  type ClassDetail,
  type ResearchSession,
} from "@/lib/api";

function fmtScore(value: number | null) {
  return value === null ? "-" : String(value);
}

const emptyForm = {
  student_id: "",
  pre_test_score: "",
  post_test_score: "",
  learning_period: "",
  notes: "",
};

export default function ResearchEvaluationPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const classId = parseInt(id, 10);
  const [class_, setClass_] = useState<ClassDetail | null>(null);
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const [c, s] = await Promise.all([getClass(classId), listResearchSessions(classId)]);
      setClass_(c);
      setSessions(s);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load research records.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, [classId]);

  function startEdit(s: ResearchSession) {
    setEditingId(s.id);
    setForm({
      student_id: String(s.student_id),
      pre_test_score: s.pre_test_score === null ? "" : String(s.pre_test_score),
      post_test_score: s.post_test_score === null ? "" : String(s.post_test_score),
      learning_period: s.learning_period ?? "",
      notes: s.notes ?? "",
    });
  }

  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }

  function num(value: string): number | null {
    if (value.trim() === "") return null;
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  async function save() {
    if (!form.student_id && editingId === null) {
      setError("Select a student.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const data = {
        pre_test_score: num(form.pre_test_score),
        post_test_score: num(form.post_test_score),
        learning_period: form.learning_period.trim() || null,
        notes: form.notes.trim() || null,
      };
      if (editingId === null) {
        await createResearchSession(classId, {
          student_id: parseInt(form.student_id, 10),
          ...data,
        });
      } else {
        await updateResearchSession(editingId, data);
      }
      cancelEdit();
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save the record.");
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading research records.</p>;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <p className="mb-4 text-sm text-muted">
        <a href="/teacher/classes">Classes</a> /{" "}
        <a href={`/teacher/classes/${classId}`}>{class_?.name}</a> / Research evaluation
      </p>
      <h1 className="text-xl font-semibold">Research evaluation</h1>
      <p className="mt-1 text-sm text-muted">
        Pre-test and post-test measurements for education research. Score
        change is calculated as post-test minus pre-test and reported as a
        measured value only.
      </p>
      {error && <FormError message={error} />}

      <div className="mt-6 rounded border border-line p-5">
        <h2 className="text-base font-semibold">
          {editingId === null ? "Add research record" : "Edit research record"}
        </h2>
        <div className="mt-4 grid max-w-2xl gap-4">
          <Field label="Student" htmlFor="rs-student">
            <SelectInput
              id="rs-student"
              value={form.student_id}
              onChange={(e) => setForm({ ...form, student_id: e.target.value })}
              disabled={editingId !== null}
            >
              <option value="">Select a student</option>
              {(class_?.enrollments ?? []).map((e) => (
                <option key={e.student_id} value={e.student_id}>
                  {e.student_name}
                </option>
              ))}
            </SelectInput>
          </Field>
          <div className="grid grid-cols-2 gap-4">
            <Field label="Pre-test score" htmlFor="rs-pre">
              <NumberInput
                id="rs-pre"
                value={form.pre_test_score}
                onChange={(e) => setForm({ ...form, pre_test_score: e.target.value })}
                placeholder="e.g. 45"
              />
            </Field>
            <Field label="Post-test score" htmlFor="rs-post">
              <NumberInput
                id="rs-post"
                value={form.post_test_score}
                onChange={(e) => setForm({ ...form, post_test_score: e.target.value })}
                placeholder="e.g. 72.5"
              />
            </Field>
          </div>
          <Field label="Learning period" htmlFor="rs-period">
            <TextInput
              id="rs-period"
              value={form.learning_period}
              onChange={(e) => setForm({ ...form, learning_period: e.target.value })}
              placeholder="e.g. 6 weeks"
            />
          </Field>
          <Field label="Research notes" htmlFor="rs-notes">
            <TextArea
              id="rs-notes"
              rows={3}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
            />
          </Field>
          <div className="flex gap-2">
            <button type="button" className="btn btn-primary" disabled={saving} onClick={save}>
              {saving ? "Saving..." : editingId === null ? "Add record" : "Save changes"}
            </button>
            {editingId !== null && (
              <button type="button" className="btn" onClick={cancelEdit}>
                Cancel
              </button>
            )}
          </div>
        </div>
      </div>

      <div className="mt-8">
        <DataTable
          columns={[
            {
              key: "student",
              header: "Student identifier",
              render: (r) => (
                <span>
                  {r.student_name}
                  <span className="block text-xs text-muted">ID {r.student_id}</span>
                </span>
              ),
            },
            { key: "class", header: "Class", render: (r) => <span>{r.class_name}</span> },
            { key: "course", header: "Course", render: (r) => <span>{r.course_title}</span> },
            { key: "pre", header: "Pre-test score", render: (r) => <span>{fmtScore(r.pre_test_score)}</span> },
            {
              key: "period",
              header: "Learning period",
              render: (r) => <span>{r.learning_period || "-"}</span>,
            },
            { key: "post", header: "Post-test score", render: (r) => <span>{fmtScore(r.post_test_score)}</span> },
            {
              key: "change",
              header: "Score change",
              render: (r) => <span>{r.score_change === null ? "-" : String(r.score_change)}</span>,
            },
            {
              key: "notes",
              header: "Research notes",
              render: (r) => <span className="text-sm">{r.notes || "-"}</span>,
            },
            {
              key: "action",
              header: "Action",
              render: (r) => (
                <button type="button" className="btn" onClick={() => startEdit(r)}>
                  Edit
                </button>
              ),
            },
          ]}
          rows={sessions}
          emptyMessage="No research records yet. Add one above."
        />
      </div>
    </div>
  );
}
