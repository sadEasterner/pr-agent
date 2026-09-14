/// <reference types="vitest/globals" />
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";
import App from "./App";
import { PullRequestsPage } from "./pages/PullRequests";
import { PullRequestDetailPage } from "./pages/PullRequestDetail";
import { SettingsPage } from "./pages/Settings";

const pr = {
  id: 1,
  repository: "acme/demo",
  number: 42,
  title: "Add user endpoint",
  author: "alice",
  source_branch: "feat",
  target_branch: "main",
  gitea_url: "https://gitea.test/acme/demo/pulls/42",
  latest_sha: "abc123def",
  status: "open",
  human_review_status: "waiting_for_human",
  latest_risk: "low",
  latest_recommendation: "ready_for_human_review",
  opened_at: "2026-09-14T00:00:00Z",
  closed_at: null,
  merged_at: null,
  updated_at: "2026-09-14T00:00:00Z",
  findings_count: 1,
  review_iterations: 2,
  merge_authority: "human_approval_required",
  ai_is_not_approval: true,
  description: "Adds an endpoint",
  reviews: [
    {
      id: 1,
      iteration: 1,
      commit_sha: "abc123def",
      created_at: "2026-09-14T00:00:00Z",
      ai_model: "mock",
      risk: "medium",
      recommendation: "changes_requested",
      summary: "Needs authorization.",
      processing_duration_ms: 10,
      findings: [
        {
          id: 1,
          severity: "high",
          confidence: 0.9,
          category: "authorization",
          rule: "Every endpoint must verify authorization.",
          file: "users.py",
          line: 82,
          message: "Missing check",
          suggested_fix: "Add guard",
        },
      ],
      metrics: {
        changed_files: 2,
        lines_added: 12,
        lines_removed: 1,
        test_files_changed: 1,
        number_of_commits: 1,
      },
    },
    {
      id: 2,
      iteration: 2,
      commit_sha: "def456abc",
      created_at: "2026-09-14T01:00:00Z",
      ai_model: "mock",
      risk: "low",
      recommendation: "ready_for_human_review",
      summary: "Improved.",
      processing_duration_ms: 11,
      findings: [],
      metrics: null,
    },
  ],
};

function mockJson(data: unknown) {
  return Promise.resolve({
    ok: true,
    json: async () => data,
  }) as Promise<Response>;
}

function mockFetch(data: unknown) {
  return vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
    const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
    if (url.includes("/api/auth/me")) {
      return mockJson({ authenticated: true, username: "sadEasterner" });
    }
    if (url.includes("/api/auth/login")) {
      return mockJson({ authenticated: true, username: "sadEasterner" });
    }
    return mockJson(data);
  });
}

describe("dashboard", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders navigation", async () => {
    mockFetch({
        prs_reviewed: 0,
        prs_waiting_for_human_review: 0,
        high_risk_prs: 0,
        prs_merged: 0,
        average_pr_size_lines: 0,
        average_pr_size_files: 0,
        average_merge_time_seconds: 0,
        average_time_to_first_review_seconds: 0,
        findings_this_week: 0,
        reviews_over_time: [],
        risk_distribution: [],
        pr_size_trend: [],
        merge_time_trend: [],
        by_severity: [],
        by_category: [],
        common_violated_rules: [],
        recurring_modules: [],
        over_time: [],
    });
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );
    expect(await screen.findByText("Overview")).toBeInTheDocument();
    expect(screen.getByText("Pull Requests")).toBeInTheDocument();
    expect(screen.getByText("AI reviews are advisory. Humans control merge.")).toBeInTheDocument();
    expect(await screen.findByText("PRs reviewed")).toBeInTheDocument();
  });

  it("renders pull request list from API state", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJson([pr]) as unknown as Response,
    );
    render(
      <MemoryRouter>
        <PullRequestsPage />
      </MemoryRouter>,
    );
    expect(await screen.findByText(/Add user endpoint/)).toBeInTheDocument();
    expect(screen.getByText("READY FOR HUMAN REVIEW")).toBeInTheDocument();
  });

  it("shows review history and human-control messaging", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(mockJson(pr) as unknown as Response);
    render(
      <MemoryRouter initialEntries={["/pull-requests/acme/demo/42"]}>
        <Routes>
          <Route path="/pull-requests/:owner/:repo/:number" element={<PullRequestDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );
    expect(await screen.findByText("READY FOR HUMAN REVIEW")).toBeInTheDocument();
    expect(screen.getByText(/This is not approval/)).toBeInTheDocument();
    expect(screen.getByText(/Review #1 — SHA abc123de/)).toBeInTheDocument();
    expect(screen.getByText(/Review #2 — SHA def456ab/)).toBeInTheDocument();
    expect(screen.getByText("Open in Gitea")).toBeInTheDocument();
  });

  it("loads settings policy", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      mockJson({
        automation_mode: "review_only",
        allowed_actions: ["post_review"],
        forbidden_actions: ["merge_pr", "approve_pr"],
        ai_enabled: false,
        ai_provider: "openai",
        ai_model: "gpt-4o-mini",
        gitea_configured: false,
        merge_authority: "human",
        notes: ["The system never merges or approves pull requests."],
      }) as unknown as Response,
    );
    render(<SettingsPage />);
    expect(await screen.findByText("review_only")).toBeInTheDocument();
    expect(screen.getByText("merge_pr")).toBeInTheDocument();
    expect(
      screen.getByText("The system never merges or approves pull requests."),
    ).toBeInTheDocument();
  });
});
