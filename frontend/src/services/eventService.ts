import { apiClient } from '../lib/apiClient';
import { EVENTS } from '../lib/api';
import type { Event, ApiResponse, EventSuggestion } from '../types/db';

export const eventService = {
  getAll: async (): Promise<Event[]> => {
    const response = await apiClient.get<ApiResponse<Event[]>>(EVENTS.LIST);
    return response.data.data;
  },

  getById: async (id: string): Promise<Event> => {
    const response = await apiClient.get<any>(EVENTS.DETAILS(id));
    return response.data?.data ?? response.data;
  },

  register: async (id: string): Promise<void> => {
    await apiClient.post(EVENTS.REGISTER(id));
  },

  cancelRegistration: async (id: string): Promise<void> => {
    await apiClient.delete(EVENTS.REGISTER(id));
  },

  /** Members' suggestions wait for an admin's approval; admins' events are published at once. */
  suggest: async (suggestion: EventSuggestion): Promise<Event> => {
    const response = await apiClient.post<Event>(EVENTS.LIST, suggestion);
    return response.data;
  },
};

export default eventService;