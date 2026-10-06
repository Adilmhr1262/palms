"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { FormError } from "@/components/forms";
import {
  ApiError,
  getAssessments,
  getClass,
  getMyAttempts,
  getTopicMastery,
  getTopics,
  MASTERY_STATUS_LABELS,
  type Assessment,
  type Attempt,
  type ClassDetail,
  type MasteryRecord,
  type Topic,
} from "@/lib/api";

export default function ClassOutlinePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const classId = parseInt(id, 10);
  const [class_, setClass_] = useState<ClassDetail | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [assessments, setAssessments] = useState<Record<number, Assessment[]>>({});
  const [attempts, setAttempts] = useState<Record<number, Attempt[]>>({});
  const [mastery, setMastery] = useState<Record<number, MasteryRecord | null>>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function load() {
      try {
        const c = await getClass(classId);
        setClass_(c);
        if (c.course_id) {
          const ts = await getTopics(c.course_id);
          setTopics(ts);
          const byTopic: Record<number, Assessment[]> = {};
          const byAssessment: Record<number, Attempt[]> = {};
          const masteryByTopic: Record<number, MasteryRecord | null> = {};
          for (const t of ts) {
            const list = await getAssessments(t.id);
            byTopic[t.id] = list;
            for (const a of list) {
              byAssessment[a.id] = await getMyAttempts(a.id);
            }
            const records = await getTopicMastery(t.id);
            masteryByTopic[t.id] = records.length ? records[0] : null;
          }
          setAssessments(byTopic);
          setAttempts(byAssessment);
          setMastery(masteryByTopic);
        }
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Could not load the class.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [classId]);

  if (loading) return <p className="text-sm text-muted">Loading...</p>;
  if (!class_) return <FormError message={error || "Class not found."} />;

  return (
    <div>
      <a href="/student/classes" className="text-sm no-underline">
        ← My classes
      </a>
      <h1 className="mb-1 mt-2 text-xl font-semibold">
        {class_.name} <span className="font-normal text-muted">· {class_.academic_year}</span>
      </h1>
      <p className="mb-6 text-sm text-muted">
        {class_.course_title || "No course linked"} · {class_.teacher_name} ·{" "}
        <Link href={`/student/classes/${classId}/path`}>Learning path</Link>
      </p>
      <FormError message={error} />
      {topics.length === 0 ? (
        <p className="text-sm text-muted">No topics published yet.</p>
      ) : (
        topics.map((topic) => (
          <section key={topic.id} className="mb-8">
            <h2 className="border-b border-line pb-2 text-base font-semibold">
              <span className="mr-2 text-sm font-normal text-muted">
                {topic.position}.
              </span>
              {topic.title}
            </h2>
            {topic.description && (
              <p className="mt-2 text-sm text-muted">{topic.description}</p>
            )}
            {mastery[topic.id] && mastery[topic.id]!.status && (
              <p className="mt-2 text-sm">
                <span className="text-muted">Mastery: </span>
                {MASTERY_STATUS_LABELS[mastery[topic.id]!.status!]}
                <span className="text-muted">
                  {" "}- latest{" "}
                  {mastery[topic.id]!.latest_score !== null
                    ? `${Math.round(mastery[topic.id]!.latest_score!)}%`
                    : "-"}
                  {", best "}
                  {mastery[topic.id]!.best_score !== null
                    ? `${Math.round(mastery[topic.id]!.best_score!)}%`
                    : "-"}
                  {" - "}
                  {mastery[topic.id]!.attempts_count} graded{" "}
                  {mastery[topic.id]!.attempts_count === 1 ? "attempt" : "attempts"}
                </span>
              </p>
            )}
            {topic.lessons.length === 0 ? (
              <p className="mt-3 text-sm text-muted">No lessons yet.</p>
            ) : (
              <ol className="mt-2 divide-y divide-line">
                {topic.lessons.map((lesson) => (
                  <li key={lesson.id} className="py-2.5">
                    <a href={`/student/lessons/${lesson.id}`} className="font-medium">
                      {lesson.title}
                    </a>
                    {lesson.is_enrichment && (
                      <span className="badge ml-2 bg-wash text-muted">Enrichment</span>
                    )}
                  </li>
                ))}
              </ol>
            )}
            {(assessments[topic.id] || []).length > 0 && (
              <div className="mt-4">
                <h3 className="text-sm font-semibold">Assessments</h3>
                <ol className="mt-1 divide-y divide-line">
                  {(assessments[topic.id] || []).map((a) => {
                    const mine = attempts[a.id] || [];
                    const active = mine.find((x) => x.status === "in_progress");
                    const done = mine.some((x) => x.status !== "in_progress");
                    return (
                      <li key={a.id} className="flex items-center justify-between py-2.5">
                        <span className="font-medium">{a.title}</span>
                        <span className="flex items-center gap-3 text-sm">
                          {active ? (
                            <span className="text-muted">In progress</span>
                          ) : done ? (
                            <span className="text-muted">Submitted</span>
                          ) : null}
                          <a href={`/student/assessments/${a.id}/take`}>
                            {active ? "Continue" : done ? "Start again" : "Start"}
                          </a>
                        </span>
                      </li>
                    );
                  })}
                </ol>
              </div>
            )}
          </section>
        ))
      )}
    </div>
  );
}
