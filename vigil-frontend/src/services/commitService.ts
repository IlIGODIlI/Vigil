import { request, ApiException } from './api';
import type {
  CommitRead,
  CommitListResponse,
  CommitAnalysisRead,
} from '../types';
import { fallbackCommits, fallbackCommitAnalysis } from './mockData';

export const commitService = {
  async getCommitsForPR(
    pullRequestId: string,
    page = 1,
    pageSize = 20,
  ): Promise<CommitListResponse> {
    try {
      return await request<CommitListResponse>(`/pull-requests/${pullRequestId}/commits`, {
        params: { page, page_size: pageSize },
      });
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        return {
          items: fallbackCommits,
          total: fallbackCommits.length,
          page: 1,
          page_size: pageSize,
          total_pages: 1,
        };
      }
      throw error;
    }
  },

  async getCommitBySha(sha: string): Promise<CommitRead> {
    try {
      return await request<CommitRead>(`/commits/${sha}`);
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        const found = fallbackCommits.find((c) => c.sha === sha);
        if (found) return found;
      }
      throw error;
    }
  },

  async triggerCommitAnalysis(sha: string): Promise<CommitAnalysisRead> {
    try {
      return await request<CommitAnalysisRead>(`/commits/${sha}/analyze`, {
        method: 'POST',
      });
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        return fallbackCommitAnalysis;
      }
      throw error;
    }
  },

  async getCommitAnalysisById(id: string): Promise<CommitAnalysisRead> {
    try {
      return await request<CommitAnalysisRead>(`/commit-analyses/${id}`);
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        return fallbackCommitAnalysis;
      }
      throw error;
    }
  },
};
