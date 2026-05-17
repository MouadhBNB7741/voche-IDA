import { apiClient } from '../lib/apiClient';
import { CLINICAL } from '../lib/api';
import type { ClinicalTrial, PaginatedResponse } from '../types/db';

const SAVED_TRIALS_KEY = 'voce_saved_trials';
const CONNECTED_TRIALS_KEY = 'voce_connected_trials';

export const trialService = {

  async getTrials(filters: { 
    search?: string; 
    disease?: string; 
    phase?: string;
    status?: string;
    location?: string;
    sponsor?: string;
    page?: number;
    limit?: number;
    sort_by?: string;
  } = {}): Promise<ClinicalTrial[]> {
    const urlParams = new URLSearchParams();
    
    if (filters.search) urlParams.append('keyword', filters.search);
    if (filters.disease && filters.disease !== 'all') urlParams.append('disease_areas', filters.disease);
    if (filters.phase && filters.phase !== 'all') urlParams.append('phases', filters.phase);
    if (filters.status && filters.status !== 'all') urlParams.append('statuses', filters.status);
    if (filters.location) urlParams.append('location', filters.location);
    if (filters.sponsor) urlParams.append('sponsor', filters.sponsor);
    
    if (filters.page) urlParams.append('page', String(filters.page));
    if (filters.limit) urlParams.append('limit', String(filters.limit));
    if (filters.sort_by) urlParams.append('sort_by', filters.sort_by);

    const response = await apiClient.get<PaginatedResponse<ClinicalTrial>>(
      CLINICAL.TRIALS,
      { params: urlParams }
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