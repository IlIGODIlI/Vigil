import type { PaginatedResponse } from './api';
import type { PullRequestRead } from './pullRequest';

export interface ReviewQueueItem {
  pull_request: PullRequestRead;
  latest_analysis_id: string | null;
  latest_analysis_status: string | null;
  latest_review_id: string | null;
  latest_review_status: string | null;
  queued_at: string | null;
}

export type ReviewQueueListResponse = PaginatedResponse<ReviewQueueItem>;
