import { mockTrials } from '../data/mockData';
import type { Trial } from '../data/mockData';

const SAVED_TRIALS_KEY = 'voce_saved_trials';
const CONNECTED_TRIALS_KEY = 'voce_connected_trials';

export const trialService = {
  getAll(): Trial[] {
    return mockTrials;
  },

  getById(id: string): Trial | undefined {
    return mockTrials.find(trial => trial.id === id);
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

  getSavedTrialDetails(): Trial[] {
    const savedIds = this.getSavedTrials();
    return mockTrials.filter(trial => savedIds.includes(trial.id));
  },

  // Connection Logic
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

  search(query: string, filters?: { disease?: string; phase?: string }): Trial[] {
    return mockTrials.filter(trial => {
      const matchesSearch = !query ||
        trial.title.toLowerCase().includes(query.toLowerCase()) ||
        trial.description.toLowerCase().includes(query.toLowerCase()) ||
        trial.location.toLowerCase().includes(query.toLowerCase());

      const matchesDisease = !filters?.disease || filters.disease === 'all' || trial.disease === filters.disease;
      const matchesPhase = !filters?.phase || filters.phase === 'all' || trial.phase === filters.phase;

      return matchesSearch && matchesDisease && matchesPhase;
    });
  },
};