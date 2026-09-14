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
  if (!settings) return <p>Loading settings…</p>;

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="mt-1 text-sm text-slate-500">
          Automation policy is review-only. Merge and approve actions are forbidden.
        </p>
      </div>
      <article className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <dl className="grid gap-4 md:grid-cols-2">
          <Item label="Automation mode" value={settings.automation_mode} />
          <Item label="Merge authority" value={settings.merge_authority} />
          <Item label="AI enabled" value={String(settings.ai_enabled)} />
          <Item label="AI provider" value={settings.ai_provider} />
          <Item label="AI model" value={settings.ai_model} />
          <Item label="Gitea configured" value={String(settings.gitea_configured)} />
        </dl>
        <div className="mt-6 grid gap-6 md:grid-cols-2">
          <List title="Allowed actions" items={settings.allowed_actions} />
          <List title="Forbidden actions" items={settings.forbidden_actions} />
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
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 font-medium">{value}</dd>
    </div>
  );
}

function List({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h2 className="font-semibold">{title}</h2>
      <ul className="mt-2 list-disc pl-5 text-sm text-slate-700">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}
