"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { Field, FormError, NumberInput, TextArea } from "@/components/forms";
import {
  ApiError,
  getAssessment,
  getGradingQueue,
  getTopic,
  gradeAnswer,
  type AssessmentDetail,
  type GradingQueueItem,
  type TopicDetail,
} from "@/lib/api";

function GradeForm({
  item,
  onSaved,
}: {
  item: GradingQueueItem;
  onSaved: (graded: GradingQueueItem) => void;
}) {
  const [points, setPoints] = useState("");
  const [comment, setComment] = useState(item.teacher_comment || "");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function save() {
    setError(null);
    setSaving(true);
    try {
      const graded = await gradeAnswer(item.answer_id, {
        points_earned: Number(points),
        teacher_comment: comment || null,
      });
      onSaved({
        ...item,
        points_earned: graded.points_earned,
        teacher_comment: graded.teacher_comment,
      });
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save the grade.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-2">
      <FormError message={error} />
      <div className="flex items-center gap-2">
        <NumberInput
          id={`pts-${item.answer_id}`}
          min={0}
          max={item.question_points}
          value={points}
          onChange={(e) => setPoints(e.target.value)}
          placeholder="0"
          className="w-24"
          aria-label={`Points out of ${item.question_points}`}
        />
        <span className="text-sm text-muted">/ {item.question_points}</span>
      </div>
      <TextArea
        id={`cmt-${item.answer_id}`}
        rows={2}
        value={comment}
        onChange={(e) => setComment(e.target.value)}
        placeholder="Comment for the student (optional)."
      />
      <button
        className="btn-primary px-3 py-1 text-[13px]"
        onClick={save}
        disabled={saving || points === ""}
      >
        {saving ? "Saving." : "Save grade"}
      </button>
    </div>
  );
}

export default function GradingQueuePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const aid = Number(id);
  const [detail, setDetail] = useState<AssessmentDetail | null>(null);
  const [topic, setTopic] = useState<TopicDetail | null>(null);
  const [items, setItems] = useState<GradingQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const d = await getAssessment(aid);
      setDetail(d);
      const [t, q] = await Promise.all([
        getTopic(d.topic_id),
        getGradingQueue(aid),
      ]);
      setTopic(t);
      setItems(q);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load the grading queue.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function onSaved(graded: GradingQueueItem) {
    setItems((list) =>
      list.map((x) => (x.answer_id === graded.answer_id ? graded : x))
    );
  }

  if (loading) return <p className="text-sm text-muted">Loading grading queue.</p>;
  if (!detail) return <FormError message={error || "Assessment not found."} />;

  const withId = (x: GradingQueueItem) => ({ ...x, id: x.answer_id });
  const pending = items.filter((x) => x.points_earned === null).map(withId);
  const reviewed = items.filter((x) => x.points_earned !== null).map(withId);

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
            /{" "}
            <Link href={`/teacher/assessments/${detail.id}`}>{detail.title}</Link>{" "}
            /
          </>
        )}{" "}
        Grading queue
      </p>
      <div className="mb-6">
        <h1 className="text-xl font-semibold">Grading queue</h1>
        <p className="mt-1 text-sm text-muted">
          {detail.title} - {pending.length} awaiting review
        </p>
      </div>
      <FormError message={error} />

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold">Awaiting review</h2>
        <DataTable
          columns={[
            {
              key: "student",
              header: "Student",
              render: (x) => <span>{x.student_name}</span>,
            },
            {
              key: "question",
              header: "Question",
              render: (x) => (
                <span className="font-serif">{x.question_prompt}</span>
              ),
            },
            {
              key: "answer",
              header: "Student answer",
              render: (x) => (
                <span className="font-serif">
                  {x.student_text ? x.student_text : <em className="text-muted">No answer given.</em>}
                </span>
              ),
            },
            {
              key: "grade",
              header: "Points and comment",
              render: (x) => <GradeForm item={x} onSaved={onSaved} />,
            },
          ]}
          rows={pending}
          emptyMessage="Nothing awaiting review."
        />
      </section>

      <section className="mb-8">
        <h2 className="mb-3 text-base font-semibold">Reviewed</h2>
        <DataTable
          columns={[
            {
              key: "student",
              header: "Student",
              render: (x) => <span>{x.student_name}</span>,
            },
            {
              key: "question",
              header: "Question",
              render: (x) => (
                <span className="font-serif">{x.question_prompt}</span>
              ),
            },
            {
              key: "points",
              header: "Points",
              render: (x) => (
                <span>
                  {x.points_earned} / {x.question_points}
                </span>
              ),
            },
            {
              key: "comment",
              header: "Comment",
              render: (x) => (
                <span className="text-sm">
                  {x.teacher_comment || <span className="text-muted">-</span>}
                </span>
              ),
            },
          ]}
          rows={reviewed}
          emptyMessage="No reviewed answers yet."
        />
      </section>
    </div>
  );
}
