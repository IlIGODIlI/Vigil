import type { PaginatedResponse } from './api';

export type AnalysisStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';
export type AnalysisTrigger = 'WEBHOOK' | 'MANUAL';

export interface AnalysisRead {
  id: string; // uuid
  pull_request_id: string; // uuid
  head_sha: string;
  status: AnalysisStatus | string;
  trigger_type: AnalysisTrigger | string;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_at: string;
}

export type AnalysisListResponse = PaginatedResponse<AnalysisRead>;
