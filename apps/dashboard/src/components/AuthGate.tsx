import { useEffect, useState, type ReactNode } from "react";
import { api } from "../api";
import { LoginPage } from "../pages/Login";

export function AuthGate({ children }: { children: (username: string) => ReactNode }) {
  const [username, setUsername] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    api
      .me()
      .then((status) => setUsername(status.authenticated ? status.username : null))
      .catch(() => setUsername(null))
      .finally(() => setReady(true));
  }, []);

  if (!ready) {
    return <p className="p-8 text-sm text-slate-500">Loading…</p>;
  }
  if (!username) {
    return <LoginPage onLoggedIn={setUsername} />;
  }
  return <>{children(username)}</>;
}
