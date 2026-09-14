import { useEffect, useState } from "react";
import { ApiError, api, type AdminControls } from "../api";
import { LoginPage } from "./Login";

export function AdminPage() {
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  const [controls, setControls] = useState<AdminControls | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    api
      .me()
      .then((status) => setUsername(status.authenticated ? status.username : null))
      .catch(() => setUsername(null))
      .finally(() => setReady(true));
  }, []);

  useEffect(() => {
    if (!username) return;
    api
      .adminControls()
      .then(setControls)
      .catch((err: Error) => setError(err.message));
  }, [username]);

  async function toggle(field: "ai_enabled" | "pr_comments_enabled", value: boolean) {
    setBusy(field);
    setError(null);
    try {
      const next = await api.updateAdminControls({ [field]: value });
      setControls(next);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Unable to update controls");
    } finally {
      setBusy(null);
    }
  }

  async function logout() {
    await api.logout();
    setUsername(null);
    setControls(null);
  }

  if (!ready) return <p className="text-slate-500">Loading admin…</p>;
  if (!username) return <LoginPage onLoggedIn={setUsername} />;
  if (!controls) return <p className="text-slate-500">Loading controls…</p>;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
          <p className="mt-1 text-sm text-slate-500">
            Signed in as {username}. These switches apply immediately to new PR reviews.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="rounded-full border border-slate-200 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
        >
          Sign out
        </button>
      </div>
      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      <div className="grid gap-4 md:grid-cols-2">
        <ToggleCard
          title="AI review API"
          description={`${controls.ai_provider} / ${controls.ai_model}. When off, only deterministic rules run.`}
          enabled={controls.ai_enabled}
          busy={busy === "ai_enabled"}
          onChange={(value) => void toggle("ai_enabled", value)}
        />
        <ToggleCard
          title="PR comments"
          description="When off, reviews are stored in the dashboard but nothing is posted back to the Git host."
          enabled={controls.pr_comments_enabled}
          busy={busy === "pr_comments_enabled"}
          onChange={(value) => void toggle("pr_comments_enabled", value)}
        />
      </div>
    </section>
  );
}

function ToggleCard({
  title,
  description,
  enabled,
  busy,
  onChange,
}: {
  title: string;
  description: string;
  enabled: boolean;
  busy: boolean;
  onChange: (value: boolean) => void;
}) {
  return (
    <article className="rounded-2xl border border-slate-200/80 bg-white p-5">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-semibold tracking-tight text-slate-800">{title}</h2>
          <p className="mt-1 text-sm text-slate-500">{description}</p>
        </div>
        <button
          type="button"
          role="switch"
          aria-checked={enabled}
          disabled={busy}
          onClick={() => onChange(!enabled)}
          className={[
            "relative h-7 w-12 shrink-0 rounded-full transition",
            enabled ? "bg-teal-600" : "bg-slate-300",
            busy ? "opacity-60" : "",
          ].join(" ")}
        >
          <span
            className={[
              "absolute top-0.5 h-6 w-6 rounded-full bg-white transition",
              enabled ? "left-0.5 translate-x-5" : "left-0.5",
            ].join(" ")}
          />
        </button>
      </div>
      <p className="mt-4 text-sm font-medium text-slate-900">{enabled ? "On" : "Off"}</p>
    </article>
  );
}
