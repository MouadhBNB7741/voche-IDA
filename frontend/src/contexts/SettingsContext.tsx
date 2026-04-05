import React, { createContext, useContext, useEffect, useState } from 'react';

type NotificationPreferences = {
  newTrials: boolean;
  forumReplies: boolean;
  eventReminders: boolean;
  weeklyDigest: boolean;
  researchUpdates: boolean;
  communityNews: boolean;
};

type PrivacySettings = {
  profileVisible: boolean;
  showLocation: boolean;
  showOrganization: boolean;
  allowMessages: boolean;
  shareActivity: boolean;
};

type SettingsContextType = {
  notifications: NotificationPreferences;
  privacy: PrivacySettings;
  updateNotifications: (updates: Partial<NotificationPreferences>) => void;
  updatePrivacy: (updates: Partial<PrivacySettings>) => void;
};

const defaultNotifications: NotificationPreferences = {
  newTrials: true,
  forumReplies: true,
  eventReminders: true,
  weeklyDigest: false,
  researchUpdates: true,
  communityNews: true,
};

const defaultPrivacy: PrivacySettings = {
  profileVisible: true,
  showLocation: true,
  showOrganization: true,
  allowMessages: true,
  shareActivity: false,
};

const SettingsContext = createContext<SettingsContextType | undefined>(undefined);

export function SettingsProvider({ children }: { children: React.ReactNode }) {
  const [notifications, setNotifications] = useState<NotificationPreferences>(() => {
    const saved = localStorage.getItem('voce_notifications');
    return saved ? JSON.parse(saved) : defaultNotifications;
  });

  const [privacy, setPrivacy] = useState<PrivacySettings>(() => {
    const saved = localStorage.getItem('voce_privacy');
    return saved ? JSON.parse(saved) : defaultPrivacy;
  });

  useEffect(() => {
    localStorage.setItem('voce_notifications', JSON.stringify(notifications));
  }, [notifications]);

  useEffect(() => {
    localStorage.setItem('voce_privacy', JSON.stringify(privacy));
  }, [privacy]);

  const updateNotifications = (updates: Partial<NotificationPreferences>) => {
    setNotifications(prev => ({ ...prev, ...updates }));
  };

  const updatePrivacy = (updates: Partial<PrivacySettings>) => {
    setPrivacy(prev => ({ ...prev, ...updates }));
  };

  return (
    <SettingsContext.Provider value={{ notifications, privacy, updateNotifications, updatePrivacy }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const context = useContext(SettingsContext);
  if (context === undefined) {
    throw new Error('useSettings must be used within a SettingsProvider');
  }
  return context;
}
