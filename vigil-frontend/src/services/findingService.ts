import { request, ApiException } from './api';
import type { FindingListResponse, FindingSeverity, FindingSource, FindingStatus } from '../types';
import { fallbackFindings } from './mockData';

export interface FindingFilterOptions {
  severity?: FindingSeverity | string;
  status?: FindingStatus;
  source?: FindingSource;
  page?: number;
  pageSize?: number;
}

export const findingService = {
  async getFindingsForPR(
    pullRequestId: string,
    filters: FindingFilterOptions = {},
  ): Promise<FindingListResponse> {
    const { severity, status, source, page = 1, pageSize = 50 } = filters;

    try {
      return await request<FindingListResponse>(`/pull-requests/${pullRequestId}/findings`, {
        params: {
          severity: severity || undefined,
          status: status || undefined,
          source: source || undefined,
          page,
          page_size: pageSize,
        },
      });
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        let filtered = [...fallbackFindings];
        if (severity) {
          filtered = filtered.filter((f) => f.severity.toUpperCase() === severity.toUpperCase());
        }
        if (status) {
          filtered = filtered.filter((f) => f.status.toUpperCase() === status.toUpperCase());
        }
        if (source) {
          filtered = filtered.filter((f) => f.source.toUpperCase() === source.toUpperCase());
        }

        return {
          items: filtered,
          total: filtered.length,
          page: 1,
          page_size: pageSize,
          total_pages: 1,
        };
      }
      throw error;
    }
  },
};
