import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { AuthorStats } from "@gitea-pr-manager/shared-types";
import { api } from "../api";
import { PageHeader } from "../components/PageHeader";
import { AnimatedBarChart, CHART, ChartCard } from "../components/charts";
import { authorLabel } from "../lib/names";
import { exportPdf } from "../lib/pdf";

export function PeoplePage() {
  const [items, setItems] = useState<AuthorStats[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.authors().then(setItems).catch((err: Error) => setError(err.message));
  }, []);

  const chartData = items.map((item) => ({
    name: authorLabel(item.author, item.display_name),
    findings: item.findings,
  }));

  return (
    <section className="space-y-6">
      <PageHeader
        title="People"
        description="Who opened each PR, how many reviews they needed, and how often findings showed up. This is process data, not a score."
        onExport={() =>
          exportPdf({
            title: "People",
            subtitle: "PR authors, review rounds, and findings",
            tables: [
              {
                headers: [
                  "Name",
                  "Login",
                  "PRs",
                  "Open",
                  "Merged",
                  "PRs with findings",
                  "Findings",
                  "Changes requested",
                  "High risk",
                  "Review rounds",
                ],
                rows: items.map((item) => [
                  item.display_name,
                  item.author,
                  item.prs,
                  item.open_prs,
                  item.merged,
                  item.prs_with_mistakes,
                  item.findings,
                  item.changes_requested,
                  item.high_risk,
                  item.review_rounds,
                ]),
              },
            ],
          })
        }
      />
      {error ? <p className="text-red-700">{error}</p> : null}
      <ChartCard title="Findings by author">
        <AnimatedBarChart data={chartData} xKey="name" yKey="findings" color={CHART.amber} />
      </ChartCard>
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Name</th>
              <th className="px-4 py-3 font-medium">PRs</th>
              <th className="px-4 py-3 font-medium">PRs with findings</th>
              <th className="px-4 py-3 font-medium">Findings</th>
              <th className="px-4 py-3 font-medium">Changes requested</th>
              <th className="px-4 py-3 font-medium">High risk</th>
              <th className="px-4 py-3 font-medium">Review rounds</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.author} className="border-t border-slate-100 transition-colors hover:bg-slate-50/80">
                <td className="px-4 py-3">
                  <Link
                    className="font-medium text-slate-900 hover:text-teal-700 hover:underline"
                    to={`/people/${encodeURIComponent(item.author)}`}
                  >
                    {authorLabel(item.author, item.display_name)}
                  </Link>
                </td>
                <td className="px-4 py-3">{item.prs}</td>
                <td className="px-4 py-3">{item.prs_with_mistakes}</td>
                <td className="px-4 py-3">{item.findings}</td>
                <td className="px-4 py-3">{item.changes_requested}</td>
                <td className="px-4 py-3">{item.high_risk}</td>
                <td className="px-4 py-3">{item.review_rounds}</td>
              </tr>
            ))}
            {items.length === 0 ? (
              <tr>
                <td className="px-4 py-6 text-slate-500" colSpan={7}>
                  No reviewed pull requests yet.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
    </section>
  );
}
