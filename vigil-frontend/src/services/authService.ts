import { request, ApiException } from './api';
import type { UserRead, RepositoryListResponse } from '../types';
import { fallbackRepositories } from './mockData';

export const authService = {
  async getCurrentUser(): Promise<UserRead> {
    try {
      return await request<UserRead>('/me');
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        // Backend offline fallback
        return {
          name: 'Demo Reviewer',
          email: 'reviewer@securepr.ai',
          roles: ['SECURITY_ANALYST'],
          message: 'Offline development mode',
        };
      }
      throw error;
    }
  },

  async getUserRepositories(page = 1, pageSize = 20): Promise<RepositoryListResponse> {
    try {
      // First try /me/repositories
      return await request<RepositoryListResponse>('/me/repositories', {
        params: { page, page_size: pageSize },
      });
    } catch (error) {
      // If 404, fall back to /repositories
      if (error instanceof ApiException && error.status === 404) {
        return await request<RepositoryListResponse>('/repositories', {
          params: { page, page_size: pageSize },
        });
      }
      // If offline
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
};
