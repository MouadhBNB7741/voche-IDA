import { apiClient } from "../lib/apiClient";
import { USERS } from "../lib/api";
import type { User } from "../types/db";

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
} 

export default userService;
