import type { PaginatedResponse } from './api';

export interface RepositoryRead {
  id: string; // uuid
  user_id: string; // uuid
  github_repo_id: number;
  owner_login: string;
  name: string;
  full_name: string;
  default_branch: string;
  private: boolean;
  html_url: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type RepositoryListResponse = PaginatedResponse<RepositoryRead>;
