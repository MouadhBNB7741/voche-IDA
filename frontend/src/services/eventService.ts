import { apiClient } from '../lib/apiClient';
import { EVENTS } from '../lib/api';
import type { Event, ApiResponse } from '../types/db';

export const eventService = {
  getAll: async (): Promise<Event[]> => {
    const response = await apiClient.get<ApiResponse<Event[]>>(EVENTS.LIST);
    return response.data.data;
  },

  getById: async (id: string): Promise<Event> => {
  const response = await apiClient.get<ApiResponse<Event>>(EVENTS.DETAILS(id));

  if (!response.data?.data) {
    throw new Error('Invalid event response');
  }

  return response.data.data;
  },

  register: async (id: string): Promise<void> => {
    await apiClient.post(EVENTS.REGISTER(id));
  },

  cancelRegistration: async (id: string): Promise<void> => {
    await apiClient.delete(EVENTS.REGISTER(id));
  },
};

export default eventService;