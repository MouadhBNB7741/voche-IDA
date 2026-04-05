import type { ClinicalTrial } from '../types/db';

/**
 * Voche Clinical Trial Service
 * Synchronized with backend schema (trial_id, disease_area, etc.)
 */

const CONNECTED_TRIALS_KEY = 'voce_connected_trials';

export const trialService = {
  /**
   * Get all trials (Placeholder for API call)
   */
  getAll(): ClinicalTrial[] {
    return [];
  },

  /**
   * Get trial by ID (Placeholder for API call)
   */
  getById(_id: string): ClinicalTrial | undefined {
    return undefined;
  },

  /**
   * Local storage fallback for connection status (until API is live)
   */
  getConnectedTrials(): string[] {
    const stored = localStorage.getItem(CONNECTED_TRIALS_KEY);
    return stored ? JSON.parse(stored) : [];
  },

  connectTrial(trialId: string): void {
    const connected = this.getConnectedTrials();
    if (!connected.includes(trialId)) {
      connected.push(trialId);
      localStorage.setItem(CONNECTED_TRIALS_KEY, JSON.stringify(connected));
    }
  },

  isTrialConnected(trialId: string): boolean {
    return this.getConnectedTrials().includes(trialId);
  },

  /**
   * Search utility (Placeholder)
   */
  search(_query: string, _filters?: { disease_area?: string; phase?: string }): ClinicalTrial[] {
    return [];
  },
};
