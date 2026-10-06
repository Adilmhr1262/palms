type Column<T> = {
  key: string;
  header: string;
  render: (row: T) => React.ReactNode;
};

export default function DataTable<T>({
  columns,
  rows,
  emptyMessage = "No records found.",
}: {
  columns: Column<T>[];
  rows: T[];
  emptyMessage?: string;
}) {
  if (rows.length === 0) {
    return <p className="py-8 text-center text-sm text-muted">{emptyMessage}</p>;
  }
  return (
    <table className="data-table">
      <thead>
        <tr>
          {columns.map((c) => (
            <th key={c.key}>{c.header}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={(row as { id?: number | string }).id ?? i}>
            {columns.map((c) => (
              <td key={c.key}>{c.render(row)}</td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
