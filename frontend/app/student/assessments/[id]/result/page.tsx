"use client";

import Link from "next/link";
import { use, useEffect, useState } from "react";
import { FormError } from "@/components/forms";
import {
  ApiError,
  getAssessment,
  getAttempt,
  getMyAttempts,
  type AssessmentDetail,
  type Attempt,
  type AttemptDetail,
  type QuestionPublic,
} from "@/lib/api";

const PENDING_NOTICE = "Short answer responses are awaiting teacher review.";

export default function AssessmentResultPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const aid = Number(id);
  const [meta, setMeta] = useState<AssessmentDetail | null>(null);
  const [latest, setLatest] = useState<Attempt | null>(null);
  const [detail, setDetail] = useState<AttemptDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [m, history] = await Promise.all([
          getAssessment(aid),
          getMyAttempts(aid),
        ]);
        setMeta(m);
        if (history.length) {
          const last = history[0];
          setLatest(last);
          setDetail(await getAttempt(last.id));
        }
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Could not load the result.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [aid]);

  if (loading) return <p className="text-sm text-muted">Loading result.</p>;
  if (error) return <FormError message={error} />;

  if (!latest || !detail) {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="text-xl font-semibold">{meta?.title}</h1>
        <p className="mt-4 text-sm text-muted">
          You have not attempted this assessment yet.
        </p>
        <Link href={`/student/assessments/${aid}/take`} className="mt-4 inline-block">
          Start assessment
        </Link>
      </div>
    );
  }

  if (latest.status === "in_progress") {
    return (
      <div className="mx-auto max-w-2xl">
        <h1 className="text-xl font-semibold">{meta?.title}</h1>
        <p className="mt-4 text-sm text-muted">
          This attempt is still in progress.
        </p>
        <Link href={`/student/assessments/${aid}/take`} className="mt-4 inline-block">
          Continue assessment
        </Link>
      </div>
    );
  }

  const byQuestion = new Map(detail.answers.map((a) => [a.question_id, a]));
  const graded = detail.status === "graded";
  const pendingShort = detail.questions.some((q) => {
    const a = byQuestion.get(q.id);
    return q.qtype === "short_answer" && (!a || a.points_earned === null);
  });
  const percent =
    graded && detail.total_score !== null && detail.max_score
      ? Math.round((detail.total_score / detail.max_score) * 100)
      : null;

  function answerText(q: QuestionPublic): string {
    const a = byQuestion.get(q.id);
    if (!a) return "No answer given.";
    if (q.qtype === "short_answer") {
      return a.student_text && a.student_text.trim()
        ? a.student_text
        : "No answer given.";
    }
    if (a.selected_option === null || a.selected_option === undefined) {
      return "No answer given.";
    }
    if (q.qtype === "true_false") {
      return a.selected_option === 0 ? "True" : "False";
    }
    return q.options?.[a.selected_option] ?? "No answer given.";
  }

  return (
    <div className="mx-auto max-w-2xl">
      <p className="mb-4 text-sm text-muted">
        <Link href="/student/classes">My classes</Link> / Result
      </p>
      <h1 className="text-xl font-semibold">{detail.assessment_title}</h1>
      <p className="mt-1 text-sm text-muted">
        Submitted{" "}
        {detail.submitted_at
          ? new Date(detail.submitted_at).toLocaleString()
          : "recently"}
      </p>

      <div className="mt-6 rounded border border-line p-5">
        {graded && detail.total_score !== null ? (
          <div className="flex items-baseline justify-between">
            <span className="text-sm text-muted">Score</span>
            <span className="text-lg font-semibold">
              {detail.total_score} of {detail.max_score}
              {percent !== null && (
                <span className="ml-2 text-sm font-normal text-muted">
                  ({percent}%)
                </span>
              )}
            </span>
          </div>
        ) : (
          <p className="text-sm">
            Submitted. Marking is in progress.
          </p>
        )}
        {pendingShort && (
          <p className="mt-3 text-sm text-warning">{PENDING_NOTICE}</p>
        )}
      </div>

      <h2 className="mb-2 mt-8 text-base font-semibold">Question review</h2>
      <ol className="divide-y divide-line rounded border border-line">
        {detail.questions.map((q, i) => {
          const a = byQuestion.get(q.id);
          const scored = a && a.points_earned !== null;
          return (
            <li key={q.id} className="p-5">
              <p className="font-serif">
                <span className="mr-2 text-sm text-muted">{i + 1}.</span>
                {q.prompt}
              </p>
              <div className="mt-3 text-sm">
                <p className="text-muted">Your answer</p>
                <p className="mt-1 font-serif">{answerText(q)}</p>
              </div>
              <div className="mt-3 flex items-center justify-between text-sm">
                <span className="text-muted">
                  {q.qtype === "short_answer" ? (
                    scored ? (
                      <span>
                        {a.points_earned} of {q.points} points
                      </span>
                    ) : (
                      <span className="text-warning">Awaiting teacher review</span>
                    )
                  ) : scored ? (
                    <span>
                      {a.is_correct ? "Correct" : "Incorrect"} - {a.points_earned}{" "}
                      of {q.points} points
                    </span>
                  ) : (
                    <span className="text-muted">Not marked yet</span>
                  )}
                </span>
              </div>
              {a && a.teacher_comment && (
                <div className="mt-3 rounded bg-wash p-3 text-sm">
                  <p className="font-semibold">Teacher comment</p>
                  <p className="mt-1">{a.teacher_comment}</p>
                </div>
              )}
            </li>
          );
        })}
      </ol>

      <div className="mt-6">
        <Link href={`/student/assessments/${aid}/take`}>
          Start a new attempt
        </Link>
      </div>
    </div>
  );
}
