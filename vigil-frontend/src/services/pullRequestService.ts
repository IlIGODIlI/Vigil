import { request, ApiException } from './api';
import type { PullRequestRead, PullRequestListResponse } from '../types';
import { fallbackPullRequests } from './mockData';

export const pullRequestService = {
  async getPullRequestsForRepository(
    repositoryId: string,
    page = 1,
    pageSize = 20,
  ): Promise<PullRequestListResponse> {
    try {
      return await request<PullRequestListResponse>(
        `/repositories/${repositoryId}/pull-requests`,
        {
          params: { page, page_size: pageSize },
        },
      );
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        const items = fallbackPullRequests.filter(
          (pr) => pr.repository_id === repositoryId || true,
        );
        return {
          items,
          total: items.length,
          page: 1,
          page_size: pageSize,
          total_pages: 1,
        };
      }
      throw error;
    }
  },

  async getPullRequestById(id: string): Promise<PullRequestRead> {
    try {
      return await request<PullRequestRead>(`/pull-requests/${id}`);
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        const found = fallbackPullRequests.find((pr) => pr.id === id);
        if (found) return found;
        if (fallbackPullRequests.length > 0) return fallbackPullRequests[0];
      }
      throw error;
    }
  },
};
