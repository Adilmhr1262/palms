"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { useConfirm } from "@/components/ConfirmDialog";
import { Field, FormError, TextArea, TextInput } from "@/components/forms";
import {
  ApiError,
  createAssessment,
  deleteAssessment,
  getAssessments,
  getTopic,
  getTopicMastery,
  MASTERY_STATUS_LABELS,
  type Assessment,
  type MasteryRecord,
  type TopicDetail,
} from "@/lib/api";

export default function TeacherAssessmentsPage({
  params,
}: {
  params: Promise<{ topicId: string }>;
}) {
  const { topicId } = use(params);
  const tid = Number(topicId);
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [assessments, setAssessments] = useState<Assessment[]>([]);
  const [mastery, setMastery] = useState<MasteryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showNew, setShowNew] = useState(false);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [saving, setSaving] = useState(false);
  const confirm = useConfirm();

  async function load() {
    try {
      const [t, list, mast] = await Promise.all([
        getTopic(tid),
        getAssessments(tid),
        getTopicMastery(tid),
      ]);
      setTopic(t);
      setAssessments(list);
      setMastery(mast);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load assessments.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const created = await createAssessment(tid, {
        title: title.trim(),
        instructions: instructions.trim() || undefined,
      });
      setAssessments((list) => [...list, created]);
      setTitle("");
      setInstructions("");
      setShowNew(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create the assessment.");
    } finally {
      setSaving(false);
    }
  }

  function remove(a: Assessment) {
    confirm.ask(
      "Delete assessment",
      `Delete "${a.title}"? Student attempts on it will be removed as well.`,
      async () => {
        try {
          await deleteAssessment(a.id);
          setAssessments((list) => list.filter((x) => x.id !== a.id));
        } catch (err) {
          setError(err instanceof ApiError ? err.message : "Could not delete the assessment.");
        }
      }
    );
  }

  if (loading) return <p className="text-sm text-muted">Loading assessments.</p>;

  return (
    <div>
      <p className="mb-4 text-sm text-muted">
        {topic && (
          <Link href={`/teacher/courses/${topic.course_id}`}>
            {topic.course_title}
          </Link>
        )}{" "}
        / Assessments
      </p>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">Assessments</h1>
          {topic && <p className="mt-1 text-sm text-muted">{topic.title}</p>}
        </div>
        <button className="btn-primary" onClick={() => setShowNew((v) => !v)}>
          New assessment
        </button>
      </div>
      <FormError message={error} />

      {showNew && (
        <form
          onSubmit={onCreate}
          className="mb-6 rounded border border-line p-5"
        >
          <h2 className="mb-4 text-base font-semibold">New assessment</h2>
          <div className="grid gap-4">
            <Field label="Title" htmlFor="as-title">
              <TextInput
                id="as-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                maxLength={200}
                placeholder="Fractions check"
              />
            </Field>
            <Field label="Instructions (shown to students before they start)" htmlFor="as-instructions">
              <TextArea
                id="as-instructions"
                rows={3}
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="How students should approach the questions."
              />
            </Field>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              type="button"
              className="btn-secondary"
              onClick={() => setShowNew(false)}
            >
              Cancel
            </button>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? "Saving." : "Create assessment"}
            </button>
          </div>
        </form>
      )}

      <DataTable
        columns={[
          {
            key: "title",
            header: "Title",
            render: (a) => (
              <Link href={`/teacher/assessments/${a.id}`}>{a.title}</Link>
            ),
          },
          {
            key: "questions",
            header: "Questions",
            render: (a) => <span>{a.question_count}</span>,
          },
          {
            key: "status",
            header: "Status",
            render: (a) => (
              <span
                className={
                  a.is_published ? "text-success" : "text-muted"
                }
              >
                {a.is_published ? "Published" : "Draft"}
              </span>
            ),
          },
          {
            key: "actions",
            header: "Actions",
            render: (a) => (
              <span className="flex gap-2">
                <Link
                  href={`/teacher/assessments/${a.id}`}
                  className="btn-secondary px-3 py-1 text-[13px] no-underline"
                >
                  Open
                </Link>
                <button
                  className="btn-secondary px-3 py-1 text-[13px]"
                  onClick={() => remove(a)}
                >
                  Delete
                </button>
              </span>
            ),
          },
        ]}
        rows={assessments}
        emptyMessage="No assessments yet. Create the first one."
      />
      <section className="mt-8">
        <h2 className="mb-3 text-base font-semibold">Student mastery</h2>
        <DataTable
          columns={[
            {
              key: "student",
              header: "Student",
              render: (m) => <span>{m.student_name}</span>,
            },
            {
              key: "attempts",
              header: "Graded attempts",
              render: (m) => <span>{m.attempts_count}</span>,
            },
            {
              key: "latest",
              header: "Latest",
              render: (m) => (
                <span>
                  {m.latest_score !== null ? `${Math.round(m.latest_score)}%` : "-"}
                </span>
              ),
            },
            {
              key: "best",
              header: "Best",
              render: (m) => (
                <span>
                  {m.best_score !== null ? `${Math.round(m.best_score)}%` : "-"}
                </span>
              ),
            },
            {
              key: "status",
              header: "Status",
              render: (m) => (
                <span>
                  {m.status ? MASTERY_STATUS_LABELS[m.status] : "-"}
                </span>
              ),
            },
          ]}
          rows={mastery}
          emptyMessage="No graded attempts yet. Mastery appears after assessments are marked."
        />
      </section>
      {confirm.dialog}
    </div>
  );
}
