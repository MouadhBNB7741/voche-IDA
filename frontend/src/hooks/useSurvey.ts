import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { surveyService } from '../services/surveyService';
import type { Answer, NewSurvey, SubmitSurveyPayload, SurveyStatus } from '../services/surveyService';
import { useErrorHandler } from './useErrorHandler';

export function useSurveys(enabled = true) {
  return useQuery({
    queryKey: ['surveys'],
    queryFn: surveyService.getSurveys,
    enabled,
    retry: false,
  });
}

export function useSurveyById(surveyId: string | undefined) {
  return useQuery({
    queryKey: ['survey', surveyId],
    queryFn: () => surveyService.getSurveyById(surveyId!),
    enabled: !!surveyId,
    retry: false,
    refetchOnWindowFocus: false,
  });
}

export function useAssignedSurveys(enabled = true) {
  return useQuery({
    queryKey: ['surveys', 'assigned'],
    queryFn: surveyService.getAssignedSurveys,
    enabled,
    retry: false,
  });
}

export function useSubmitSurvey() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();

  return useMutation({
    mutationFn: ({ surveyId, payload }: { surveyId: string; payload: SubmitSurveyPayload }) =>
      surveyService.submitSurvey(surveyId, payload),

    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      toast.success('Survey Submitted', {
        description: 'Your responses have been recorded. Thank you!',
      });
    },

    onError: (err) => {
      handleError(err, 'Could not submit your responses. Please try again.');
    },
  });
}

export function useSaveSurveyDraft() {
  return useMutation({
    mutationFn: ({ surveyId, answers }: { surveyId: string; answers: Record<string, Answer> }) =>
      surveyService.saveDraft(surveyId, answers),
  });
}

export function useCompletedSurveys(enabled = true) {
  return useQuery({
    queryKey: ['surveys', 'completed'],
    queryFn: surveyService.getCompletedSurveys,
    enabled,
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

export function useManagedSurveys(enabled = true) {
  return useQuery({
    queryKey: ['surveys', 'manage'],
    queryFn: surveyService.getManagedSurveys,
    enabled,
    retry: false,
  });
}

export function useCreateSurvey() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: (payload: NewSurvey) => surveyService.createSurvey(payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      toast.success('Survey Created');
    },
    onError: (err) => handleError(err, 'Could not create the survey. Please check the questions.'),
  });
}

export function useChangeSurveyStatus() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: ({ surveyId, status }: { surveyId: string; status: SurveyStatus }) =>
      surveyService.changeStatus(surveyId, status),
    onSuccess: (_, { status }) => {
      queryClient.invalidateQueries({ queryKey: ['surveys'] });
      toast.success(status === 'active' ? 'Survey Published' : 'Survey Closed');
    },
    onError: (err) => handleError(err, 'Could not change the survey status.'),
  });
}

export function useAssignSurvey() {
  const queryClient = useQueryClient();
  const { handleError } = useErrorHandler();
  return useMutation({
    mutationFn: ({ surveyId, emails, dueDate }: { surveyId: string; emails: string[]; dueDate?: string }) =>
      surveyService.assignSurvey(surveyId, emails, dueDate),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['surveys', 'manage'] }),
    onError: (err) => handleError(err, 'Could not assign the survey.'),
  });
}

export function useSurveyAnalytics(surveyId: string | undefined) {
  return useQuery({
    queryKey: ['surveys', 'analytics', surveyId],
    queryFn: () => surveyService.getAnalytics(surveyId!),
    enabled: !!surveyId,
    retry: false,
  });
}
