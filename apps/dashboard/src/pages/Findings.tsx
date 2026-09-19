import type { AnalyticsFindings } from "@gitea-pr-manager/shared-types";
import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { PageHeader } from "../components/PageHeader";
import { AnimatedBarChart, CHART, ChartCard, severityFill } from "../components/charts";
import { exportPdf } from "../lib/pdf";

export function FindingsPage() {
  const [data, setData] = useState<AnalyticsFindings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.findings().then(setData).catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!data) return <p className="text-slate-500">Loading findings…</p>;

  return (
    <section className="space-y-6">
      <PageHeader
        title="Findings"
        description="Pattern analysis across repositories. This is not a developer scoreboard."
        onExport={() =>
          exportPdf({
            title: "Findings",
            subtitle: "Pattern analysis across repositories",
            tables: [
              {
                title: "By severity",
                headers: ["Severity", "Count"],
                rows: data.by_severity.map((item) => [item.severity, item.count]),
              },
              {
                title: "By category",
                headers: ["Category", "Count"],
                rows: data.by_category.map((item) => [item.category, item.count]),
              },
              {
                title: "Common violated rules",
                headers: ["Rule", "Count"],
                rows: data.common_violated_rules.map((item) => [item.rule, item.count]),
              },
              {
                title: "Recurring modules",
                headers: ["Path", "Count"],
                rows: data.recurring_modules.map((item) => [item.path, item.count]),
              },
            ],
          })
        }
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="By severity">
          <AnimatedBarChart
            data={data.by_severity}
            xKey="severity"
            yKey="count"
            color={CHART.amber}
            colorBy={Object.fromEntries(data.by_severity.map((item) => [item.severity, severityFill(item.severity)]))}
          />
        </ChartCard>
        <ChartCard title="By category">
          <AnimatedBarChart data={data.by_category} xKey="category" yKey="count" color={CHART.teal} />
        </ChartCard>
        <RankedList title="Common violated rules" rows={data.common_violated_rules.map((item) => [item.rule, item.count])} />
        <RankedList
          title="Modules with recurring problems"
          rows={data.recurring_modules.map((item) => [item.path, item.count])}
        />
      </div>
    </section>
  );
}

function RankedList({ title, rows }: { title: string; rows: Array<[string, number]> }) {
  const max = useMemo(() => Math.max(1, ...rows.map(([, count]) => count)), [rows]);
  return (
    <article className="animate-fade-up rounded-2xl border border-slate-200/80 bg-white p-5">
      <h2 className="mb-4 text-sm font-semibold tracking-tight text-slate-800">{title}</h2>
      <ul className="space-y-3 text-sm">
        {rows.length === 0 ? <li className="text-slate-500">No data yet.</li> : null}
        {rows.map(([label, count], index) => (
          <li key={label}>
            <div className="mb-1 flex justify-between gap-4">
              <span className="truncate text-slate-700">{label}</span>
              <span className="font-medium text-slate-900">{count}</span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-teal-600 origin-left animate-bar-grow"
                style={{ width: `${Math.round((count / max) * 100)}%`, animationDelay: `${index * 80}ms` }}
              />
            </div>
          </li>
        ))}
      </ul>
    </article>
  );
}
