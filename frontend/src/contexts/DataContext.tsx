import React, { createContext, useContext, useState, useEffect } from 'react';
import type { AppState, User, ClinicalTrial, Event, Resource, ForumPost, Notification, Community, WorkingGroup, Survey } from '../types/db';

interface DataContextType {
  state: AppState;
  actions: {
    setUser: (user: User | null) => void;
    setTrials: (trials: ClinicalTrial[]) => void;
    setEvents: (events: Event[]) => void;
    setResources: (resources: Resource[]) => void;
    setForumPosts: (forumPosts: ForumPost[]) => void;
    setNotifications: (notifications: Notification[]) => void;
    setCommunities: (communities: Community[]) => void;
    setWorkingGroups: (workingGroups: WorkingGroup[]) => void;
    setSurveys: (surveys: Survey[]) => void;
    saveTrial: (trialId: string) => void;
    unsaveTrial: (trialId: string) => void;
    registerEvent: (eventId: string, eventName?: string) => void;
    unregisterEvent: (eventId: string) => void;
    addNotification: (notification: Notification) => void;
    markNotificationAsRead: (notificationId: string) => void;
  };
}

const initialState: AppState = {
  users: [],
  trials: [],
  events: [],
  resources: [],
  forumPosts: [],
  notifications: [],
  communities: [],
  workingGroups: [],
  surveys: [],
  currentUser: null,
  savedTrials: [],
  registeredEvents: []
};

const DataContext = createContext<DataContextType | undefined>(undefined);

export const DataProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, setState] = useState<AppState>(() => {
    const saved = localStorage.getItem('voche_app_state');
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        return { ...initialState, ...parsed };
      } catch (e) {
        return initialState;
      }
    }
    return initialState;
  });

  useEffect(() => {
    localStorage.setItem('voche_app_state', JSON.stringify(state));
  }, [state]);

  const actions = {
    setUser: (user: User | null) => setState(prev => ({ ...prev, currentUser: user })),
    setTrials: (trials: ClinicalTrial[]) => setState(prev => ({ ...prev, trials })),
    setEvents: (events: Event[]) => setState(prev => ({ ...prev, events })),
    setResources: (resources: Resource[]) => setState(prev => ({ ...prev, resources })),
    setForumPosts: (forumPosts: ForumPost[]) => setState(prev => ({ ...prev, forumPosts })),
    setNotifications: (notifications: Notification[]) => setState(prev => ({ ...prev, notifications })),
    setCommunities: (communities: Community[]) => setState(prev => ({ ...prev, communities })),
    setWorkingGroups: (workingGroups: WorkingGroup[]) => setState(prev => ({ ...prev, workingGroups })),
    setSurveys: (surveys: Survey[]) => setState(prev => ({ ...prev, surveys })),
    saveTrial: (trialId: string) => setState(prev => ({
      ...prev,
      savedTrials: prev.savedTrials.includes(trialId) ? prev.savedTrials : [...prev.savedTrials, trialId]
    })),
    unsaveTrial: (trialId: string) => setState(prev => ({
      ...prev,
      savedTrials: prev.savedTrials.filter(id => id !== trialId)
    })),
    registerEvent: (eventId: string, _eventName?: string) => setState(prev => ({
      ...prev,
      registeredEvents: prev.registeredEvents.includes(eventId) ? prev.registeredEvents : [...prev.registeredEvents, eventId]
    })),
    unregisterEvent: (eventId: string) => setState(prev => ({
      ...prev,
      registeredEvents: prev.registeredEvents.filter(id => id !== eventId)
    })),
    addNotification: (notification: Notification) => setState(prev => ({
      ...prev,
      notifications: [notification, ...prev.notifications]
    })),
    markNotificationAsRead: (notificationId: string) => setState(prev => ({
      ...prev,
      notifications: prev.notifications.map(n =>
        n.notification_id === notificationId ? { ...n, read: true } : n
      )
    }))
  };

  return (
    <DataContext.Provider value={{ state, actions }}>
      {children}
    </DataContext.Provider>
  );
};

export const useData = () => {
  const context = useContext(DataContext);
  if (context === undefined) {
    throw new Error('useData must be used within a DataProvider');
  }
  return context;
};
