import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { MetricCard } from "@gitea-pr-manager/ui";
import { api, formatDuration } from "../api";
import type { AnalyticsSummary, AnalyticsTrends, AnalyticsFindings } from "@gitea-pr-manager/shared-types";

const COLORS = ["#0f766e", "#d97706", "#ea580c", "#b91c1c", "#64748b"];

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

  if (error) return <p className="text-red-700">Unable to load overview: {error}</p>;
  if (!summary || !trends || !findings) return <p>Loading overview…</p>;

  return (
    <section className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold">Overview</h1>
        <p className="mt-1 text-sm text-slate-500">
          Engineering process metrics. AI recommendations never authorize a merge.
        </p>
      </div>
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
        <ChartCard title="PR reviews over time">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trends.reviews_over_time}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Line type="monotone" dataKey="count" stroke="#0f766e" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Severity distribution">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={findings.by_severity}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="severity" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#d97706" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Common finding categories">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={findings.by_category}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="category" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#0f766e" />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Risk distribution">
          <ResponsiveContainer width="100%" height={260}>
            <PieChart>
              <Pie data={trends.risk_distribution} dataKey="count" nameKey="risk" outerRadius={90} label>
                {trends.risk_distribution.map((entry, index) => (
                  <Cell key={entry.risk} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Legend />
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="PR size trend">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trends.pr_size_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="average_lines" stroke="#0369a1" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
        <ChartCard title="Merge time trend">
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={trends.merge_time_trend}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" />
              <YAxis />
              <Tooltip />
              <Line type="monotone" dataKey="average_seconds" stroke="#7c3aed" />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>
    </section>
  );
}

function ChartCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 className="mb-4 text-sm font-semibold text-slate-700">{title}</h2>
      {children}
    </article>
  );
}
