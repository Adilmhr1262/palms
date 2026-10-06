"use client";

import { use, useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { Field, FormError, SelectInput } from "@/components/forms";
import {
  ApiError,
  downloadCsv,
  getClass,
  getClassProgress,
  getStudentProgress,
  MASTERY_STATUS_LABELS,
  type ClassDetail,
  type ClassProgressRow,
  type MasteryStatus,
  type StudentProgressRow,
} from "@/lib/api";

function fmtScore(value: number | null) {
  return value === null ? "-" : `${Math.round(value)}%`;
}

function masteryLabel(status: string | null) {
  if (!status) return "-";
  return (
    MASTERY_STATUS_LABELS[status as MasteryStatus] ?? status.replace(/_/g, " ")
  );
}

export default function TeacherReportsPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const classId = parseInt(id, 10);
  const [class_, setClass_] = useState<ClassDetail | null>(null);
  const [progress, setProgress] = useState<ClassProgressRow[]>([]);
  const [studentId, setStudentId] = useState("");
  const [studentRows, setStudentRows] = useState<StudentProgressRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getClass(classId), getClassProgress(classId)])
      .then(([c, p]) => {
        setClass_(c);
        setProgress(p);
        if (c.enrollments.length) setStudentId(String(c.enrollments[0].student_id));
      })
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load reports.")
      )
      .finally(() => setLoading(false));
  }, [classId]);

  useEffect(() => {
    if (!studentId) return;
    getStudentProgress(classId, parseInt(studentId, 10))
      .then(setStudentRows)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load the student report.")
      );
  }, [classId, studentId]);

  async function exportCsv(kind: "mastery" | "assessments" | "research") {
    setDownloading(kind);
    setError(null);
    try {
      await downloadCsv(
        `/exports/${kind}.csv?class_id=${classId}`,
        `${kind}-class-${classId}.csv`
      );
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not export the file.");
    } finally {
      setDownloading(null);
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading reports.</p>;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <p className="mb-4 text-sm text-muted">
        <a href="/teacher/classes">Classes</a> /{" "}
        <a href={`/teacher/classes/${classId}`}>{class_?.name}</a> / Reports
      </p>
      <h1 className="text-xl font-semibold">Reports</h1>
      <p className="mt-1 text-sm text-muted">
        Class and student progress for {class_?.name}. Exports are CSV files.
      </p>
      {error && <FormError message={error} />}

      <div className="mt-6 flex flex-wrap gap-2">
        <button
          type="button"
          className="btn"
          disabled={downloading === "mastery"}
          onClick={() => exportCsv("mastery")}
        >
          {downloading === "mastery" ? "Exporting..." : "Export mastery CSV"}
        </button>
        <button
          type="button"
          className="btn"
          disabled={downloading === "assessments"}
          onClick={() => exportCsv("assessments")}
        >
          {downloading === "assessments" ? "Exporting..." : "Export assessment results CSV"}
        </button>
        <button
          type="button"
          className="btn"
          disabled={downloading === "research"}
          onClick={() => exportCsv("research")}
        >
          {downloading === "research" ? "Exporting..." : "Export research CSV"}
        </button>
      </div>

      <h2 className="mt-8 text-base font-semibold">Class progress report</h2>
      <div className="mt-3">
        <DataTable
          columns={[
            { key: "student", header: "Student", render: (r) => <span>{r.student_name}</span> },
            { key: "topic", header: "Topic", render: (r) => <span>{r.topic_title}</span> },
            { key: "attempts", header: "Attempts", render: (r) => <span>{r.attempts_count}</span> },
            { key: "latest", header: "Latest score", render: (r) => <span>{fmtScore(r.latest_score)}</span> },
            { key: "best", header: "Best score", render: (r) => <span>{fmtScore(r.best_score)}</span> },
            { key: "mastery", header: "Mastery status", render: (r) => <span>{masteryLabel(r.mastery_status)}</span> },
          ]}
          rows={progress}
          emptyMessage="No students enrolled yet."
        />
      </div>

      <h2 className="mt-8 text-base font-semibold">Student progress report</h2>
      <div className="mt-3 max-w-xs">
        <Field label="Student" htmlFor="report-student">
          <SelectInput
            id="report-student"
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
      <div className="mt-3">
        <DataTable
          columns={[
            { key: "topic", header: "Topic", render: (r) => <span>{r.topic_title}</span> },
            {
              key: "lessons",
              header: "Lessons completed",
              render: (r) => <span>{r.lessons_completed} of {r.lessons_total}</span>,
            },
            {
              key: "attempts",
              header: "Assessment attempts",
              render: (r) => <span>{r.assessment_attempts}</span>,
            },
            { key: "latest", header: "Latest score", render: (r) => <span>{fmtScore(r.latest_score)}</span> },
            { key: "mastery", header: "Mastery status", render: (r) => <span>{masteryLabel(r.mastery_status)}</span> },
          ]}
          rows={studentRows}
          emptyMessage="No progress recorded for this student yet."
        />
      </div>
    </div>
  );
}
