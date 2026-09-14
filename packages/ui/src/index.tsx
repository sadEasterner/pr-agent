import type { HumanReviewStatus, RiskLevel } from "@gitea-pr-manager/shared-types";
import { HUMAN_STATUS_LABEL } from "@gitea-pr-manager/shared-types";

const RISK_CLASS: Record<string, string> = {
  low: "bg-emerald-100 text-emerald-800",
  medium: "bg-amber-100 text-amber-800",
  high: "bg-orange-100 text-orange-800",
  critical: "bg-red-100 text-red-800",
  unknown: "bg-slate-100 text-slate-700",
};

const STATUS_CLASS: Record<string, string> = {
  waiting_for_human: "bg-sky-100 text-sky-800",
  changes_requested: "bg-amber-100 text-amber-900",
  high_risk: "bg-red-100 text-red-800",
  unable_to_review: "bg-slate-200 text-slate-700",
  pending: "bg-slate-100 text-slate-600",
};

export function RiskBadge({ risk }: { risk: RiskLevel | string | null }) {
  const value = risk ?? "unknown";
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold capitalize ${RISK_CLASS[value] ?? RISK_CLASS.unknown}`}
    >
      {value}
    </span>
  );
}

export function StatusBadge({ status }: { status: HumanReviewStatus | string }) {
  return (
    <span
      className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${STATUS_CLASS[status] ?? STATUS_CLASS.pending}`}
    >
      {HUMAN_STATUS_LABEL[status as HumanReviewStatus] ?? status}
    </span>
  );
}

export function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <article className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold tracking-tight text-slate-900">{value}</p>
      {hint ? <p className="mt-2 text-xs text-slate-500">{hint}</p> : null}
    </article>
  );
}
