"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { FormError } from "@/components/forms";
import {
  ApiError,
  dismissRecommendation,
  getAssessments,
  getTopic,
  listRecommendations,
  RECOMMENDATION_STATUS_LABELS,
  type Recommendation,
} from "@/lib/api";

export default function StudentRecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [firstLesson, setFirstLesson] = useState<Record<number, number | null>>({});
  const [practice, setPractice] = useState<Record<number, number | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const list = await listRecommendations();
      setRecs(list);
      const topicIds = [...new Set(list.map((r) => r.topic_id))];
      const lessonMap: Record<number, number | null> = {};
      const practiceMap: Record<number, number | null> = {};
      for (const tid of topicIds) {
        try {
          const detail = await getTopic(tid);
          const lessons = [...detail.lessons].sort(
            (a, b) => a.position - b.position
          );
          lessonMap[tid] = lessons.length ? lessons[0].id : null;
        } catch {
          lessonMap[tid] = null;
        }
        try {
          const assessments = await getAssessments(tid);
          const open = assessments.filter((a) => a.is_published);
          practiceMap[tid] = open.length ? open[0].id : null;
        } catch {
          practiceMap[tid] = null;
        }
      }
      setFirstLesson(lessonMap);
      setPractice(practiceMap);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load recommendations.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function dismiss(id: number) {
    try {
      await dismissRecommendation(id);
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not dismiss.");
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading recommendations.</p>;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-xl font-semibold">Recommendations</h1>
      <p className="mt-1 text-sm text-muted">
        Guidance based on your assessment results. Each recommendation states
        its reason.
      </p>
      {error && <FormError message={error} />}
      <div className="mt-6">
        <DataTable
          columns={[
            {
              key: "topic",
              header: "Topic",
              render: (r) => (
                <span>
                  {r.topic_title}
                  <span className="block text-xs text-muted">{r.course_title}</span>
                </span>
              ),
            },
            {
              key: "rec",
              header: "Recommendation",
              render: (r) => (
                <span>
                  <span className="font-semibold">{r.title}</span>
                  <span className="block text-sm text-muted">{r.message}</span>
                  {r.teacher_note && (
                    <span className="mt-1 block text-sm">
                      Teacher note: {r.teacher_note}
                    </span>
                  )}
                </span>
              ),
            },
            {
              key: "reason",
              header: "Reason",
              render: (r) => <span className="text-sm">{r.reason}</span>,
            },
            {
              key: "status",
              header: "Status",
              render: (r) => (
                <span>{RECOMMENDATION_STATUS_LABELS[r.status]}</span>
              ),
            },
            {
              key: "action",
              header: "Action",
              render: (r) => (
                <span className="flex flex-wrap gap-2">
                  {firstLesson[r.topic_id] ? (
                    <Link
                      href={`/student/lessons/${firstLesson[r.topic_id]}`}
                      className="no-underline"
                    >
                      Open lesson
                    </Link>
                  ) : null}
                  {practice[r.topic_id] ? (
                    <Link
                      href={`/student/assessments/${practice[r.topic_id]}/take`}
                      className="no-underline"
                    >
                      Start practice
                    </Link>
                  ) : null}
                  {r.status === "active" && (
                    <button
                      type="button"
                      className="btn"
                      onClick={() => dismiss(r.id)}
                    >
                      Dismiss
                    </button>
                  )}
                </span>
              ),
            },
          ]}
          rows={recs}
          emptyMessage="No recommendations yet. They appear after your assessments are marked."
        />
      </div>
    </div>
  );
}
