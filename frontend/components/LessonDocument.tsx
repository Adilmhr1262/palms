import type { LessonDetail, ResourceItem } from "@/lib/api";

function formatSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function ResourceList({ resources }: { resources: ResourceItem[] }) {
  if (resources.length === 0) {
    return <p className="text-sm text-muted">No files attached to this lesson.</p>;
  }
  return (
    <ul className="divide-y divide-line border-y border-line">
      {resources.map((r) => (
        <li key={r.id} className="flex items-baseline justify-between gap-4 py-2.5">
          <a href={`/api/proxy/resources/${r.id}/download`}>{r.file_name}</a>
          <span className="shrink-0 text-xs text-muted">
            {formatSize(r.size_bytes)}
          </span>
        </li>
      ))}
    </ul>
  );
}

export default function LessonDocument({ lesson }: { lesson: LessonDetail }) {
  return (
    <article>
      <nav className="mb-6 text-[13px] text-muted">
        <a href="/student/classes" className="no-underline">
          My classes
        </a>
        {" / "}
        <span>{lesson.course_title}</span>
        {" / "}
        <span>{lesson.topic_title}</span>
      </nav>
      <h1 className="font-serif text-[28px] font-semibold leading-snug">
        {lesson.title}
      </h1>
      {lesson.objectives && (
        <section className="mt-6">
          <h2 className="text-sm font-semibold uppercase tracking-wider text-muted">
            Learning objectives
          </h2>
          <div className="mt-2 whitespace-pre-line font-serif text-[16px]">
            {lesson.objectives}
          </div>
        </section>
      )}
      {lesson.body && (
        <section className="mt-6">
          <div className="whitespace-pre-line font-serif text-[16px] leading-[1.75]">
            {lesson.body}
          </div>
        </section>
      )}
      <section className="mt-8">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wider text-muted">
          Resources
        </h2>
        <ResourceList resources={lesson.resources} />
      </section>
    </article>
  );
}
