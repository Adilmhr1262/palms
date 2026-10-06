"use client";

import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { FormError } from "@/components/forms";
import {
  ApiError,
  getMyFeedback,
  type StudentFeedbackRow,
} from "@/lib/api";

function fmtDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString();
}

export default function StudentFeedbackPage() {
  const [rows, setRows] = useState<StudentFeedbackRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getMyFeedback()
      .then(setRows)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load your feedback.")
      )
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="text-sm text-muted">Loading your feedback.</p>;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-xl font-semibold">My feedback</h1>
      <p className="mt-1 text-sm text-muted">
        Your assessment results, teacher comments, and suggestions for
        improvement.
      </p>
      {error && <FormError message={error} />}
      <div className="mt-6">
        <DataTable
          columns={[
            {
              key: "date",
              header: "Date",
              render: (r) => <span>{fmtDate(r.date)}</span>,
            },
            {
              key: "assessment",
              header: "Assessment",
              render: (r) => <span>{r.assessment_title}</span>,
            },
            {
              key: "topic",
              header: "Topic",
              render: (r) => <span>{r.topic_title}</span>,
            },
            {
              key: "score",
              header: "Score",
              render: (r) => <span>{r.score}</span>,
            },
            {
              key: "comment",
              header: "Teacher comment",
              render: (r) => (
                <span className="text-sm">{r.teacher_comment || "-"}</span>
              ),
            },
            {
              key: "suggestion",
              header: "Suggestion",
              render: (r) => <span className="text-sm">{r.suggestion || "-"}</span>,
            },
          ]}
          rows={rows}
          emptyMessage="No feedback yet. It appears after your assessments are marked."
        />
      </div>
    </div>
  );
}
