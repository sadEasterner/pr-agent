import { useEffect, useState } from "react";
import type { AppSettings } from "@gitea-pr-manager/shared-types";
import { api } from "../api";

export function SettingsPage() {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.settings().then(setSettings).catch((err: Error) => setError(err.message));
  }, []);

  if (error) return <p className="text-red-700">{error}</p>;
  if (!settings) return <p className="text-slate-500">Loading settings…</p>;

  return (
    <section className="space-y-6">
      <div className="animate-fade-up">
        <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Automation policy is review-only. Merge and approve actions are forbidden.
        </p>
      </div>
      <article className="animate-fade-up rounded-2xl border border-slate-200/80 bg-white p-6">
        <dl className="grid gap-4 md:grid-cols-2">
          <Item label="Automation mode" value={settings.automation_mode} />
          <Item label="Merge authority" value={settings.merge_authority} />
          <Item label="AI enabled" value={String(settings.ai_enabled)} />
          <Item label="AI provider" value={settings.ai_provider} />
          <Item label="AI model" value={settings.ai_model} />
          <Item label="Gitea configured" value={String(settings.gitea_configured)} />
        </dl>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <List title="Allowed actions" items={settings.allowed_actions} tone="ok" />
          <List title="Forbidden actions" items={settings.forbidden_actions} tone="warn" />
        </div>
        <ul className="mt-6 list-disc space-y-1 pl-5 text-sm text-slate-700">
          {settings.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      </article>
    </section>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-slate-50 px-4 py-3">
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium text-slate-900">{value}</dd>
    </div>
  );
}

function List({ title, items, tone }: { title: string; items: string[]; tone: "ok" | "warn" }) {
  return (
    <div>
      <h2 className="font-semibold">{title}</h2>
      <ul className="mt-2 space-y-1 text-sm">
        {items.map((item) => (
          <li
            key={item}
            className={
              tone === "warn"
                ? "rounded-lg bg-rose-50 px-3 py-1.5 text-rose-800"
                : "rounded-lg bg-teal-50 px-3 py-1.5 text-teal-800"
            }
          >
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
