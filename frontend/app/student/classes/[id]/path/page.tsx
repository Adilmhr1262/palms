"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { FormError } from "@/components/forms";
import {
  ApiError,
  getLearningPath,
  MASTERY_STATUS_LABELS,
  type LearningPath,
} from "@/lib/api";

export default function LearningPathPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const classId = parseInt(id, 10);
  const [path, setPath] = useState<LearningPath | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getLearningPath(classId)
      .then(setPath)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load the learning path.")
      )
      .finally(() => setLoading(false));
  }, [classId]);

  if (loading) return <p className="text-sm text-muted">Loading learning path.</p>;
  if (error) return <FormError message={error} />;
  if (!path) return null;

  const current = path.current_activity;

  return (
    <div className="mx-auto max-w-3xl">
      <p className="mb-4 text-sm text-muted">
        <Link href="/student/classes">My classes</Link> /{" "}
        <Link href={`/student/classes/${path.class_id}`}>{path.class_name}</Link> /{" "}
        Learning path
      </p>
      <h1 className="text-xl font-semibold">Learning path</h1>
      <p className="mt-1 text-sm text-muted">{path.course_title}</p>

      {current && (
        <section className="mt-6 rounded border border-line p-5">
          <h2 className="text-base font-semibold">Current recommended activity</h2>
          <p className="mt-2 font-semibold">{current.title}</p>
          <p className="mt-1 text-sm text-muted">{current.message}</p>
          <p className="mt-2 text-sm">
            <span className="text-muted">Reason: </span>
            {current.reason}
          </p>
          <p className="mt-3">
            <Link href="/student/recommendations">View all recommendations</Link>
          </p>
        </section>
      )}

      <ol className="mt-8">
        {path.topics.map((topic, i) => {
          const isNext = topic.id === path.next_topic_id;
          const done = topic.lessons.filter((l) => l.completed).length;
          return (
            <li key={topic.id} className="border-t border-line py-5">
              <div className="flex items-baseline justify-between">
                <h2 className="text-base font-semibold">
                  <span className="mr-2 text-sm font-normal text-muted">{i + 1}.</span>
                  {topic.title}
                </h2>
                {isNext && (
                  <span className="text-sm font-semibold">Next available topic</span>
                )}
              </div>
              <p className="mt-1 text-sm text-muted">
                {topic.mastery_status
                  ? `Mastery: ${MASTERY_STATUS_LABELS[topic.mastery_status]}`
                  : "Not attempted yet"}
                {topic.latest_score !== null &&
                  ` - latest ${Math.round(topic.latest_score)}%`}
                {` - ${done} of ${topic.lessons.length} lessons complete`}
              </p>
              <ul className="mt-3 list-none pl-0">
                {topic.lessons.map((lesson) => (
                  <li key={lesson.id} className="py-1 text-sm">
                    <Link href={`/student/lessons/${lesson.id}`}>{lesson.title}</Link>
                    {lesson.completed && (
                      <span className="ml-2 text-muted">- complete</span>
                    )}
                  </li>
                ))}
              </ul>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
