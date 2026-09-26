import { request, ApiException } from './api';
import type { ReviewQueueListResponse, ReviewQueueItem } from '../types';
import { fallbackQueueItems } from './mockData';

export const reviewQueueService = {
  async getReviewQueue(page = 1, pageSize = 20): Promise<ReviewQueueListResponse> {
    try {
      return await request<ReviewQueueListResponse>('/review-queue', {
        params: { page, page_size: pageSize },
      });
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        return {
          items: fallbackQueueItems,
          total: fallbackQueueItems.length,
          page: 1,
          page_size: pageSize,
          total_pages: 1,
        };
      }
      throw error;
    }
  },

  async getReviewQueueItem(pullRequestId: string): Promise<ReviewQueueItem> {
    try {
      return await request<ReviewQueueItem>(`/review-queue/${pullRequestId}`);
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        const item = fallbackQueueItems.find((q) => q.pull_request.id === pullRequestId);
        if (item) return item;
      }
      throw error;
    }
  },
};
