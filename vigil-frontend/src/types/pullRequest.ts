import type { PaginatedResponse } from './api';

export interface PullRequestRead {
  id: string; // uuid
  repository_id: string; // uuid
  github_pr_id: number;
  pr_number: number;
  title: string;
  description: string | null;
  author_login: string;
  source_branch: string;
  target_branch: string;
  head_sha: string;
  base_sha: string;
  status: string; // e.g., "OPEN", "CLOSED", "MERGED"
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  merged_at: string | null;
}

export type PullRequestListResponse = PaginatedResponse<PullRequestRead>;
