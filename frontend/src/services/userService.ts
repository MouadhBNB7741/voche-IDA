import { apiClient } from "../lib/apiClient";
import { USERS } from "../lib/api";
import type { User } from "../types/db";

export interface OnboardingDetails {
  user_type?: User['user_type'];
  interests?: string[];
  location?: string;
}

export const userService = {

    /**
   * Update profile
   */

  updateProfile: async (data: Partial<User>): Promise<User> => {
    try {
      const response = await apiClient.patch<User>(USERS.ME, data);
      return response.data;
    } catch (err) {
      throw err;
    }
  },

  /**
   * Upload user avatar
   */
  uploadAvatar: async (file: File): Promise<{ success: boolean; message: string; avatar: string }> => {
    try {
      const formData = new FormData();
      formData.append("file", file);
      const response = await apiClient.post<{ success: boolean; message: string; avatar: string }>(
        USERS.ME_AVATAR,
        formData,
        { headers: { "Content-Type": "multipart/form-data" } }
      );
      return response.data;
    } catch (err) {
      throw err;
    }
  },

  /**
   * Delete user avatar
   */
  deleteAvatar: async (): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.delete<{ success: boolean; message: string }>(
        USERS.ME_AVATAR
      );
      return response.data;
    } catch (err) {
      throw err;
    }
  },

  /**
   * Schedule account deletion in 1 week
   */
  deleteAccount: async (): Promise<{ success: boolean; message: string }> => {
    try {
      const response = await apiClient.delete<{ success: boolean; message: string }>(USERS.ME);
      return response.data;
    } catch (err) {
      throw err;
    }
  },

  /**
   * Cancel a scheduled account deletion
   */
  cancelDeletion: async (): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>(USERS.ME_CANCEL_DELETION);
    return response.data;
  },

  /**
   * Finish the onboarding wizard
   */
  completeOnboarding: async (details: OnboardingDetails): Promise<User> => {
    const response = await apiClient.post<User>(USERS.ONBOARDING_COMPLETE, details);
    return response.data;
  },
} 

export default userService;
