import { useEffect, useState } from "react";
import type { RepositoryStats } from "@gitea-pr-manager/shared-types";
import { api } from "../api";
import { AnimatedBarChart, CHART, ChartCard } from "../components/charts";

export function RepositoriesPage() {
  const [items, setItems] = useState<RepositoryStats[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.repositories().then(setItems).catch((err: Error) => setError(err.message));
  }, []);

  const chartData = items.map((item) => ({
    repository: shortRepo(item.repository),
    reviews: item.reviews,
    high_risk: item.high_risk,
  }));

  return (
    <section className="space-y-6">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-semibold tracking-tight">Repositories</h1>
        <p className="mt-1 text-sm text-slate-500">Review volume and risk by repository.</p>
      </div>
      {error ? <p className="text-red-700">{error}</p> : null}
      <ChartCard title="Reviews by repository">
        <AnimatedBarChart data={chartData} xKey="repository" yKey="reviews" color={CHART.teal} />
      </ChartCard>
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Repository</th>
              <th className="px-4 py-3 font-medium">PRs</th>
              <th className="px-4 py-3 font-medium">Reviews</th>
              <th className="px-4 py-3 font-medium">Merged</th>
              <th className="px-4 py-3 font-medium">High risk</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.repository} className="border-t border-slate-100 transition-colors hover:bg-slate-50/80">
                <td className="px-4 py-3 font-medium">{item.repository}</td>
                <td className="px-4 py-3">{item.prs}</td>
                <td className="px-4 py-3">{item.reviews}</td>
                <td className="px-4 py-3">{item.merged}</td>
                <td className="px-4 py-3">{item.high_risk}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function shortRepo(name: string) {
  const parts = name.split("/");
  return parts[parts.length - 1] || name;
}
