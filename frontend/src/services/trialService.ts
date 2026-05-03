import { apiClient } from '../lib/apiClient';
import { CLINICAL } from '../lib/api';
import type { ClinicalTrial, PaginatedResponse } from '../types/db';

const SAVED_TRIALS_KEY = 'voce_saved_trials';
const CONNECTED_TRIALS_KEY = 'voce_connected_trials';

export const trialService = {

  async getTrials(filters: { search?: string; disease?: string; phase?: string } = {}): Promise<ClinicalTrial[]> {
    const params: Record<string, string> = {};
    if (filters.search) params.search = filters.search;
    if (filters.disease && filters.disease !== 'all') params.disease_area = filters.disease;
    if (filters.phase && filters.phase !== 'all') params.phase = filters.phase;

    const response = await apiClient.get<PaginatedResponse<ClinicalTrial>>(
      CLINICAL.TRIALS,
      { params }
    );
    return response.data?.items ?? [];
  },

  async getById(id: string): Promise<ClinicalTrial> {
    const response = await apiClient.get<ClinicalTrial>(CLINICAL.TRIAL_BY_ID(id));
    return response.data;
  },

  getSavedTrials(): string[] {
    const stored = localStorage.getItem(SAVED_TRIALS_KEY);
    return stored ? JSON.parse(stored) : [];
  },

  saveTrial(trialId: string): void {
    const saved = this.getSavedTrials();
    if (!saved.includes(trialId)) {
      saved.push(trialId);
      localStorage.setItem(SAVED_TRIALS_KEY, JSON.stringify(saved));
    }
  },

  unsaveTrial(trialId: string): void {
    const saved = this.getSavedTrials().filter(id => id !== trialId);
    localStorage.setItem(SAVED_TRIALS_KEY, JSON.stringify(saved));
  },

  isTrialSaved(trialId: string): boolean {
    return this.getSavedTrials().includes(trialId);
  },

  toggleSavedTrial(trialId: string): boolean {
    if (this.isTrialSaved(trialId)) {
      this.unsaveTrial(trialId);
      return false;
    } else {
      this.saveTrial(trialId);
      return true;
    }
  },

  getSavedTrialDetails(): ClinicalTrial[] {
    return [];
  },

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
};