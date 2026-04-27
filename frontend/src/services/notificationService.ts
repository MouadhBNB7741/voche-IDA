import { apiClient } from '../lib/apiClient';
import { USERS } from '../lib/api';

export interface NotificationPreferences {
  frequency: 'instant' | 'daily' | 'weekly';
  emailAlerts: boolean;
  notificationTypes: Record<string, boolean>;
  pushNotifications: boolean;
}

export const notificationKeyMap: Record<string, string> = {
  trialMatches: 'trial_match',
  trialAlerts: 'trial_alert',
  communityReplies: 'community_reply',
  communityLikes: 'community_like',
  eventReminders: 'event_reminder',
  eventUpdates: 'event_update',
  resourceUpdates: 'resource_update',
  surveyAvailable: 'survey_available',
  events: 'event_reminder',
  system: 'system_announcement',
};

export const notificationService = {
  /**
   * Get current notification preferences.
   */
  getPreferences: async (): Promise<NotificationPreferences> => {
  try {
    const response = await apiClient.get(USERS.NOTIFICATION_PREFERENCES);
    return response.data?.data?.notification_preferences ?? response.data;
  } catch (err) {
    throw err;
  }
},

/**
   * Update notification preferences.
   */
updatePreferences: async (data: Partial<NotificationPreferences>): Promise<NotificationPreferences> => {
  try {
    const payload = {
      ...data,
      notificationTypes: data.notificationTypes
        ? Object.fromEntries(
            Object.entries(data.notificationTypes).map(([k, v]) => [
              notificationKeyMap[k] || k,
              v,
            ])
          )
        : undefined,
    };
    const response = await apiClient.patch(USERS.NOTIFICATION_PREFERENCES, payload);
    return response.data?.data?.notification_preferences ?? response.data;
  } catch (err) {
    throw err;
  }
},
  
};

export default notificationService;