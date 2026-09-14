export type RiskLevel = "low" | "medium" | "high" | "critical" | "unknown";

export type Recommendation =
  | "ready_for_human_review"
  | "changes_requested"
  | "high_risk"
  | "unable_to_review";

export type HumanReviewStatus =
  | "pending"
  | "waiting_for_human"
  | "changes_requested"
  | "high_risk"
  | "unable_to_review";

export interface Finding {
  id: number;
  severity: "critical" | "high" | "medium" | "low";
  confidence: number;
  category: string;
  rule: string;
  file: string;
  line: number | null;
  message: string;
  suggested_fix: string;
}

export interface ReviewMetrics {
  changed_files: number;
  lines_added: number;
  lines_removed: number;
  test_files_changed: number;
  number_of_commits: number;
}

export interface Review {
  id: number;
  iteration: number;
  commit_sha: string;
  created_at: string;
  ai_model: string | null;
  risk: RiskLevel;
  recommendation: Recommendation;
  summary: string;
  processing_duration_ms: number;
  findings: Finding[];
  metrics: ReviewMetrics | null;
}

export interface PullRequestSummary {
  id: number;
  repository: string;
  number: number;
  title: string;
  author: string;
  source_branch: string;
  target_branch: string;
  gitea_url: string;
  latest_sha: string;
  status: string;
  human_review_status: HumanReviewStatus;
  latest_risk: RiskLevel | null;
  latest_recommendation: Recommendation | null;
  opened_at: string | null;
  closed_at: string | null;
  merged_at: string | null;
  updated_at: string;
  findings_count: number;
  review_iterations: number;
  merge_authority: "human_approval_required";
  ai_is_not_approval: boolean;
}

export interface PullRequestDetail extends PullRequestSummary {
  description: string;
  reviews: Review[];
}

export interface AnalyticsSummary {
  prs_reviewed: number;
  prs_waiting_for_human_review: number;
  high_risk_prs: number;
  prs_merged: number;
  average_pr_size_lines: number;
  average_pr_size_files: number;
  average_merge_time_seconds: number;
  average_time_to_first_review_seconds: number;
  findings_this_week: number;
}

export interface AnalyticsTrends {
  reviews_over_time: Array<{ date: string; count: number }>;
  risk_distribution: Array<{ risk: string; count: number }>;
  pr_size_trend: Array<{ date: string; average_lines: number }>;
  merge_time_trend: Array<{ date: string; average_seconds: number }>;
}

export interface AnalyticsFindings {
  by_severity: Array<{ severity: string; count: number }>;
  by_category: Array<{ category: string; count: number }>;
  common_violated_rules: Array<{ rule: string; count: number }>;
  recurring_modules: Array<{ path: string; count: number }>;
  over_time: Array<{ date: string; severity: string; count: number }>;
}

export interface RepositoryStats {
  repository: string;
  prs: number;
  reviews: number;
  merged: number;
  high_risk: number;
}

export interface AppSettings {
  automation_mode: string;
  allowed_actions: string[];
  forbidden_actions: string[];
  ai_enabled: boolean;
  ai_provider: string;
  ai_model: string;
  gitea_configured: boolean;
  merge_authority: "human";
  notes: string[];
}

export const HUMAN_STATUS_LABEL: Record<HumanReviewStatus, string> = {
  pending: "Pending",
  waiting_for_human: "READY FOR HUMAN REVIEW",
  changes_requested: "CHANGES REQUESTED",
  high_risk: "HIGH RISK",
  unable_to_review: "UNABLE TO REVIEW",
};
