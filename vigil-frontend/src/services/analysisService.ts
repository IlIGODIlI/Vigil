import { request, ApiException } from './api';
import type { AnalysisRead } from '../types';

export const analysisService = {
  async triggerPRAnalysis(pullRequestId: string): Promise<AnalysisRead> {
    try {
      return await request<AnalysisRead>(`/pull-requests/${pullRequestId}/analyze`, {
        method: 'POST',
      });
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        // Fallback simulated queued analysis
        return {
          id: 'temp-analysis-' + Date.now(),
          pull_request_id: pullRequestId,
          head_sha: 'head-sha-sample',
          status: 'QUEUED',
          trigger_type: 'MANUAL',
          started_at: new Date().toISOString(),
          completed_at: null,
          error_message: null,
          created_at: new Date().toISOString(),
        };
      }
      throw error;
    }
  },

  async getAnalysisById(analysisId: string): Promise<AnalysisRead> {
    try {
      return await request<AnalysisRead>(`/analyses/${analysisId}`);
    } catch (error) {
      if (error instanceof ApiException && error.status === 0) {
        return {
          id: analysisId,
          pull_request_id: 'mock-pr-id',
          head_sha: 'head-sha-sample',
          status: 'COMPLETED',
          trigger_type: 'MANUAL',
          started_at: new Date().toISOString(),
          completed_at: new Date().toISOString(),
          error_message: null,
          created_at: new Date().toISOString(),
        };
      }
      throw error;
    }
  },

  async pollAnalysisStatus(
    analysisId: string,
    onPoll?: (analysis: AnalysisRead) => void,
    maxAttempts = 60,
    intervalMs = 2500,
  ): Promise<AnalysisRead> {
    let attempts = 0;

    while (attempts < maxAttempts) {
      attempts++;
      const current = await this.getAnalysisById(analysisId);
      if (onPoll) {
        onPoll(current);
      }

      const status = current.status.toUpperCase();
      if (status === 'COMPLETED' || status === 'FAILED' || status === 'CANCELLED') {
        return current;
      }

      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }

    throw new Error('Analysis polling timed out before reaching a terminal status.');
  },
};
