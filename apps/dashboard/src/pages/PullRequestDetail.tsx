import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { RiskBadge } from "@gitea-pr-manager/ui";
import type { Finding, PullRequestDetail } from "@gitea-pr-manager/shared-types";
import { HUMAN_STATUS_LABEL } from "@gitea-pr-manager/shared-types";
import { api, shortSha } from "../api";
import { authorLabel } from "../lib/names";
import { exportPdf } from "../lib/pdf";

const SEVERITIES = ["critical", "high", "medium", "low"] as const;

export function PullRequestDetailPage() {
  const params = useParams();
  const [item, setItem] = useState<PullRequestDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!params.owner || !params.repo || !params.number) return;
    api
      .pullRequest(`${params.owner}/${params.repo}`, params.number)
      .then(setItem)
      .catch((err: Error) => setError(err.message));
  }, [params.owner, params.repo, params.number]);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!item) return <p className="text-slate-500">Loading pull request…</p>;

  const latest = item.reviews[item.reviews.length - 1];
  const grouped = SEVERITIES.map((severity) => ({
    severity,
    findings: latest?.findings.filter((finding) => finding.severity === severity) ?? [],
  }));

  return (
    <section className="space-y-6">
      <Link to="/pull-requests" className="text-sm text-slate-500 hover:text-slate-800">
        ← Pull Requests
      </Link>
      <div className="animate-fade-up rounded-2xl border border-slate-200/80 bg-white p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm text-slate-500">
              {item.repository} #{item.number}
            </p>
            <h1 className="mt-1 text-2xl font-semibold">{item.title}</h1>
            <p className="mt-2 text-sm text-slate-600">
              <Link
                className="font-medium text-slate-900 hover:text-teal-700 hover:underline"
                to={`/people/${encodeURIComponent(item.author)}`}
              >
                {authorLabel(item.author, item.author_name)}
              </Link>{" "}
              · {item.source_branch} → {item.target_branch}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded-full border border-slate-200 bg-white px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
              onClick={() =>
                exportPdf({
                  title: `#${item.number} ${item.title}`,
                  subtitle: `${item.repository} · ${authorLabel(item.author, item.author_name)}`,
                  metrics: [
                    { label: "Author", value: authorLabel(item.author, item.author_name) },
                    { label: "Risk", value: item.latest_risk ?? "—" },
                    { label: "Review status", value: HUMAN_STATUS_LABEL[item.human_review_status] },
                    { label: "Findings", value: latest?.findings.length ?? 0 },
                    { label: "Review rounds", value: item.reviews.length },
                  ],
                  tables: [
                    {
                      title: "Latest findings",
                      headers: ["Severity", "File", "Message", "Rule"],
                      rows: (latest?.findings ?? []).map((finding) => [
                        finding.severity,
                        `${finding.file}${finding.line ? `:${finding.line}` : ""}`,
                        finding.message,
                        finding.rule || finding.category,
                      ]),
                    },
                    {
                      title: "Review history",
                      headers: ["Round", "SHA", "Risk", "Recommendation", "Findings"],
                      rows: item.reviews.map((review) => [
                        review.iteration,
                        shortSha(review.commit_sha),
                        review.risk,
                        review.recommendation,
                        review.findings.length,
                      ]),
                    },
                  ],
                })
              }
            >
              Export PDF
            </button>
            <a
              className="rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800"
              href={item.gitea_url}
              target="_blank"
              rel="noreferrer"
            >
              Open pull request
            </a>
          </div>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-4">
          <Info label="Latest SHA" value={shortSha(item.latest_sha)} />
          <Info
            label="Size"
            value={
              latest?.metrics
                ? `${latest.metrics.changed_files} files / +${latest.metrics.lines_added} −${latest.metrics.lines_removed}`
                : "—"
            }
          />
          <Info label="Opened" value={item.opened_at ? new Date(item.opened_at).toLocaleString() : "—"} />
          <Info label="Current risk" value={<RiskBadge risk={item.latest_risk} />} />
        </div>
        <div className="mt-6 rounded-xl border border-amber-200 bg-amber-50 p-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-amber-800">
            AI Recommendation
          </p>
          <p className="mt-1 text-lg font-semibold text-amber-950">
            {HUMAN_STATUS_LABEL[item.human_review_status]}
          </p>
          <p className="mt-2 text-sm text-amber-900">
            This is not approval. Merge authority remains with a human on the Git host.
          </p>
        </div>
      </div>
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Findings</h2>
        {grouped.map((group) => (
          <article key={group.severity} className="animate-fade-up rounded-2xl border border-slate-200/80 bg-white p-4">
            <h3 className="font-semibold capitalize">
              {group.severity} ({group.findings.length})
            </h3>
            <ul className="mt-3 space-y-3">
              {group.findings.map((finding) => (
                <FindingItem key={finding.id} finding={finding} />
              ))}
              {group.findings.length === 0 ? (
                <li className="text-sm text-slate-500">No {group.severity} findings in the latest review.</li>
              ) : null}
            </ul>
          </article>
        ))}
      </section>
      <section className="animate-fade-up rounded-2xl border border-slate-200/80 bg-white p-4">
        <h2 className="text-lg font-semibold">Review history</h2>
        <p className="mt-1 text-sm text-slate-500">
          Compare how the PR changed across commit SHAs. The same SHA is not reviewed twice unless a
          human requests it.
        </p>
        <ol className="mt-4 space-y-3">
          {item.reviews.map((review) => (
            <li key={review.id} className="rounded-xl border border-slate-100 bg-slate-50/70 p-3">
              <p className="font-medium">
                Review #{review.iteration} — SHA {shortSha(review.commit_sha)}
              </p>
              <p className="text-sm text-slate-500">
                {new Date(review.created_at).toLocaleString()} · {review.risk} · {review.recommendation} ·{" "}
                {review.findings.length} findings
              </p>
              <p className="mt-2 text-sm">{review.summary}</p>
            </li>
          ))}
        </ol>
      </section>
    </section>
  );
}

function Info({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-1 text-sm font-medium text-slate-900">{value}</div>
    </div>
  );
}

function FindingItem({ finding }: { finding: Finding }) {
  return (
    <li className="rounded-md bg-slate-50 p-3 text-sm">
      <p className="font-medium">
        {finding.file}
        {finding.line ? `:${finding.line}` : ""}
      </p>
      <p className="mt-1">{finding.message}</p>
      <p className="mt-1 text-slate-500">Rule: {finding.rule || finding.category}</p>
      {finding.suggested_fix ? <p className="mt-1">Suggested fix: {finding.suggested_fix}</p> : null}
      <p className="mt-1 text-xs text-slate-500">Confidence: {Math.round(finding.confidence * 100)}%</p>
    </li>
  );
}
