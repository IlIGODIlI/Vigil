import type { PaginatedResponse } from './api';

export interface CommitRead {
  id: string; // uuid
  repository_id: string; // uuid
  sha: string;
  message: string;
  author_login: string | null;
  author_name: string | null;
  author_email: string | null;
  committed_at: string | null;
  parent_sha: string | null;
  created_at: string;
}

export type CommitListResponse = PaginatedResponse<CommitRead>;
