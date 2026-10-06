"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { useConfirm } from "@/components/ConfirmDialog";
import {
  Field,
  FormError,
  NumberInput,
  SelectInput,
  TextArea,
  TextInput,
} from "@/components/forms";
import {
  ApiError,
  createQuestion,
  deleteQuestion,
  getQuestions,
  getTopic,
  updateQuestion,
  QUESTION_TYPE_LABELS,
  type Question,
  type QuestionType,
  type TopicDetail,
} from "@/lib/api";

type Draft = {
  qtype: QuestionType;
  prompt: string;
  options: string[];
  correct_option: number | null;
  model_answer: string;
  points: number;
};

const EMPTY_DRAFT: Draft = {
  qtype: "mcq",
  prompt: "",
  options: ["", ""],
  correct_option: null,
  model_answer: "",
  points: 1,
};

function toDraft(q: Question): Draft {
  return {
    qtype: q.qtype,
    prompt: q.prompt,
    options: q.options && q.options.length ? q.options : ["", ""],
    correct_option: q.correct_option,
    model_answer: q.model_answer || "",
    points: q.points,
  };
}

export default function QuestionBankPage({
  params,
}: {
  params: Promise<{ topicId: string }>;
}) {
  const { topicId } = use(params);
  const tid = Number(topicId);
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [questions, setQuestions] = useState<Question[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [editing, setEditing] = useState<Question | null>(null);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const confirm = useConfirm();

  async function load() {
    try {
      const [t, qs] = await Promise.all([getTopic(tid), getQuestions(tid)]);
      setTopic(t);
      setQuestions(qs);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the question bank.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function openNew() {
    setEditing(null);
    setDraft(EMPTY_DRAFT);
    setFormError(null);
    setShowForm(true);
  }

  function openEdit(q: Question) {
    setEditing(q);
    setDraft(toDraft(q));
    setFormError(null);
    setShowForm(true);
  }

  function setOption(i: number, value: string) {
    setDraft((d) => {
      const options = [...d.options];
      options[i] = value;
      return { ...d, options };
    });
  }

  function addOption() {
    setDraft((d) =>
      d.options.length >= 6 ? d : { ...d, options: [...d.options, ""] }
    );
  }

  function removeOption(i: number) {
    setDraft((d) => {
      if (d.options.length <= 2) return d;
      const options = d.options.filter((_, j) => j !== i);
      let correct_option = d.correct_option;
      if (correct_option === i) correct_option = null;
      else if (correct_option !== null && correct_option > i) correct_option -= 1;
      return { ...d, options, correct_option };
    });
  }

  async function save() {
    setFormError(null);
    setSaving(true);
    try {
      const payload = {
        qtype: draft.qtype,
        prompt: draft.prompt,
        points: draft.points,
        options:
          draft.qtype === "mcq" ? draft.options.filter((o) => o.trim()) : null,
        correct_option:
          draft.qtype === "mcq" || draft.qtype === "true_false"
            ? draft.correct_option
            : null,
        model_answer:
          draft.qtype === "short_answer" ? draft.model_answer || null : null,
      };
      if (editing) {
        await updateQuestion(editing.id, payload);
      } else {
        await createQuestion(tid, payload);
      }
      setShowForm(false);
      setQuestions(await getQuestions(tid));
    } catch (e) {
      setFormError(e instanceof ApiError ? e.message : "Could not save the question.");
    } finally {
      setSaving(false);
    }
  }

  function remove(q: Question) {
    confirm.ask(
      "Delete question",
      "Delete this question? It will also be removed from any draft assessments.",
      async () => {
        try {
          await deleteQuestion(q.id);
          setQuestions((qs) => qs.filter((x) => x.id !== q.id));
        } catch (e) {
          setError(e instanceof ApiError ? e.message : "Could not delete the question.");
        }
      }
    );
  }

  if (loading) return <p className="text-sm text-muted">Loading question bank.</p>;

  return (
    <div>
      <p className="mb-4 text-sm text-muted">
        {topic && (
          <Link href={`/teacher/courses/${topic.course_id}`}>
            {topic.course_title}
          </Link>
        )}{" "}
        / Question bank
      </p>
      <div className="mb-6 flex items-start justify-between">
        <div>
          <h1 className="text-xl font-semibold">Question bank</h1>
          {topic && <p className="mt-1 text-sm text-muted">{topic.title}</p>}
        </div>
        <button className="btn-primary" onClick={openNew}>
          New question
        </button>
      </div>
      <FormError message={error} />

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
              <span className="flex gap-2">
                <button
                  className="btn-secondary px-3 py-1 text-[13px]"
                  onClick={() => openEdit(q)}
                >
                  Edit
                </button>
                <button
                  className="btn-secondary px-3 py-1 text-[13px]"
                  onClick={() => remove(q)}
                >
                  Delete
                </button>
              </span>
            ),
          },
        ]}
        rows={questions}
        emptyMessage="No questions yet. Add the first one."
      />

      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 p-4">
          <div className="max-h-[90vh] w-full max-w-2xl overflow-y-auto rounded border border-line bg-paper p-6">
            <h2 className="mb-4 text-base font-semibold">
              {editing ? "Edit question" : "New question"}
            </h2>
            <FormError message={formError} />
            <Field label="Question type" htmlFor="qb-type">
              <SelectInput
                id="qb-type"
                value={draft.qtype}
                onChange={(e) =>
                  setDraft((d) => ({
                    ...d,
                    qtype: e.target.value as QuestionType,
                    correct_option: null,
                    options:
                      e.target.value === "mcq" && d.options.length < 2
                        ? ["", ""]
                        : d.options,
                  }))
                }
              >
                <option value="mcq">Multiple choice</option>
                <option value="true_false">True / False</option>
                <option value="short_answer">Short answer</option>
              </SelectInput>
            </Field>
            <Field label="Question" htmlFor="qb-prompt">
              <TextArea
                id="qb-prompt"
                rows={3}
                value={draft.prompt}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, prompt: e.target.value }))
                }
                placeholder="Write the question as the student will read it."
              />
            </Field>

            {draft.qtype === "mcq" && (
              <Field label="Options (mark the correct one)" htmlFor="qb-opt">
                <div className="space-y-2">
                  {draft.options.map((opt, i) => (
                    <div key={i} className="flex items-center gap-2">
                      <input
                        type="radio"
                        name="correct-option"
                        checked={draft.correct_option === i}
                        onChange={() =>
                          setDraft((d) => ({ ...d, correct_option: i }))
                        }
                        aria-label={`Mark option ${i + 1} as correct`}
                      />
                      <TextInput
                        value={opt}
                        onChange={(e) => setOption(i, e.target.value)}
                        placeholder={`Option ${i + 1}`}
                      />
                      <button
                        type="button"
                        className="btn-secondary px-3 py-1 text-[13px]"
                        onClick={() => removeOption(i)}
                        disabled={draft.options.length <= 2}
                      >
                        Remove
                      </button>
                    </div>
                  ))}
                </div>
                <button
                  type="button"
                  className="btn-secondary mt-2 px-3 py-1 text-[13px]"
                  onClick={addOption}
                  disabled={draft.options.length >= 6}
                >
                  Add option
                </button>
              </Field>
            )}

            {draft.qtype === "true_false" && (
              <Field label="Correct answer" htmlFor="qb-correct">
                <SelectInput
                  id="qb-correct"
                  value={
                    draft.correct_option === null
                      ? ""
                      : String(draft.correct_option)
                  }
                  onChange={(e) =>
                    setDraft((d) => ({
                      ...d,
                      correct_option:
                        e.target.value === "" ? null : Number(e.target.value),
                    }))
                  }
                >
                  <option value="">Select</option>
                  <option value="0">True</option>
                  <option value="1">False</option>
                </SelectInput>
              </Field>
            )}

            {draft.qtype === "short_answer" && (
              <Field label="Model answer (for the teacher marking guide)" htmlFor="qb-model">
                <TextArea
                  id="qb-model"
                  rows={3}
                  value={draft.model_answer}
                  onChange={(e) =>
                    setDraft((d) => ({ ...d, model_answer: e.target.value }))
                  }
                  placeholder="What a good answer should cover."
                />
              </Field>
            )}

            <Field label="Points" htmlFor="qb-points">
              <NumberInput
                id="qb-points"
                min={1}
                value={draft.points}
                onChange={(e) =>
                  setDraft((d) => ({ ...d, points: Number(e.target.value) || 1 }))
                }
              />
            </Field>

            <div className="mt-5 flex justify-end gap-2">
              <button className="btn-secondary" onClick={() => setShowForm(false)}>
                Cancel
              </button>
              <button className="btn-primary" onClick={save} disabled={saving}>
                {saving ? "Saving." : editing ? "Save changes" : "Add question"}
              </button>
            </div>
          </div>
        </div>
      )}
      {confirm.dialog}
    </div>
  );
}
