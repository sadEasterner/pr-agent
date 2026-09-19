import type { ReactNode } from "react";

export function PageHeader({
  title,
  description,
  onExport,
  actions,
}: {
  title: string;
  description?: string;
  onExport?: () => void;
  actions?: ReactNode;
}) {
  return (
    <div className="animate-fade-up flex flex-wrap items-start justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
        {description ? <p className="mt-1 text-sm text-slate-500">{description}</p> : null}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        {actions}
        {onExport ? (
          <button
            type="button"
            onClick={onExport}
            className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-50"
          >
            Export PDF
          </button>
        ) : null}
      </div>
    </div>
  );
}
