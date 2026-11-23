import { apiClient } from "../lib/apiClient";
import { SURVEYS } from '../lib/api';

export type QuestionType =
  | 'single_choice' | 'multiple_choice' | 'scale' | 'open_text' | 'yes_no' | 'number' | 'date';

export type SurveyStatus = 'draft' | 'active' | 'closed';

export type Answer = string | number | string[];

export interface BranchingRule {
  condition: 'equals';
  value: string;
  next_question_id: string;
}

export interface SurveyQuestion {
  question_id: string;
  text: string;
  type: QuestionType;
  options?: string[] | null;
  required: boolean;
  branching_rules: BranchingRule[];
}

export interface Survey {
  survey_id: string;
  title: string;
  description: string;
  consent_text?: string | null;
  estimated_time?: string | null;
  questions: SurveyQuestion[];
  draft_answers?: Record<string, Answer> | null;
}

export interface SurveyListItem {
  survey_id: string;
  title: string;
  description: string;
  estimated_time?: string | null;
  incentive?: string | null;
  status: SurveyStatus;
  already_completed: boolean;
}

export interface AssignedSurvey {
  survey_id: string;
  title: string;
  description: string;
  estimated_time?: string | null;
  status: 'pending' | 'in_progress' | 'completed' | 'expired';
  due_date?: string | null;
  has_draft: boolean;
  trial_title?: string | null;
  assigned_at: string;
}

export interface ManagedSurvey {
  survey_id: string;
  title: string;
  status: SurveyStatus;
  created_at: string;
  closing_date?: string | null;
  question_count: number;
  responses: number;
  assigned: number;
}

export interface SurveyResponse {
  question_id: string;
  answer: Answer;
}

export interface SubmitSurveyPayload {
  consent_given: boolean;
  anonymous: boolean;
  responses: SurveyResponse[];
}

export interface CompletedSurvey {
  completion_id: string;
  survey_id: string;
  title: string;
  submitted_at: string;
}

export interface CompletedSurveyDetail {
  completion_id: string;
  survey_id: string;
  submitted_at: string;
  responses: { question_id: string; question_text: string; answer: Answer }[];
}

export interface NewQuestion {
  text: string;
  type: QuestionType;
  required: boolean;
  options?: string[];
  branching: { value: string; next: number }[];
}

export interface NewSurvey {
  title: string;
  description: string;
  consent_text?: string;
  estimated_time?: string;
  status: SurveyStatus;
  questions: NewQuestion[];
}

export interface AssignResult {
  assigned: string[];
  already_assigned: string[];
  not_found: string[];
}

export interface QuestionAnalytics {
  question_id: string;
  question_text: string;
  question_type: QuestionType;
  answered: number;
  distribution?: Record<string, number> | null;
  average?: number | null;
  min?: number | null;
  max?: number | null;
}

export interface SurveyAnalytics {
  survey_id: string;
  title: string;
  total_responses: number;
  assigned: number;
  completed_assignments: number;
  completion_rate?: number | null;       // % of assignments completed
  avg_completion_hours?: number | null;  // from assignment to submission
  questions: QuestionAnalytics[];
}

export const isEmptyAnswer = (a: Answer | undefined) =>
  a === undefined || a === null || (Array.isArray(a) ? a.length === 0 : String(a).trim() === '');

/** Questions the respondent reaches, in order. Mirrors answer_path on the backend. */
export function answerPath(questions: SurveyQuestion[], answers: Record<string, Answer>): SurveyQuestion[] {
  const position = new Map(questions.map((q, i) => [q.question_id, i]));
  const path: SurveyQuestion[] = [];
  const seen = new Set<string>();
  let i = 0;
  while (i < questions.length) {
    const q = questions[i];
    if (seen.has(q.question_id)) break;
    seen.add(q.question_id);
    path.push(q);
    let next = i + 1;
    const answer = answers[q.question_id];
    if (!isEmptyAnswer(answer)) {
      const given = (Array.isArray(answer) ? answer : [answer]).map(v => String(v).trim().toLowerCase());
      const rule = (q.branching_rules || []).find(r =>
        (r.condition ?? 'equals') === 'equals' &&
        position.has(r.next_question_id) &&
        given.includes(String(r.value).trim().toLowerCase()));
      if (rule) next = position.get(rule.next_question_id)!;
    }
    i = next;
  }
  return path;
}


export const surveyService = {
  async getSurveys(): Promise<SurveyListItem[]> {
    const response = await apiClient.get(SURVEYS.LIST);
    return response.data.data;
  },

  async getSurveyById(id: string): Promise<Survey> {
    const response = await apiClient.get(SURVEYS.BY_ID(id));
    return response.data;
  },

  async submitSurvey(surveyId: string, payload: SubmitSurveyPayload): Promise<void> {
    await apiClient.post(SURVEYS.SUBMIT(surveyId), payload);
  },

  async saveDraft(surveyId: string, answers: Record<string, Answer>): Promise<void> {
    await apiClient.patch(SURVEYS.DRAFT(surveyId), { answers });
  },

  async getAssignedSurveys(): Promise<AssignedSurvey[]> {
    const response = await apiClient.get(SURVEYS.ASSIGNED);
    return response.data;
  },

  async getCompletedSurveys(): Promise<CompletedSurvey[]> {
    const response = await apiClient.get(SURVEYS.COMPLETED);
    return response.data.data;
  },

  async getCompletedSurveyById(completionId: string): Promise<CompletedSurveyDetail> {
    const response = await apiClient.get(SURVEYS.COMPLETED_BY_ID(completionId));
    return response.data;
  },

  async getManagedSurveys(): Promise<ManagedSurvey[]> {
    const response = await apiClient.get(SURVEYS.MANAGE);
    return response.data;
  },

  async createSurvey(payload: NewSurvey): Promise<{ survey_id: string }> {
    const response = await apiClient.post(SURVEYS.CREATE, payload);
    return response.data;
  },

  async changeStatus(surveyId: string, status: SurveyStatus): Promise<void> {
    await apiClient.patch(SURVEYS.STATUS(surveyId), { status });
  },

  async assignSurvey(surveyId: string, patient_emails: string[], due_date?: string): Promise<AssignResult> {
    const response = await apiClient.post(SURVEYS.ASSIGN(surveyId), { patient_emails, due_date: due_date || null });
    return response.data;
  },

  async getAnalytics(surveyId: string): Promise<SurveyAnalytics> {
    const response = await apiClient.get(SURVEYS.ANALYTICS(surveyId));
    return response.data;
  },
};
