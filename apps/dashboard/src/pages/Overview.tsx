import { MetricCard } from "@gitea-pr-manager/ui";
import type { AnalyticsFindings, AnalyticsSummary, AnalyticsTrends } from "@gitea-pr-manager/shared-types";
import { useEffect, useState } from "react";
import { api, formatDuration } from "../api";
import { PageHeader } from "../components/PageHeader";
import {
  AnimatedAreaChart,
  AnimatedBarChart,
  AnimatedDonutChart,
  CHART,
  ChartCard,
  severityFill,
} from "../components/charts";
import { exportPdf } from "../lib/pdf";

export function OverviewPage() {
  const [summary, setSummary] = useState<AnalyticsSummary | null>(null);
  const [trends, setTrends] = useState<AnalyticsTrends | null>(null);
  const [findings, setFindings] = useState<AnalyticsFindings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.summary(), api.trends(), api.findings()])
      .then(([summaryValue, trendsValue, findingsValue]) => {
        setSummary(summaryValue);
        setTrends(trendsValue);
        setFindings(findingsValue);
      })
      .catch((err: Error) => setError(err.message));
  }, []);

  if (!summary || !trends || !findings) {
    return (
      <section className="space-y-8">
        <PageHeader
          title="Overview"
          description="Engineering process metrics. AI recommendations never authorize a merge."
        />
        {error ? (
          <p className="text-red-700">Unable to load overview: {error}</p>
        ) : (
          <p className="text-slate-500">Loading overview…</p>
        )}
      </section>
    );
  }

  return (
    <section className="space-y-8">
      <PageHeader
        title="Overview"
        description="Engineering process metrics. AI recommendations never authorize a merge."
        onExport={() =>
          exportPdf({
            title: "Overview",
            subtitle: "Engineering process metrics. AI recommendations never authorize a merge.",
            metrics: [
              { label: "PRs reviewed", value: summary.prs_reviewed },
              { label: "Waiting for human review", value: summary.prs_waiting_for_human_review },
              { label: "High-risk PRs", value: summary.high_risk_prs },
              { label: "Average merge time", value: formatDuration(summary.average_merge_time_seconds) },
              { label: "Average PR size", value: `${Math.round(summary.average_pr_size_lines)} lines` },
              { label: "Findings this week", value: summary.findings_this_week },
            ],
            tables: [
              {
                title: "Findings by severity",
                headers: ["Severity", "Count"],
                rows: findings.by_severity.map((item) => [item.severity, item.count]),
              },
              {
                title: "Findings by category",
                headers: ["Category", "Count"],
                rows: findings.by_category.map((item) => [item.category, item.count]),
              },
              {
                title: "Risk distribution",
                headers: ["Risk", "Count"],
                rows: trends.risk_distribution.map((item) => [item.risk, item.count]),
              },
            ],
          })
        }
      />
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard label="PRs reviewed" value={summary.prs_reviewed} />
        <MetricCard
          label="PRs waiting for human review"
          value={summary.prs_waiting_for_human_review}
        />
        <MetricCard label="High-risk PRs" value={summary.high_risk_prs} />
        <MetricCard
          label="Average merge time"
          value={formatDuration(summary.average_merge_time_seconds)}
        />
        <MetricCard
          label="Average PR size"
          value={`${Math.round(summary.average_pr_size_lines)} lines`}
        />
        <MetricCard label="Findings this week" value={summary.findings_this_week} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="PR reviews over time" hint="Accepted reviews by day">
          <AnimatedAreaChart
            data={trends.reviews_over_time}
            xKey="date"
            yKey="count"
            color={CHART.teal}
            label="Reviews"
          />
        </ChartCard>
        <ChartCard title="Severity distribution" hint="Latest findings by severity">
          <AnimatedBarChart
            data={findings.by_severity}
            xKey="severity"
            yKey="count"
            color={CHART.amber}
            colorBy={Object.fromEntries(findings.by_severity.map((item) => [item.severity, severityFill(item.severity)]))}
          />
        </ChartCard>
        <ChartCard title="Common finding categories">
          <AnimatedBarChart
            data={findings.by_category}
            xKey="category"
            yKey="count"
            color={CHART.teal}
          />
        </ChartCard>
        <ChartCard title="Risk distribution" hint="Share of reviewed PRs">
          <AnimatedDonutChart data={trends.risk_distribution} nameKey="risk" valueKey="count" />
        </ChartCard>
        <ChartCard title="PR size trend" hint="Average changed lines">
          <AnimatedAreaChart
            data={trends.pr_size_trend}
            xKey="date"
            yKey="average_lines"
            color={CHART.sky}
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
