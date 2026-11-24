import { useQuery } from '@tanstack/react-query';
import { trialService } from '../services/trialService';

interface TrialFilters {
  search?: string;
  disease?: string;
  phase?: string;
  status?: string;
  location?: string;
  sponsor?: string;
  page?: number;
  limit?: number;
  sort_by?: string;
  eligibleForMe?: boolean;
}

export function useTrials(filters: TrialFilters = {}, enabled = true) {
  return useQuery({
    queryKey: ['trials', filters], 
    queryFn: () => trialService.getTrials(filters),
    enabled,
    retry: false
  });
}