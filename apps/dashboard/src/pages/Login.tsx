import { useState, type FormEvent } from "react";
import { ApiError, api } from "../api";

export function LoginPage({ onLoggedIn }: { onLoggedIn: (username: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api.login(username, password);
      if (!result.authenticated || !result.username) {
        setError("Invalid username or password");
        return;
      }
      onLoggedIn(result.username);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Invalid username or password");
      } else {
        setError(err instanceof Error ? err.message : "Unable to sign in");
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex justify-start">
      <form
        onSubmit={submit}
        className="w-full max-w-sm space-y-5 rounded-2xl border border-slate-200/80 bg-white p-6"
      >
        <div>
          <h1 className="text-xl font-semibold tracking-tight text-slate-900">Admin sign in</h1>
          <p className="mt-1 text-sm text-slate-500">
            Overview, PRs, and findings stay public. Only this page requires a login.
          </p>
        </div>
        <label className="block text-sm text-slate-600">
          Username
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none transition focus:border-teal-600 focus:bg-white"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            required
          />
        </label>
        <label className="block text-sm text-slate-600">
          Password
          <input
            className="mt-1 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-900 outline-none transition focus:border-teal-600 focus:bg-white"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>
        {error ? <p className="text-sm text-red-700">{error}</p> : null}
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-full bg-slate-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:opacity-60"
        >
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
    </div>
  );
}
