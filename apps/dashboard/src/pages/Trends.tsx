import type { AnalyticsFindings, AnalyticsTrends } from "@gitea-pr-manager/shared-types";
import { useEffect, useState } from "react";
import { api } from "../api";
import { PageHeader } from "../components/PageHeader";
import { AnimatedAreaChart, CHART, ChartCard, DualAreaChart } from "../components/charts";
import { exportPdf } from "../lib/pdf";

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
      <PageHeader
        title="Trends"
        description="Review throughput, size, merge time, and findings over time."
        onExport={() =>
          exportPdf({
            title: "Trends",
            subtitle: "Review throughput, size, merge time, and findings over time",
            tables: [
              {
                title: "Reviews over time",
                headers: ["Date", "Reviews"],
                rows: trends.reviews_over_time.map((item) => [item.date, item.count]),
              },
              {
                title: "PR size trend",
                headers: ["Date", "Average lines"],
                rows: trends.pr_size_trend.map((item) => [item.date, item.average_lines]),
              },
              {
                title: "Merge time trend",
                headers: ["Date", "Average seconds"],
                rows: trends.merge_time_trend.map((item) => [item.date, item.average_seconds]),
              },
              {
                title: "Findings over time",
                headers: ["Date", "Severity", "Count"],
                rows: findings.over_time.map((item) => [item.date, item.severity, item.count]),
              },
            ],
          })
        }
      />
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
