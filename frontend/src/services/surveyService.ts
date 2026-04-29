import apiClient from './axiosInterceptor';
import { SURVEYS } from '../lib/api';


export interface SurveyQuestion {
  question_id: string;
  text: string;
  type: 'yes_no' | 'multiple_choice' | 'text' | 'scale';
  options?: string[];
  required: boolean;
}

export interface Survey {
  survey_id: string;
  title: string;
  description?: string;
  trial_id?: string;
  questions: SurveyQuestion[];
}

export interface SurveyListItem {
  survey_id: string;
  title: string;
  description?: string;
  trial_id?: string;
  question_count: number;
}

export interface SurveyResponse {
  question_id: string;
  answer: string | number;
}

export interface SubmitSurveyPayload {
  consent_given: boolean;
  anonymous: boolean;
  responses: SurveyResponse[];
}

export interface CompletedSurvey {
  completion_id: string;
  survey_id: string;
  survey_title: string;
  completed_at: string;
  responses: SurveyResponse[];
}


export const surveyService = {

  async getSurveys(): Promise<SurveyListItem[]> {
    const response = await apiClient.get(SURVEYS.LIST);
    return response.data;
  },

  async getSurveyById(id: string): Promise<Survey> {
    const response = await apiClient.get(SURVEYS.BY_ID(id));
    return response.data;
  },

  async submitSurvey(surveyId: string, payload: SubmitSurveyPayload): Promise<void> {
    await apiClient.post(SURVEYS.SUBMIT(surveyId), payload);
  },

  async getCompletedSurveys(): Promise<CompletedSurvey[]> {
    const response = await apiClient.get(SURVEYS.COMPLETED);
    return response.data;
  },

  async getCompletedSurveyById(completionId: string): Promise<CompletedSurvey> {
    const response = await apiClient.get(SURVEYS.COMPLETED_BY_ID(completionId));
    return response.data;
  },
};