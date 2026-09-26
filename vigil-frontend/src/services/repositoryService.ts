import { request, ApiException } from './api';
import type { RepositoryRead, RepositoryListResponse } from '../types';
import { fallbackRepositories } from './mockData';

export const repositoryService = {
  async getRepositories(page = 1, pageSize = 20): Promise<RepositoryListResponse> {
    try {
      return await request<RepositoryListResponse>('/repositories', {
        params: { page, page_size: pageSize },
      });
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        return {
          items: fallbackRepositories,
          total: fallbackRepositories.length,
          page: 1,
          page_size: pageSize,
          total_pages: 1,
        };
      }
      throw error;
    }
  },

  async getRepositoryById(id: string): Promise<RepositoryRead> {
    try {
      return await request<RepositoryRead>(`/repositories/${id}`);
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        const found = fallbackRepositories.find((r) => r.id === id);
        if (found) return found;
      }
      throw error;
    }
  },
};
