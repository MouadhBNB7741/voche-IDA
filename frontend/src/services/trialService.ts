import { apiClient } from '../lib/apiClient';
import { CLINICAL } from '../lib/api';
import type {
  AlertFrequency,
  ClinicalTrial,
  ConsentForm,
  Referral,
  PaginatedResponse,
  ScreeningAnswers,
  ScreeningResult,
  TrialPhase,
} from '../types/db';

export const trialService = {

  async getTrials(filters: { 
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
  } = {}): Promise<ClinicalTrial[]> {
    const urlParams = new URLSearchParams();
    
    if (filters.search) urlParams.append('keyword', filters.search);
    if (filters.disease && filters.disease !== 'all') urlParams.append('disease_areas', filters.disease);
    if (filters.phase && filters.phase !== 'all') urlParams.append('phases', filters.phase);
    if (filters.status && filters.status !== 'all') urlParams.append('statuses', filters.status);
    if (filters.location) urlParams.append('location', filters.location);
    if (filters.sponsor) urlParams.append('sponsor', filters.sponsor);
    
    if (filters.page) urlParams.append('page', String(filters.page));
    if (filters.limit) urlParams.append('limit', String(filters.limit));
    if (filters.sort_by) urlParams.append('sort_by', filters.sort_by);
    if (filters.eligibleForMe) urlParams.append('eligible_for_me', 'true');

    const response = await apiClient.get<PaginatedResponse<ClinicalTrial>>(
      CLINICAL.TRIALS,
      { params: urlParams }
    );
    return response.data?.items ?? [];
  },

  async getById(id: string): Promise<ClinicalTrial> {
    const response = await apiClient.get<ClinicalTrial>(CLINICAL.TRIAL_BY_ID(id));
    return response.data;
  },

  async screenEligibility(trialId: string, answers: ScreeningAnswers): Promise<ScreeningResult> {
    const response = await apiClient.post<ScreeningResult>(CLINICAL.SCREEN(trialId), answers);
    return response.data;
  },

  async expressInterest(trialId: string, message?: string): Promise<void> {
    await apiClient.post(CLINICAL.INTEREST(trialId), { message });
  },

  async referPatient(trialId: string, patientEmail: string, clinicalNotes?: string): Promise<Referral> {
    const response = await apiClient.post<Referral>(CLINICAL.REFER(trialId), {
      patient_email: patientEmail,
      clinical_notes: clinicalNotes || undefined,
    });
    return response.data;
  },

  async getSentReferrals(): Promise<Referral[]> {
    return (await apiClient.get<Referral[]>(CLINICAL.REFERRALS_SENT)).data;
  },

  async getReceivedReferrals(): Promise<Referral[]> {
    return (await apiClient.get<Referral[]>(CLINICAL.REFERRALS_RECEIVED)).data;
  },

  async respondToReferral(referralId: string, action: 'accept' | 'decline'): Promise<Referral> {
    return (await apiClient.patch<Referral>(CLINICAL.REFERRAL_RESPOND(referralId), { action })).data;
  },

  async getConsentForm(referralId: string): Promise<ConsentForm> {
    return (await apiClient.get<ConsentForm>(CLINICAL.REFERRAL_CONSENT(referralId))).data;
  },

  async signConsent(referralId: string, version: string, signedName: string): Promise<Referral> {
    return (await apiClient.post<Referral>(CLINICAL.REFERRAL_CONSENT(referralId), {
      version,
      signed_name: signedName,
      agreed: true,
    })).data;
  },

  async createAlert(alert: {
    disease_area?: string;
    location?: string;
    phase?: TrialPhase;
    alert_frequency: AlertFrequency;
  }): Promise<void> {
    await apiClient.post(CLINICAL.ALERTS, alert);
  },
};