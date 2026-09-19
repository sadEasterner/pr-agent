import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { StatusBadge } from "@gitea-pr-manager/ui";
import type { AuthorDetail } from "@gitea-pr-manager/shared-types";
import { api } from "../api";
import { PageHeader } from "../components/PageHeader";
import { AnimatedBarChart, CHART, ChartCard } from "../components/charts";
import { authorLabel } from "../lib/names";
import { exportPdf } from "../lib/pdf";

export function PersonDetailPage() {
  const params = useParams();
  const author = params.author ? decodeURIComponent(params.author) : "";
  const [item, setItem] = useState<AuthorDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!author) return;
    api.author(author).then(setItem).catch((err: Error) => setError(err.message));
  }, [author]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!item) return <p className="text-slate-500">Loading person…</p>;

  const name = authorLabel(item.author, item.display_name);

  return (
    <section className="space-y-6">
      <Link to="/people" className="text-sm text-slate-500 hover:text-slate-800">
        ← People
      </Link>
      <PageHeader
        title={name}
        description="How this author's pull requests were reviewed: findings, re-reviews, and risk."
        onExport={() =>
          exportPdf({
            title: name,
            subtitle: `Pull request review history for ${item.author}`,
            metrics: [
              { label: "PRs", value: item.prs },
              { label: "PRs with findings", value: item.prs_with_mistakes },
              { label: "Findings", value: item.findings },
              { label: "Changes requested", value: item.changes_requested },
              { label: "High risk", value: item.high_risk },
              { label: "Review rounds", value: item.review_rounds },
            ],
            tables: [
              {
                title: "Findings by category",
                headers: ["Category", "Count"],
                rows: item.by_category.map((row) => [row.category, row.count]),
              },
              {
                title: "Pull requests",
                headers: ["PR", "Repository", "Status", "Findings", "Risk"],
                rows: item.pull_requests.map((pr) => [
                  `#${pr.number} ${pr.title}`,
                  pr.repository,
                  pr.human_review_status,
                  pr.findings_count,
                  pr.latest_risk ?? "—",
                ]),
              },
            ],
          })
        }
      />
      <div className="grid gap-4 md:grid-cols-3">
        <Stat label="PRs" value={item.prs} />
        <Stat label="PRs with findings" value={item.prs_with_mistakes} />
        <Stat label="Findings" value={item.findings} />
        <Stat label="Changes requested" value={item.changes_requested} />
        <Stat label="High risk" value={item.high_risk} />
        <Stat label="Review rounds" value={item.review_rounds} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard title="Finding categories">
          <AnimatedBarChart data={item.by_category} xKey="category" yKey="count" color={CHART.teal} />
        </ChartCard>
        <ChartCard title="Finding severity">
          <AnimatedBarChart data={item.by_severity} xKey="severity" yKey="count" color={CHART.amber} />
        </ChartCard>
      </div>
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">Pull request</th>
              <th className="px-4 py-3 font-medium">Repository</th>
              <th className="px-4 py-3 font-medium">Findings</th>
              <th className="px-4 py-3 font-medium">Status</th>
            </tr>
          </thead>
          <tbody>
            {item.pull_requests.map((pr) => (
              <tr key={pr.id} className="border-t border-slate-100 hover:bg-slate-50/80">
                <td className="px-4 py-3">
                  <Link
                    className="font-medium text-slate-900 hover:text-teal-700 hover:underline"
                    to={`/pull-requests/${pr.repository}/${pr.number}`}
                  >
                    #{pr.number} {pr.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-600">{pr.repository}</td>
                <td className="px-4 py-3">{pr.findings_count}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={pr.human_review_status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white px-4 py-3">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold text-slate-900">{value}</p>
    </article>
  );
}
