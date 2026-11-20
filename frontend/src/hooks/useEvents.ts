import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { eventService } from '../services/eventService';
import { toast } from 'sonner';
import { useErrorHandler } from './useErrorHandler';
import { useAuthContext } from '../contexts/AuthContext';

export function useEvents() {
  return useQuery({
    queryKey: ['events'],
    queryFn: eventService.getAll,
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * The events the logged-in user is registered for, as a set of ids.
 * The events list itself doesn't say, so pages combine the two.
 */
export function useMyEventIds() {
  const { isAuthenticated } = useAuthContext();
  const query = useQuery({
    queryKey: ['events', 'mine'],
    queryFn: eventService.getMyEventIds,
    enabled: isAuthenticated,
    staleTime: 60 * 1000,
  });
  return new Set(isAuthenticated ? query.data ?? [] : []);
}

/** Register for an event, or cancel, from a list of events. */
export function useToggleRegistration() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: ({ id, registered }: { id: string; registered: boolean }) =>
      registered ? eventService.cancelRegistration(id) : eventService.register(id),
    onSuccess: (_, { id, registered }) => {
      if (registered) toast.info('Registration Cancelled');
      else toast.success('Registration Successful', { description: 'You have been registered!' });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: (err, { registered }) =>
      handleError(err, registered ? 'Could not cancel. Please try again.' : 'Could not register. Please try again.'),
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
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: () => eventService.register(id!),
    onSuccess: () => {
      toast.success('Registration Successful', {
        description: 'You have been registered!',
      });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: (err) => {
      handleError(err, 'Could not register. Please try again.');
    },
  });
}

export function useCancelRegistration(id?: string) {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: () => eventService.cancelRegistration(id!),
    onSuccess: () => {
      toast.info('Registration Cancelled', {
        description: 'You are no longer registered.',
      });
      queryClient.invalidateQueries({ queryKey: ['events'] });
      queryClient.invalidateQueries({ queryKey: ['event', id] });
    },
    onError: (err) => {
      handleError(err, 'Could not cancel. Please try again.');
    },
  });
}