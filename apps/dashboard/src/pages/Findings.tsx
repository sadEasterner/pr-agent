import { useEffect, useState } from "react";
import type { AnalyticsFindings } from "@gitea-pr-manager/shared-types";
import { api } from "../api";

export function FindingsPage() {
  const [data, setData] = useState<AnalyticsFindings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.findings().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p>Loading findings…</p>;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Findings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Pattern analysis across repositories. This is not a developer scoreboard.
        </p>
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <Panel title="By severity" rows={data.by_severity.map((item) => [item.severity, item.count])} />
        <Panel title="By category" rows={data.by_category.map((item) => [item.category, item.count])} />
        <Panel
          title="Common violated rules"
          rows={data.common_violated_rules.map((item) => [item.rule, item.count])}
        />
        <Panel
          title="Modules with recurring problems"
          rows={data.recurring_modules.map((item) => [item.path, item.count])}
        />
      </div>
    </section>
  );
}

function Panel({ title, rows }: { title: string; rows: Array<[string, number]> }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-3 font-semibold">{title}</h2>
      <ul className="space-y-2 text-sm">
        {rows.length === 0 ? <li className="text-slate-500">No data yet.</li> : null}
        {rows.map(([label, count]) => (
          <li key={label} className="flex justify-between gap-4">
            <span className="truncate">{label}</span>
            <span className="font-medium">{count}</span>
          </li>
        ))}
      </ul>
    </article>
  );
}
