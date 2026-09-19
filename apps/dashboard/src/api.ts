import type {
  AnalyticsFindings,
  AnalyticsSummary,
  AnalyticsTrends,
  AppSettings,
  AuthorDetail,
  AuthorStats,
  PullRequestDetail,
  PullRequestSummary,
  RepositoryStats,
} from "@gitea-pr-manager/shared-types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    throw new ApiError(response.status, `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export type AuthStatus = {
  authenticated: boolean;
  username: string | null;
};

export type AdminControls = {
  username: string;
  ai_enabled: boolean;
  pr_comments_enabled: boolean;
  ai_provider: string;
  ai_model: string;
};

export const api = {
  me: () => request<AuthStatus>("/api/auth/me"),
  login: (username: string, password: string) =>
    request<AuthStatus>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<AuthStatus>("/api/auth/logout", { method: "POST" }),
  adminControls: () => request<AdminControls>("/api/admin/controls"),
  updateAdminControls: (payload: Partial<Pick<AdminControls, "ai_enabled" | "pr_comments_enabled">>) =>
    request<AdminControls>("/api/admin/controls", {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  summary: () => request<AnalyticsSummary>("/api/analytics/summary"),
  trends: () => request<AnalyticsTrends>("/api/analytics/trends"),
  findings: () => request<AnalyticsFindings>("/api/analytics/findings"),
  repositories: () => request<RepositoryStats[]>("/api/analytics/repositories"),
  authors: () => request<AuthorStats[]>("/api/analytics/authors"),
  author: (author: string) => request<AuthorDetail>(`/api/analytics/authors/${encodeURIComponent(author)}`),
  pullRequests: (params?: Record<string, string>) => {
    const query = new URLSearchParams(params).toString();
    return request<PullRequestSummary[]>(`/api/prs${query ? `?${query}` : ""}`);
  },
  pullRequest: (repository: string, number: string) =>
    request<PullRequestDetail>(`/api/prs/${repository}/${number}`),
  settings: () => request<AppSettings>("/api/settings"),
};

export function formatDuration(seconds: number): string {
  if (!seconds) return "—";
  const hours = seconds / 3600;
  if (hours < 1) return `${Math.round(seconds / 60)}m`;
  if (hours < 48) return `${hours.toFixed(1)}h`;
  return `${(hours / 24).toFixed(1)}d`;
}

export function shortSha(sha: string): string {
  return sha.slice(0, 8);
}
