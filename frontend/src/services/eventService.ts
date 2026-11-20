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

  /** Ids of the events the logged-in user is registered for. */
  getMyEventIds: async (): Promise<string[]> => {
    const response = await apiClient.get(EVENTS.MY_EVENTS, { params: { limit: 100 } });
    const items: { event_id: string }[] = response.data?.data ?? [];
    return items.map(item => item.event_id);
  },

  /** Members' suggestions wait for an admin's approval; admins' events are published at once. */
  suggest: async (suggestion: EventSuggestion): Promise<Event> => {
    const response = await apiClient.post<Event>(EVENTS.LIST, suggestion);
    return response.data;
  },
};

export default eventService;