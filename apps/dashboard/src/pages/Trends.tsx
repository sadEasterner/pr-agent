import type { AnalyticsFindings, AnalyticsTrends } from "@gitea-pr-manager/shared-types";
import { useEffect, useState } from "react";
import { api } from "../api";
import { AnimatedAreaChart, CHART, ChartCard, DualAreaChart } from "../components/charts";

export function TrendsPage() {
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [findings, setFindings] = useState<AnalyticsFindings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.trends(), api.findings()])
      .then(([trendValue, findingValue]) => {
        setTrends(trendValue);
        setFindings(findingValue);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!trends || !findings) return <p className="text-slate-500">Loading trends…</p>;

  const combined = mergeByDate(trends.reviews_over_time, findings.over_time);

  return (
    <section className="space-y-6">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-semibold tracking-tight">Trends</h1>
        <p className="mt-1 text-sm text-slate-500">Review throughput, size, merge time, and findings over time.</p>
      </div>
      <ChartCard title="Reviews and findings" hint="Daily volume of completed reviews versus new findings">
        <DualAreaChart
          data={combined}
          xKey="date"
          series={[
            { key: "reviews", color: CHART.sky, label: "Reviews" },
            { key: "findings", color: CHART.orange, label: "Findings" },
          ]}
        />
      </ChartCard>
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="PR size trend" hint="Average changed lines">
          <AnimatedAreaChart
            data={trends.pr_size_trend}
            xKey="date"
            yKey="average_lines"
            color={CHART.teal}
            label="Lines"
          />
        </ChartCard>
        <ChartCard title="Merge time trend" hint="Average seconds to merge">
          <AnimatedAreaChart
            data={trends.merge_time_trend}
            xKey="date"
            yKey="average_seconds"
            color={CHART.violet}
            label="Seconds"
          />
        </ChartCard>
      </div>
    </section>
  );
}

function mergeByDate(
  reviews: Array<{ date: string; count: number }>,
  findings: Array<{ date: string; count: number }>,
) {
  const map = new Map<string, { date: string; reviews: number; findings: number }>();
  for (const item of reviews) {
    map.set(item.date, { date: item.date, reviews: item.count, findings: 0 });
  }
  for (const item of findings) {
    const current = map.get(item.date) ?? { date: item.date, reviews: 0, findings: 0 };
    current.findings = item.count;
    map.set(item.date, current);
  }
  return Array.from(map.values()).sort((a, b) => a.date.localeCompare(b.date));
}
