"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { use, useEffect, useRef, useState } from "react";
import { useConfirm } from "@/components/ConfirmDialog";
import { FormError, TextArea } from "@/components/forms";
import {
  ApiError,
  getAssessment,
  getAttempt,
  getMyAttempts,
  saveAnswer,
  startAttempt,
  submitAttempt,
  type Answer,
  type AssessmentDetail,
  type Attempt,
  type AttemptDetail,
  type QuestionPublic,
} from "@/lib/api";

type AnswerState = { selected_option: number | null; student_text: string };

function blankAnswers(answers: Answer[]): Record<number, AnswerState> {
  const map: Record<number, AnswerState> = {};
  for (const a of answers) {
    map[a.question_id] = {
      selected_option: a.selected_option,
      student_text: a.student_text || "",
    };
  }
  return map;
}

function isAnswered(a: AnswerState | undefined): boolean {
  if (!a) return false;
  return a.selected_option !== null || a.student_text.trim() !== "";
}

export default function TakeAssessmentPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const aid = Number(id);
  const router = useRouter();
  const [meta, setMeta] = useState<AssessmentDetail | null>(null);
  const [history, setHistory] = useState<Attempt[]>([]);
  const [attempt, setAttempt] = useState<AttemptDetail | null>(null);
  const [answers, setAnswers] = useState<Record<number, AnswerState>>({});
  const [index, setIndex] = useState(0);
  const [reviewing, setReviewing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedTick, setSavedTick] = useState(false);
  const confirm = useConfirm();
  const pendingText = useRef<{ questionId: number; text: string } | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [m, h] = await Promise.all([getAssessment(aid), getMyAttempts(aid)]);
        setMeta(m);
        setHistory(h);
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Could not load the assessment.");
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [aid]);

  async function begin() {
    setError(null);
    try {
      const a = await startAttempt(aid);
      if (a.status !== "in_progress") {
        router.push(`/student/assessments/${aid}/result`);
        return;
      }
      setAttempt(a);
      setAnswers(blankAnswers(a.answers));
      setIndex(0);
      setReviewing(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not start the assessment.");
    }
  }

  async function continueAttempt(attemptId: number) {
    setError(null);
    try {
      const a = await getAttempt(attemptId);
      setAttempt(a);
      setAnswers(blankAnswers(a.answers));
      setIndex(0);
      setReviewing(false);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not resume the assessment.");
    }
  }

  function markSaved() {
    setSavedTick(true);
    window.setTimeout(() => setSavedTick(false), 1500);
  }

  async function persist(questionId: number, state: AnswerState) {
    if (!attempt) return;
    setSaveError(null);
    try {
      const q = attempt.questions.find((x) => x.id === questionId);
      await saveAnswer(attempt.id, {
        question_id: questionId,
        selected_option: q?.qtype === "short_answer" ? null : state.selected_option,
        student_text: q?.qtype === "short_answer" ? state.student_text || null : null,
      });
      markSaved();
    } catch (e) {
      setSaveError(e instanceof ApiError ? e.message : "Could not save the answer.");
    }
  }

  function flushPending() {
    if (pendingText.current) {
      const { questionId, text } = pendingText.current;
      pendingText.current = null;
      return persist(questionId, { selected_option: null, student_text: text });
    }
    return Promise.resolve();
  }

  async function chooseOption(q: QuestionPublic, option: number) {
    const state = { selected_option: option, student_text: "" };
    setAnswers((m) => ({ ...m, [q.id]: state }));
    await persist(q.id, state);
  }

  function typeText(q: QuestionPublic, text: string) {
    setAnswers((m) => ({ ...m, [q.id]: { selected_option: null, student_text: text } }));
    pendingText.current = { questionId: q.id, text };
  }

  async function blurText(q: QuestionPublic) {
    await flushPending();
  }

  async function goTo(i: number) {
    await flushPending();
    setIndex(i);
    setReviewing(false);
  }

  async function openReview() {
    await flushPending();
    setReviewing(true);
  }

  function doSubmit() {
    if (!attempt) return;
    confirm.ask(
      "Submit assessment",
      "Submit your answers? You cannot change them after submitting.",
      async () => {
        try {
          await submitAttempt(attempt.id);
          router.push(`/student/assessments/${aid}/result`);
        } catch (e) {
          setError(e instanceof ApiError ? e.message : "Could not submit the assessment.");
        }
      },
      "Submit"
    );
  }

  if (loading) return <p className="text-sm text-muted">Loading assessment.</p>;
  if (error && !meta) return <FormError message={error} />;

  // Intro screen: instructions and start/continue.
  if (!attempt || !meta) {
    const active = history.find((h) => h.status === "in_progress");
    return (
      <div className="mx-auto max-w-2xl">
        <p className="mb-4 text-sm text-muted">
          <Link href="/student/classes">My classes</Link> / Assessment
        </p>
        <h1 className="text-xl font-semibold">{meta?.title || "Assessment"}</h1>
        {meta?.instructions && (
          <div className="mt-4 rounded border border-line bg-wash p-5">
            <h2 className="mb-2 text-sm font-semibold">Instructions</h2>
            <p className="whitespace-pre-line text-sm">{meta.instructions}</p>
          </div>
        )}
        <FormError message={error} />
        <div className="mt-6">
          {active ? (
            <button className="btn-primary" onClick={() => continueAttempt(active.id)}>
              Continue assessment
            </button>
          ) : (
            <button className="btn-primary" onClick={begin}>
              {history.length ? "Start a new attempt" : "Start assessment"}
            </button>
          )}
        </div>
        {history.length > 0 && (
          <div className="mt-8">
            <h2 className="mb-2 text-sm font-semibold">Previous attempts</h2>
            <ul className="divide-y divide-line text-sm">
              {history.map((h) => (
                <li key={h.id} className="py-2">
                  <span className="capitalize text-muted">
                    {h.status.replace("_", " ")}
                  </span>
                  <span className="text-muted">
                    {" "}
                    - started {new Date(h.started_at).toLocaleString()}
                    {h.submitted_at &&
                      `, submitted ${new Date(h.submitted_at).toLocaleString()}`}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    );
  }

  const questions = attempt.questions;
  const q = questions[index];
  const state = answers[q.id];
  const answeredCount = questions.filter((x) => isAnswered(answers[x.id])).length;

  return (
    <div className="mx-auto max-w-2xl">
      <p className="mb-4 text-sm text-muted">
        <Link href="/student/classes">My classes</Link> / {attempt.assessment_title}
      </p>
      <div className="mb-2 flex items-baseline justify-between">
        <p className="text-sm text-muted">
          Question {index + 1} of {questions.length}
        </p>
        <p className="text-sm text-muted">
          {answeredCount} answered
          {savedTick && <span className="ml-3">Saved.</span>}
        </p>
      </div>
      <div className="mb-6 h-1 w-full bg-wash">
        <div
          className="h-1 bg-ink"
          style={{ width: `${((index + 1) / questions.length) * 100}%` }}
        />
      </div>
      <FormError message={saveError} />

      {!reviewing ? (
        <div>
          <p className="font-serif text-lg leading-relaxed">{q.prompt}</p>
          <p className="mt-1 text-sm text-muted">{q.points} points</p>

          <div className="mt-5">
            {(q.qtype === "mcq" || q.qtype === "true_false") && (
              <div>
                <p className="field-label">Choose one</p>
                <div className="space-y-2">
                  {(q.qtype === "mcq"
                    ? q.options || []
                    : ["True", "False"]
                  ).map((opt, i) => (
                    <label
                      key={i}
                      className={`flex cursor-pointer items-start gap-3 rounded border p-3.5 text-[15px] ${
                        state?.selected_option === i
                          ? "border-ink bg-wash"
                          : "border-line"
                      }`}
                    >
                      <input
                        type="radio"
                        name={`q-${q.id}`}
                        checked={state?.selected_option === i}
                        onChange={() => chooseOption(q, i)}
                        className="mt-1"
                      />
                      <span className={q.qtype === "true_false" ? "" : "font-serif"}>
                        {opt}
                      </span>
                    </label>
                  ))}
                </div>
              </div>
            )}
            {q.qtype === "short_answer" && (
              <div>
                <label className="field-label" htmlFor={`sa-${q.id}`}>
                  Your answer
                </label>
                <TextArea
                  id={`sa-${q.id}`}
                  rows={6}
                  value={state?.student_text || ""}
                  onChange={(e) => typeText(q, e.target.value)}
                  onBlur={() => blurText(q)}
                  placeholder="Write your answer here."
                  className="font-serif"
                />
                <p className="mt-1 text-[13px] text-muted">
                  Your answer is saved when you leave this box.
                </p>
              </div>
            )}
          </div>

          <div className="mt-8 flex items-center justify-between">
            <button
              className="btn-secondary"
              onClick={() => goTo(index - 1)}
              disabled={index === 0}
            >
              Previous
            </button>
            {index < questions.length - 1 ? (
              <button className="btn-primary" onClick={() => goTo(index + 1)}>
                Next
              </button>
            ) : (
              <button className="btn-primary" onClick={openReview}>
                Review answers
              </button>
            )}
          </div>
        </div>
      ) : (
        <div>
          <h2 className="mb-4 text-base font-semibold">Review your answers</h2>
          <ol className="divide-y divide-line">
            {questions.map((item, i) => {
              const a = answers[item.id];
              const done = isAnswered(a);
              return (
                <li key={item.id} className="flex items-center justify-between py-3">
                  <button
                    className="text-left font-serif underline-offset-2 hover:underline"
                    onClick={() => goTo(i)}
                  >
                    <span className="mr-2 text-sm text-muted">{i + 1}.</span>
                    {item.prompt.length > 90
                      ? item.prompt.slice(0, 90) + "."
                      : item.prompt}
                  </button>
                  <span
                    className={`ml-4 whitespace-nowrap text-sm ${
                      done ? "text-muted" : "text-warning"
                    }`}
                  >
                    {done ? "Answered" : "Not answered"}
                  </span>
                </li>
              );
            })}
          </ol>
          {answeredCount < questions.length && (
            <p className="mt-4 text-sm text-warning">
              {questions.length - answeredCount} question
              {questions.length - answeredCount === 1 ? " is" : "s are"} still
              unanswered. You can go back and answer{" "}
              {questions.length - answeredCount === 1 ? "it" : "them"}, or submit
              as is.
            </p>
          )}
          <div className="mt-6 flex items-center justify-between">
            <button className="btn-secondary" onClick={() => setReviewing(false)}>
              Back to questions
            </button>
            <button className="btn-primary" onClick={doSubmit}>
              Submit assessment
            </button>
          </div>
        </div>
      )}
      {confirm.dialog}
    </div>
  );
}
