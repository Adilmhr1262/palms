"use client";

import { use, useEffect, useState } from "react";
import LessonDocument from "@/components/LessonDocument";
import { FormError } from "@/components/forms";
import {
  ApiError,
  completeLesson,
  getLesson,
  type LessonDetail,
} from "@/lib/api";

export default function StudentLessonPage({
  params,
}: {
  params: Promise<{ lessonId: string }>;
}) {
  const { lessonId } = use(params);
  const id = parseInt(lessonId, 10);
  const [lesson, setLesson] = useState<LessonDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLesson(id)
      .then(setLesson)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load the lesson.")
      )
      .finally(() => setLoading(false));
  }, [id]);

  const [completed, setCompleted] = useState(false);
  const [saving, setSaving] = useState(false);

  if (loading) return <p className="text-sm text-muted">Loading...</p>;
  if (!lesson) return <FormError message={error || "Lesson not found."} />;
  return (
    <div className="mx-auto max-w-3xl">
      <LessonDocument lesson={lesson} />
      <div className="mt-6 border-t border-line pt-4">
        {completed ? (
          <p className="text-sm text-muted">Marked as complete.</p>
        ) : (
          <button
            type="button"
            className="btn"
            disabled={saving}
            onClick={async () => {
              setSaving(true);
              try {
                await completeLesson(id);
                setCompleted(true);
              } catch (e) {
                setError(
                  e instanceof ApiError ? e.message : "Could not mark complete."
                );
              } finally {
                setSaving(false);
              }
            }}
          >
            {saving ? "Saving..." : "Mark as complete"}
          </button>
        )}
      </div>
    </div>
  );
}
