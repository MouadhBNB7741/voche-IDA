import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { eventService } from '../services/eventService';
import { toast } from 'sonner';

export function useEvents() {
  return useQuery({
    queryKey: ['events'],
    queryFn: eventService.getAll,
    staleTime: 5 * 60 * 1000,
  });
}

export function useEventById(id?: string) {
  return useQuery({
    queryKey: ['event', id],
    queryFn: () => eventService.getById(id!),
    enabled: !!id,
  });
}

export function useRegisterEvent(id?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => eventService.register(id!),
    onSuccess: () => {
      toast.success('Registration Successful', {
        description: 'You have been registered!',
      });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: () => {
      toast.error('Registration Failed', {
        description: 'Could not register. Please try again.',
      });
    },
  });
}

export function useCancelRegistration(id?: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => eventService.cancelRegistration(id!),
    onSuccess: () => {
      toast.info('Registration Cancelled', {
        description: 'You are no longer registered.',
      });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: () => {
      toast.error('Cancellation Failed', {
        description: 'Could not cancel. Please try again.',
      });
    },
  });
}