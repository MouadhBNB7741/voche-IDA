import { useQuery } from '@tanstack/react-query';
import { trialService } from '../services/trialService';

export function useTrialById(id: string | undefined) {
  return useQuery({
    queryKey: ['trial', id],
    queryFn: () => trialService.getById(id!),
    enabled: !!id,
    retry: false,
  });
}