import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsFindings, AnalyticsTrends } from "@gitea-pr-manager/shared-types";
import { api } from "../api";

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
  if (!trends || !findings) return <p>Loading trends…</p>;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Trends</h1>
        <p className="mt-1 text-sm text-slate-500">Review throughput, size, merge time, and findings over time.</p>
      </div>
      <article className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-sm font-semibold">Findings over time</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={findings.over_time}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#0f766e" />
          </LineChart>
        </ResponsiveContainer>
      </article>
      <article className="rounded-xl border border-slate-200 bg-white p-4">
        <h2 className="mb-4 text-sm font-semibold">Reviews over time</h2>
        <ResponsiveContainer width="100%" height={280}>
          <LineChart data={trends.reviews_over_time}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#0369a1" />
          </LineChart>
        </ResponsiveContainer>
      </article>
    </section>
  );
}
