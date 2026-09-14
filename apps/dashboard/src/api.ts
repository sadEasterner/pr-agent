import type {
  AnalyticsFindings,
  AnalyticsSummary,
  AnalyticsTrends,
  AppSettings,
  PullRequestDetail,
  PullRequestSummary,
  RepositoryStats,
} from "@gitea-pr-manager/shared-types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "";

async function request<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return (await response.json()) as T;
}

export const api = {
  summary: () => request<AnalyticsSummary>("/api/analytics/summary"),
  trends: () => request<AnalyticsTrends>("/api/analytics/trends"),
  findings: () => request<AnalyticsFindings>("/api/analytics/findings"),
  repositories: () => request<RepositoryStats[]>("/api/analytics/repositories"),
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
