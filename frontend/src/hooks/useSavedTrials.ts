import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useData } from '../contexts/DataContext';
import { useAuth } from './useAuth';
import apiClient from '../services/axiosInterceptor';
import { USERS } from '../lib/api';

/**
 * useSavedTrials
 * Fetches the user's saved trial IDs from the backend on login
 * and syncs them into DataContext as the single source of truth.
 *
 * Call this once at the app level (e.g. PatientDashboard layout or App.tsx)
 */
export function useSavedTrials() {
  const { user } = useAuth();
  const { actions } = useData();

  const { data: savedTrialIds = [] } = useQuery<string[]>({
    queryKey: ['savedTrials'],
    queryFn: async () => {
      const response = await apiClient.get(USERS.ME_SAVED_TRIALS);
      // Backend returns array of trial objects or IDs — extract IDs
      const data = response.data;
      return Array.isArray(data)
        ? data.map((t: { id?: string; trial_id?: string } | string) =>
            typeof t === 'string' ? t : (t.id ?? t.trial_id ?? '')
          ).filter(Boolean)
        : [];
    },
    enabled: !!user,   // only fetch when logged in
    staleTime: 30 * 1000,
    retry: false,
  });

  // ✅ Sync API result into DataContext whenever it changes
  useEffect(() => {
    if (savedTrialIds.length > 0) {
      savedTrialIds.forEach(id => actions.saveTrial(id));
    }
  }, [savedTrialIds]);

  return { savedTrialIds };
}