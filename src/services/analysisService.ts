import { request } from './api';
import type { AnalysisRead } from '../types';

export const analysisService = {
  /**
   * POST /api/v1/pull-requests/{id}/analyze
   */
  async triggerPRAnalysis(
    pullRequestId: string,
  ): Promise<AnalysisRead> {
    return await request<AnalysisRead>(
      `/pull-requests/${pullRequestId}/analyze`,
      {
        method: 'POST',
      },
    );
  },

  /**
   * GET /api/v1/analyses/{id}
   */
  async getAnalysisById(
    analysisId: string,
  ): Promise<AnalysisRead> {
    return await request<AnalysisRead>(
      `/analyses/${analysisId}`,
    );
  },

  /**
   * Poll:
   * GET /api/v1/analyses/{id}
   *
   * Stops when the backend reports a terminal status.
   */
  async pollAnalysisStatus(
    analysisId: string,
    onPoll?: (analysis: AnalysisRead) => void,
    maxAttempts = 60,
    intervalMs = 2500,
  ): Promise<AnalysisRead> {
    let attempts = 0;

    while (attempts < maxAttempts) {
      attempts++;

      const current =
        await this.getAnalysisById(
          analysisId,
        );

      onPoll?.(current);

      const status =
        current.status.toUpperCase();

      if (
        status === 'COMPLETED' ||
        status === 'FAILED' ||
        status === 'CANCELLED'
      ) {
        return current;
      }

      await new Promise<void>(
        (resolve) =>
          setTimeout(
            resolve,
            intervalMs,
          ),
      );
    }

    throw new Error(
      'Analysis polling timed out before reaching a terminal status.',
    );
  },
};