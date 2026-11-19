import { apiClient } from '../lib/apiClient';
import { DOCTORS } from '../lib/api';

export interface DoctorVerification {
  verification_id: string;
  license_number: string;
  institution: string;
  country: string;
  specialization: string;
  status: 'pending' | 'approved' | 'rejected';
  created_at: string;
  reviewed_at?: string | null;
  rejection_reason?: string | null;
  issuing_region?: string | null;
  expiration_date?: string | null;
  has_document: boolean;
}

export const doctorService = {
  /**
   * The doctor's latest verification request, or null if there is none.
   */
  getMine: async (): Promise<DoctorVerification | null> => {
    try {
      const response = await apiClient.get<DoctorVerification>(DOCTORS.VERIFICATION);
      return response.data;
    } catch (err: any) {
      if (err?.status === 404) return null;
      throw err;
    }
  },

  /**
   * Submit a licence with its document for admin review.
   */
  submit: async (data: FormData): Promise<DoctorVerification> => {
    const response = await apiClient.post<DoctorVerification>(DOCTORS.VERIFICATION_UPLOAD, data, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 60000,
    });
    return response.data;
  },

  /**
   * Open the private document in a new tab. It needs the login token, so it cannot be a plain link.
   */
  openDocument: async (verificationId: string): Promise<void> => {
    const tab = window.open('', '_blank');
    try {
      const response = await apiClient.get<Blob>(DOCTORS.DOCUMENT(verificationId), { responseType: 'blob' });
      const url = URL.createObjectURL(response.data);
      if (tab) tab.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch (err) {
      tab?.close();
      throw err;
    }
  },
};

export default doctorService;
