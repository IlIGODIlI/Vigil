import type { PaginatedResponse } from './api';

export type ReviewStatus = 'DRAFT' | 'READY' | 'PUBLISHED' | 'PUBLISH_FAILED' | string;

export interface ReviewRead {
  id: string; // uuid
  analysis_id: string; // uuid
  status: ReviewStatus;
  summary: string | null;
  review_body: string | null;
  github_review_id: number | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export type ReviewListResponse = PaginatedResponse<ReviewRead>;
