import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { RiskBadge, StatusBadge } from "@gitea-pr-manager/ui";
import type { PullRequestSummary } from "@gitea-pr-manager/shared-types";
import { api } from "../api";

export function PullRequestsPage() {
  const [items, setItems] = useState<PullRequestSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState({
    repository: "",
    risk: "",
    status: "",
    author: "",
    finding_severity: "",
  });

  useEffect(() => {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value),
    );
    api
      .pullRequests(params)
      .then(setItems)
      .catch((err: Error) => setError(err.message));
  }, [filters]);

  const repositories = useMemo(
    () => Array.from(new Set(items.map((item) => item.repository))),
    [items],
  );

  return (
    <section className="space-y-6">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-semibold tracking-tight">Pull Requests</h1>
        <p className="mt-1 text-sm text-slate-500">
          Review status is an AI recommendation, not an approval.
        </p>
      </div>
      <div className="grid gap-3 rounded-2xl border border-slate-200/80 bg-white p-4 md:grid-cols-5">
        <Filter
          label="Repository"
          value={filters.repository}
          onChange={(value) => setFilters((current) => ({ ...current, repository: value }))}
          options={repositories}
        />
        <Filter
          label="Risk"
          value={filters.risk}
          onChange={(value) => setFilters((current) => ({ ...current, risk: value }))}
          options={["low", "medium", "high", "critical"]}
        />
        <Filter
          label="Status"
          value={filters.status}
          onChange={(value) => setFilters((current) => ({ ...current, status: value }))}
          options={["waiting_for_human", "changes_requested", "high_risk", "unable_to_review"]}
        />
        <label className="text-sm text-slate-600">
          Author
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none transition focus:border-teal-600 focus:bg-white"
            value={filters.author}
            onChange={(event) => setFilters((current) => ({ ...current, author: event.target.value }))}
          />
        </label>
        <Filter
          label="Finding severity"
          value={filters.finding_severity}
          onChange={(value) => setFilters((current) => ({ ...current, finding_severity: value }))}
          options={["critical", "high", "medium", "low"]}
        />
      </div>
      {error ? <p className="text-red-700">{error}</p> : null}
      <div className="overflow-hidden rounded-2xl border border-slate-200/80 bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3 font-medium">PR</th>
              <th className="px-4 py-3 font-medium">Repository</th>
              <th className="px-4 py-3 font-medium">Author</th>
              <th className="px-4 py-3 font-medium">Risk</th>
              <th className="px-4 py-3 font-medium">Findings</th>
              <th className="px-4 py-3 font-medium">Recommendation</th>
              <th className="px-4 py-3 font-medium">Review Status</th>
              <th className="px-4 py-3 font-medium">Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} className="border-t border-slate-100 transition-colors hover:bg-slate-50/80">
                <td className="px-4 py-3">
                  <Link
                    className="font-medium text-slate-900 hover:text-teal-700 hover:underline"
                    to={`/pull-requests/${item.repository}/${item.number}`}
                  >
                    #{item.number} {item.title}
                  </Link>
                </td>
                <td className="px-4 py-3 text-slate-600">{item.repository}</td>
                <td className="px-4 py-3">{item.author}</td>
                <td className="px-4 py-3">
                  <RiskBadge risk={item.latest_risk} />
                </td>
                <td className="px-4 py-3">{item.findings_count}</td>
                <td className="px-4 py-3">{item.latest_recommendation ?? "—"}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={item.human_review_status} />
                </td>
                <td className="px-4 py-3 text-slate-500">
                  {new Date(item.updated_at).toLocaleString()}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function Filter({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  options: string[];
}) {
  return (
    <label className="text-sm text-slate-600">
      {label}
      <select
        className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none transition focus:border-teal-600 focus:bg-white"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">All</option>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}
