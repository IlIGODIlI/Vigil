import type { PaginatedResponse } from './api';

export type CommitAnalysisStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | string;

export type CommitAnalysisOverallStatus =
  | 'NO_SIGNIFICANT_GAPS'
  | 'NEEDS_REVIEW'
  | 'INSUFFICIENT_EVIDENCE'
  | string;

export interface CommitAnalysisRead {
  id: string; // uuid
  commit_id: string; // uuid
  status: CommitAnalysisStatus;
  overall_status: CommitAnalysisOverallStatus;
  summary: string | null;
  implementation_notes: string | null;
  testing_notes: string | null;
  error_handling_notes: string | null;
  documentation_notes: string | null;
  placeholder_notes: string | null;
  signals: Record<string, unknown> | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
}

export type CommitAnalysisListResponse = PaginatedResponse<CommitAnalysisRead>;
