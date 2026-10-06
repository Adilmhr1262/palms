"use client";

import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { FormError, TextArea } from "@/components/forms";
import {
  ApiError,
  getTopicMastery,
  listRecommendations,
  MASTERY_STATUS_LABELS,
  reviewRecommendation,
  type MasteryRecord,
  type Recommendation,
} from "@/lib/api";

function MasteryCell({ records }: { records: MasteryRecord[] }) {
  if (!records.length) return <span className="text-muted">No graded attempts</span>;
  const m = records[0];
  return (
    <span>
      {m.status ? MASTERY_STATUS_LABELS[m.status] : "-"}
      <span className="text-muted">
        {" "}
        ({m.latest_score !== null ? `${Math.round(m.latest_score)}%` : "-"})
      </span>
    </span>
  );
}

export default function TeacherInterventionsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([]);
  const [mastery, setMastery] = useState<Record<string, MasteryRecord[]>>({});
  const [reviewing, setReviewing] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    try {
      const list = await listRecommendations();
      setRecs(list);
      const keys = [...new Set(list.map((r) => `${r.student_id}:${r.topic_id}`))];
      const map: Record<string, MasteryRecord[]> = {};
      for (const key of keys) {
        const [sid, tid] = key.split(":").map(Number);
        try {
          const records = await getTopicMastery(tid);
          map[key] = records.filter((m) => m.student_id === sid);
        } catch {
          map[key] = [];
        }
      }
      setMastery(map);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not load interventions.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  async function markReviewed(id: number) {
    try {
      await reviewRecommendation(id, note.trim());
      setReviewing(null);
      setNote("");
      await load();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not mark reviewed.");
    }
  }

  if (loading) return <p className="text-sm text-muted">Loading interventions.</p>;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-xl font-semibold">Interventions</h1>
      <p className="mt-1 text-sm text-muted">
        Active recommendations for students in your courses, highest priority
        first. Add a note and mark reviewed when you have followed up.
      </p>
      {error && <FormError message={error} />}
      <div className="mt-6">
        <DataTable
          columns={[
            {
              key: "student",
              header: "Student",
              render: (r) => <span>{r.student_name}</span>,
            },
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
              key: "mastery",
              header: "Current mastery",
              render: (r) => (
                <MasteryCell records={mastery[`${r.student_id}:${r.topic_id}`] ?? []} />
              ),
            },
            {
              key: "reason",
              header: "Recommendation reason",
              render: (r) => (
                <span>
                  <span className="font-semibold">{r.title}</span>
                  <span className="block text-sm text-muted">{r.reason}</span>
                </span>
              ),
            },
            {
              key: "action",
              header: "Action",
              render: (r) => (
                <span>
                  {reviewing === r.id ? (
                    <span className="block min-w-56">
                      <label
                        htmlFor={`note-${r.id}`}
                        className="mb-1 block text-sm text-muted"
                      >
                        Teacher note
                      </label>
                      <TextArea
                        id={`note-${r.id}`}
                        value={note}
                        onChange={(e) => setNote(e.target.value)}
                        rows={3}
                      />
                      <span className="mt-2 flex gap-2">
                        <button
                          type="button"
                          className="btn btn-primary"
                          onClick={() => markReviewed(r.id)}
                        >
                          Mark reviewed
                        </button>
                        <button
                          type="button"
                          className="btn"
                          onClick={() => {
                            setReviewing(null);
                            setNote("");
                          }}
                        >
                          Cancel
                        </button>
                      </span>
                    </span>
                  ) : (
                    <button
                      type="button"
                      className="btn"
                      onClick={() => {
                        setReviewing(r.id);
                        setNote(r.teacher_note ?? "");
                      }}
                    >
                      Review
                    </button>
                  )}
                </span>
              ),
            },
          ]}
          rows={recs}
          emptyMessage="No active recommendations. They appear when students are marked."
        />
      </div>
    </div>
  );
}
