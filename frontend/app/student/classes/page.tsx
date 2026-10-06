"use client";

import { useEffect, useState } from "react";
import DataTable from "@/components/DataTable";
import { FormError } from "@/components/forms";
import { ApiError, getClassList, type ClassItem } from "@/lib/api";

export default function StudentClassesPage() {
  const [classes, setClasses] = useState<ClassItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getClassList()
      .then(setClasses)
      .catch((e) =>
        setError(e instanceof ApiError ? e.message : "Could not load your classes.")
      )
      .finally(() => setLoading(false));
  }, []);

  return (
    <div>
      <h1 className="mb-1 text-xl font-semibold">My classes</h1>
      <p className="mb-6 text-sm text-muted">
        Classes you are enrolled in. Open a class to see its course outline.
      </p>
      <FormError message={error} />
      {loading ? (
        <p className="text-sm text-muted">Loading...</p>
      ) : (
        <DataTable
          columns={[
            {
              key: "name",
              header: "Class",
              render: (c) => (
                <a href={`/student/classes/${c.id}`} className="font-medium">
                  {c.name}
                </a>
              ),
            },
            { key: "year", header: "Year", render: (c) => c.academic_year },
            {
              key: "course",
              header: "Course",
              render: (c) => c.course_title || <span className="text-muted">-</span>,
            },
            { key: "teacher", header: "Teacher", render: (c) => c.teacher_name || "-" },
          ]}
          rows={classes}
          emptyMessage="You are not enrolled in any class yet."
        />
      )}
    </div>
  );
}
