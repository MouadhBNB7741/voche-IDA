import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { surveyService } from '../services/surveyService';
import type { SubmitSurveyPayload } from '../services/surveyService';

export function useSurveys() {
  return useQuery({
    queryKey: ['surveys'],
    queryFn: surveyService.getSurveys,
    retry: false,
  });
}

export function useSurveyById(surveyId: string | undefined) {
  return useQuery({
    queryKey: ['survey', surveyId],
    queryFn: () => surveyService.getSurveyById(surveyId!),
    enabled: !!surveyId,
    retry: false,
  });
}

export function useSubmitSurvey() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ surveyId, payload }: { surveyId: string; payload: SubmitSurveyPayload }) =>
      surveyService.submitSurvey(surveyId, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys', 'completed'] });
      toast.success('Survey Submitted', {
        description: 'Your responses have been recorded. Thank you!',
      });
    },

    onError: () => {
      toast.error('Submission Failed', {
        description: 'Could not submit your responses. Please try again.',
      });
    },
  });
}

export function useCompletedSurveys() {
  return useQuery({
    queryKey: ['surveys', 'completed'],
    queryFn: surveyService.getCompletedSurveys,
    retry: false,
  });
}

export function useCompletedSurveyById(completionId: string | undefined) {
  return useQuery({
    queryKey: ['surveys', 'completed', completionId],
    queryFn: () => surveyService.getCompletedSurveyById(completionId!),
    enabled: !!completionId,
    retry: false,
  });
}