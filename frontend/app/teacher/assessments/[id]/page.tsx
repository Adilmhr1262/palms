"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { useConfirm } from "@/components/ConfirmDialog";
import { Field, FormError, NumberInput, TextArea, TextInput } from "@/components/forms";
import {
  ApiError,
  addAssessmentQuestion,
  deleteAssessment,
  getAssessment,
  getAssessmentAttempts,
  getGradingQueue,
  getQuestions,
  getTopic,
  moveAssessmentQuestion,
  publishAssessment,
  removeAssessmentQuestion,
  updateAssessment,
  QUESTION_TYPE_LABELS,
  type AssessmentDetail,
  type AttemptDetail,
  type GradingQueueItem,
  type Question,
  type TopicDetail,
} from "@/lib/api";

export default function AssessmentBuilderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const aid = Number(id);
  const [detail, setDetail] = useState<AssessmentDetail | null>(null);
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [bank, setBank] = useState<Question[]>([]);
  const [attempts, setAttempts] = useState<AttemptDetail[]>([]);
  const [queue, setQueue] = useState<GradingQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingMeta, setEditingMeta] = useState(false);
  const [title, setTitle] = useState("");
  const [instructions, setInstructions] = useState("");
  const [saving, setSaving] = useState(false);
  const confirm = useConfirm();

  async function load() {
    try {
      const d = await getAssessment(aid);
      setDetail(d);
      setTitle(d.title);
      setInstructions(d.instructions || "");
      const [t, qs, atts, gq] = await Promise.all([
        getTopic(d.topic_id),
        getQuestions(d.topic_id),
        getAssessmentAttempts(aid),
        getGradingQueue(aid),
      ]);
      setTopic(t);
      setBank(qs);
      setAttempts(atts);
      setQueue(gq);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the assessment.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function saveMeta() {
    if (!detail) return;
    setSaving(true);
    try {
      const updated = await updateAssessment(aid, {
        title: title.trim(),
        instructions: instructions.trim() || null,
      });
      setDetail({ ...detail, title: updated.title, instructions: updated.instructions });
      setEditingMeta(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save changes.");
    } finally {
      setSaving(false);
    }
  }

  async function togglePublish() {
    if (!detail) return;
    try {
      const updated = await publishAssessment(aid, !detail.is_published);
      setDetail({ ...detail, is_published: updated.is_published });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not change publish state.");
    }
  }

  async function addQuestion(q: Question) {
    if (!detail) return;
    try {
      await addAssessmentQuestion(aid, { question_id: q.id });
      setDetail(await getAssessment(aid));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not add the question.");
    }
  }

  async function changePosition(questionId: number, position: number) {
    if (!detail) return;
    try {
      await moveAssessmentQuestion(aid, questionId, position);
      setDetail(await getAssessment(aid));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not move the question.");
    }
  }

  function removeQuestion(questionId: number) {
    confirm.ask(
      "Remove question",
      "Remove this question from the assessment? The question stays in the bank.",
      async () => {
        try {
          await removeAssessmentQuestion(aid, questionId);
          setDetail(await getAssessment(aid));
        } catch (e) {
          setError(e instanceof ApiError ? e.message : "Could not remove the question.");
        }
      }
    );
  }

  function deleteWhole() {
    if (!detail) return;
    confirm.ask(
      "Delete assessment",
      `Delete "${detail.title}"? Student attempts on it will be removed as well.`,
      async () => {
        try {
          await deleteAssessment(aid);
          window.location.href = `/teacher/topics/${detail.topic_id}/assessments`;
        } catch (e) {
          setError(e instanceof ApiError ? e.message : "Could not delete the assessment.");
        }
      }
    );
  }

  if (loading) return <p className="text-sm text-muted">Loading assessment.</p>;
  if (!detail) return <FormError message={error || "Assessment not found."} />;

  const inAssessment = new Set(detail.questions.map((q) => q.question_id));
  const available = bank.filter((q) => !inAssessment.has(q.id));
  const sorted = [...detail.questions]
    .sort((a, b) => a.position - b.position)
    .map((item) => ({ ...item, id: item.question_id }));

  return (
    <div>
      <p className="mb-4 text-sm text-muted">
        {topic && (
          <>
            <Link href={`/teacher/courses/${topic.course_id}`}>
              {topic.course_title}
            </Link>{" "}
            /{" "}
            <Link href={`/teacher/topics/${topic.id}/assessments`}>
              Assessments
            </Link>{" "}
            /
          </>
        )}{" "}
        Builder
      </p>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">{detail.title}</h1>
          <p className="mt-1 text-sm">
            <span className={detail.is_published ? "text-success" : "text-muted"}>
              {detail.is_published ? "Published" : "Draft"}
            </span>
            <span className="text-muted">
              {" "}
              - {detail.questions.length} question
              {detail.questions.length === 1 ? "" : "s"}
            </span>
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            href={`/teacher/assessments/${detail.id}/grading`}
            className="btn-secondary no-underline"
          >
            Grading queue ({queue.filter((x) => x.points_earned === null).length})
          </Link>
          <button className="btn-secondary" onClick={togglePublish}>
            {detail.is_published ? "Unpublish" : "Publish"}
          </button>
          <button className="btn-secondary" onClick={deleteWhole}>
            Delete
          </button>
        </div>
      </div>
      <FormError message={error} />
      {detail.is_published && (
        <p className="mb-6 rounded border border-line bg-wash p-4 text-sm text-muted">
          This assessment is published. The question set is locked while it is
          published; unpublish it to add, remove, or reorder questions.
        </p>
      )}

      <section className="mb-8">
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-base font-semibold">Details</h2>
          {!editingMeta && (
            <button
              className="btn-secondary px-3 py-1 text-[13px]"
              onClick={() => setEditingMeta(true)}
            >
              Edit
            </button>
          )}
        </div>
        {editingMeta ? (
          <div className="rounded border border-line p-5">
            <div className="grid gap-4">
              <Field label="Title" htmlFor="ab-title">
                <TextInput id="ab-title" value={title} onChange={(e) => setTitle(e.target.value)} maxLength={200} />
              </Field>
              <Field label="Instructions" htmlFor="ab-instructions">
                <TextArea
                  id="ab-instructions"
                  rows={3}
                  value={instructions}
                  onChange={(e) => setInstructions(e.target.value)}
                />
              </Field>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setEditingMeta(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={saveMeta} disabled={saving}>
                {saving ? "Saving." : "Save changes"}
              </button>
            </div>
          </div>
        ) : (
          <div className="rounded border border-line p-5 text-sm">
            {detail.instructions ? (
              <p className="whitespace-pre-line">{detail.instructions}</p>
            ) : (
              <p className="text-muted">No instructions set.</p>
            )}
          </div>
        )}
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold">Questions in this assessment</h2>
        <DataTable
          columns={[
            {
              key: "position",
              header: "No.",
              render: (item) =>
                detail.is_published ? (
                  <span>{item.position}</span>
                ) : (
                  <NumberInput
                    min={1}
                    value={item.position}
                    onChange={(e) =>
                      changePosition(item.question_id, Number(e.target.value) || 1)
                    }
                    className="w-20"
                  />
                ),
            },
            {
              key: "type",
              header: "Type",
              render: (item) => (
                <span className="whitespace-nowrap text-[13px] text-muted">
                  {item.question ? QUESTION_TYPE_LABELS[item.question.qtype] : "-"}
                </span>
              ),
            },
            {
              key: "prompt",
              header: "Question",
              render: (item) => (
                <span className="font-serif">{item.question?.prompt}</span>
              ),
            },
            {
              key: "points",
              header: "Points",
              render: (item) => <span>{item.question?.points}</span>,
            },
            {
              key: "actions",
              header: "Actions",
              render: (item) =>
                detail.is_published ? (
                  <span className="text-muted">-</span>
                ) : (
                  <button
                    className="btn-secondary px-3 py-1 text-[13px]"
                    onClick={() => removeQuestion(item.question_id)}
                  >
                    Remove
                  </button>
                ),
            },
          ]}
          rows={sorted}
          emptyMessage="No questions yet. Add some from the question bank below."
        />
      </section>

      {!detail.is_published && (
        <section className="mb-8">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-base font-semibold">Add from question bank</h2>
            {topic && (
              <Link
                href={`/teacher/bank/${topic.id}`}
                className="text-sm"
              >
                Open full question bank
              </Link>
            )}
          </div>
          <DataTable
            columns={[
              {
                key: "type",
                header: "Type",
                render: (q) => (
                  <span className="whitespace-nowrap text-[13px] text-muted">
                    {QUESTION_TYPE_LABELS[q.qtype]}
                  </span>
                ),
              },
              {
                key: "prompt",
                header: "Question",
                render: (q) => <span className="font-serif">{q.prompt}</span>,
              },
              {
                key: "points",
                header: "Points",
                render: (q) => <span>{q.points}</span>,
              },
              {
                key: "actions",
                header: "Actions",
                render: (q) => (
                  <button
                    className="btn-secondary px-3 py-1 text-[13px]"
                    onClick={() => addQuestion(q)}
                  >
                    Add
                  </button>
                ),
              },
            ]}
            rows={available}
            emptyMessage="Every bank question is already in this assessment."
          />
        </section>
      )}

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold">
          Student attempts ({attempts.length})
        </h2>
        <DataTable
          columns={[
            {
              key: "student",
              header: "Student",
              render: (a) => <span>{a.student_name}</span>,
            },
            {
              key: "status",
              header: "Status",
              render: (a) => (
                <span className="capitalize text-muted">{a.status.replace("_", " ")}</span>
              ),
            },
            {
              key: "started",
              header: "Started",
              render: (a) => (
                <span>{new Date(a.started_at).toLocaleString()}</span>
              ),
            },
            {
              key: "submitted",
              header: "Submitted",
              render: (a) => (
                <span>
                  {a.submitted_at ? new Date(a.submitted_at).toLocaleString() : "-"}
                </span>
              ),
            },
          ]}
          rows={attempts}
          emptyMessage="No student has started this assessment yet."
        />
        <p className="mt-2 text-sm text-muted">
          Grading of submitted attempts arrives in the next step.
        </p>
      </section>
      {confirm.dialog}
    </div>
  );
}
