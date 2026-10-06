"use client";

import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { Field, FormError, SelectInput } from "@/components/forms";
import {
  ApiError,
  getClass,
  getFeedbackHistory,
  type ClassDetail,
  type FeedbackHistoryRow,
} from "@/lib/api";

function fmtDate(value: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleDateString();
}

export default function TeacherFeedbackHistoryPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const classId = parseInt(id, 10);
  const [class_, setClass_] = useState<ClassDetail | null>(null);
  const [studentId, setStudentId] = useState("");
  const [rows, setRows] = useState<FeedbackHistoryRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getClass(classId)
      .then((c) => {
        setClass_(c);
        if (c.enrollments.length && !studentId) {
          setStudentId(String(c.enrollments[0].student_id));
        }
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load the class.")
      )
      .finally(() => setLoading(false));
  }, [classId]);

  useEffect(() => {
    if (!studentId) return;
    getFeedbackHistory(classId, parseInt(studentId, 10))
      .then(setRows)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load feedback.")
      );
  }, [classId, studentId]);

  if (loading) return <p className="text-sm text-muted">Loading feedback history.</p>;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <p className="mb-4 text-sm text-muted">
        <a href="/teacher/classes">Classes</a> /{" "}
        <a href={`/teacher/classes/${classId}`}>{class_?.name}</a> / Feedback history
      </p>
      <h1 className="text-xl font-semibold">Student feedback history</h1>
      <p className="mt-1 text-sm text-muted">
        Assessment history, teacher comments, and interventions for one student.
      </p>
      {error && <FormError message={error} />}
      <div className="mt-4 max-w-xs">
        <Field label="Student" htmlFor="student">
          <SelectInput
            id="student"
            value={studentId}
            onChange={(e) => setStudentId(e.target.value)}
          >
            {(class_?.enrollments ?? []).map((e) => (
              <option key={e.student_id} value={e.student_id}>
                {e.student_name}
              </option>
            ))}
          </SelectInput>
        </Field>
      </div>
      <div className="mt-4">
        <DataTable
          columns={[
            {
              key: "date",
              header: "Date",
              render: (r) => <span>{fmtDate(r.date)}</span>,
            },
            {
              key: "course",
              header: "Course",
              render: (r) => <span>{r.course_title}</span>,
            },
            {
              key: "topic",
              header: "Topic",
              render: (r) => <span>{r.topic_title}</span>,
            },
            {
              key: "assessment",
              header: "Assessment",
              render: (r) => <span>{r.assessment_title}</span>,
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
              key: "intervention",
              header: "Intervention",
              render: (r) => <span className="text-sm">{r.intervention || "-"}</span>,
            },
          ]}
          rows={rows}
          emptyMessage="No graded assessments for this student yet."
        />
      </div>
    </div>
  );
}
