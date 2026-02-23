import React, { createContext, useContext, useEffect, useReducer } from 'react';
import type { AppState, Event, ForumPost, Notification, Resource, Trial, User } from '../types/db';
import { mockEvents, mockForumPosts, mockResources, mockTrials, currentUser as mockCurrentUser } from '../data/mockData';

// Initial State with Mock Data
const initialState: AppState = {
    users: [mockCurrentUser],
    trials: mockTrials as any as Trial[], // Cast to match new strict types if needed
    events: mockEvents as any as Event[],
    resources: mockResources as any as Resource[],
    forumPosts: mockForumPosts as any as ForumPost[],
    notifications: [
        {
            id: '1',
            userId: '1',
            type: 'trial',
            title: 'New Trial Match Found',
            message: 'A Phase III HIV Prevention trial matches your profile.',
            time: '2 hours ago',
            read: false,
            link: '/trials/1'
        },
        {
            id: '2',
            userId: '1',
            type: 'event',
            title: 'Upcoming Webinar Reminder',
            message: 'The "Strengthening Primary Health Care" webinar starts in 1 hour.',
            time: '1 hour ago',
            read: false,
            link: '/events/1'
        }
    ],
    currentUser: null,
    savedTrials: [],
    registeredEvents: ['1', '3'] // Matches mock logic from EventDetail
};

// Actions
type Action =
    | { type: 'INIT_STORE'; payload: AppState }
    | { type: 'REGISTER_EVENT'; payload: { eventId: string } }
    | { type: 'UNREGISTER_EVENT'; payload: { eventId: string } }
    | { type: 'SAVE_TRIAL'; payload: { trialId: string } }
    | { type: 'UNSAVE_TRIAL'; payload: { trialId: string } }
    | { type: 'ADD_NOTIFICATION'; payload: Notification }
    | { type: 'MARK_NOTIFICATION_READ'; payload: { id: string } }
    | { type: 'MARK_ALL_NOTIFICATIONS_READ' }
    | { type: 'DELETE_NOTIFICATION'; payload: { id: string } }
    | { type: 'CLEAR_NOTIFICATIONS' }
    | { type: 'DELETE_POST'; payload: { postId: string } }
    | { type: 'LIKE_POST'; payload: { postId: string } }
    | { type: 'ADD_POST'; payload: ForumPost };

// Reducer
function dataReducer(state: AppState, action: Action): AppState {
    switch (action.type) {
        case 'INIT_STORE':
            return action.payload;
        case 'REGISTER_EVENT':
            if (state.registeredEvents.includes(action.payload.eventId)) return state;
            return {
                ...state,
                registeredEvents: [...state.registeredEvents, action.payload.eventId]
            };
        case 'UNREGISTER_EVENT':
            return {
                ...state,
                registeredEvents: state.registeredEvents.filter(id => id !== action.payload.eventId)
            };
        case 'SAVE_TRIAL':
            if (state.savedTrials.includes(action.payload.trialId)) return state;
            return {
                ...state,
                savedTrials: [...state.savedTrials, action.payload.trialId]
            };
        case 'UNSAVE_TRIAL':
            return {
                ...state,
                savedTrials: state.savedTrials.filter(id => id !== action.payload.trialId)
            };
        case 'ADD_NOTIFICATION':
            return {
                ...state,
                notifications: [action.payload, ...state.notifications]
            };
        case 'MARK_NOTIFICATION_READ':
            return {
                ...state,
                notifications: state.notifications.map(n =>
                    n.id === action.payload.id ? { ...n, read: true } : n
                )
            };
        case 'MARK_ALL_NOTIFICATIONS_READ':
            return {
                ...state,
                notifications: state.notifications.map(n => ({ ...n, read: true }))
            };
        case 'DELETE_NOTIFICATION':
            return {
                ...state,
                notifications: state.notifications.filter(n => n.id !== action.payload.id)
            };
        case 'CLEAR_NOTIFICATIONS':
            return {
                ...state,
                notifications: []
            };
        case 'DELETE_POST':
            return {
                ...state,
                forumPosts: state.forumPosts.filter(p => p.id !== action.payload.postId)
            };
        case 'ADD_POST':
            return {
                ...state,
                forumPosts: [action.payload, ...state.forumPosts]
            }
        default:
            return state;
    }
}

// Context
interface DataContextType {
    state: AppState;
    dispatch: React.Dispatch<Action>;
    isAdmin: boolean;
    actions: {
        registerEvent: (eventId: string, title?: string) => void;
        unregisterEvent: (eventId: string) => void;
        saveTrial: (trialId: string) => void;
        unsaveTrial: (trialId: string) => void;
        addNotification: (notification: Omit<Notification, 'id' | 'read' | 'userId' | 'time'>) => void;
        markRead: (id: string) => void;
        markAllRead: () => void;
        deleteNotification: (id: string) => void;
        clearNotifications: () => void;
        deletePost: (id: string) => void;
        createPost: (post: Omit<ForumPost, 'id' | 'timestamp' | 'likes' | 'replies' | 'userId'>) => void;
    }
}

const DataContext = createContext<DataContextType | undefined>(undefined);

export function DataProvider({ children }: { children: React.ReactNode }) {
    // Initialize from localStorage or default
    const [state, dispatch] = useReducer(dataReducer, initialState, (defaultState) => {
        const saved = localStorage.getItem('voce_app_state');
        if (saved) {
            try {
                return { ...defaultState, ...JSON.parse(saved) };
            } catch (e) {
                console.error("Failed to load state", e);
                return defaultState;
            }
        }
        return defaultState;
    });

    // Persist to localStorage
    useEffect(() => {
        localStorage.setItem('voce_app_state', JSON.stringify(state));
    }, [state]);

    const actions = {
        registerEvent: (eventId: string, title?: string) => {
            dispatch({ type: 'REGISTER_EVENT', payload: { eventId } });
            dispatch({
                type: 'ADD_NOTIFICATION',
                payload: {
                    id: Date.now().toString(),
                    userId: state.currentUser?.id || 'guest',
                    type: 'event',
                    title: 'Registration Confirmed',
                    message: `You have successfully registered for ${title || 'an event'}.`,
                    time: 'Just now',
                    read: false,
                    link: `/events/${eventId}`
                }
            });
        },
        unregisterEvent: (eventId: string) => {
            dispatch({ type: 'UNREGISTER_EVENT', payload: { eventId } });
        },
        saveTrial: (trialId: string) => {
            dispatch({ type: 'SAVE_TRIAL', payload: { trialId } });
        },
        unsaveTrial: (trialId: string) => {
            dispatch({ type: 'UNSAVE_TRIAL', payload: { trialId } });
        },
        addNotification: (notif: Omit<Notification, 'id' | 'read' | 'userId' | 'time'>) => {
            dispatch({
                type: 'ADD_NOTIFICATION',
                payload: {
                    ...notif,
                    id: Date.now().toString(),
                    userId: state.currentUser?.id || 'guest',
                    read: false,
                    time: 'Just now'
                }
            });
        },
        markRead: (id: string) => dispatch({ type: 'MARK_NOTIFICATION_READ', payload: { id } }),
        markAllRead: () => dispatch({ type: 'MARK_ALL_NOTIFICATIONS_READ' }),
        deleteNotification: (id: string) => dispatch({ type: 'DELETE_NOTIFICATION', payload: { id } }),
        clearNotifications: () => dispatch({ type: 'CLEAR_NOTIFICATIONS' }),
        deletePost: (postId: string) => dispatch({ type: 'DELETE_POST', payload: { postId } }),
        createPost: (post: Omit<ForumPost, 'id' | 'timestamp' | 'likes' | 'replies' | 'userId'>) => {
            dispatch({
                type: 'ADD_POST',
                payload: {
                    ...post,
                    id: Date.now().toString(),
                    userId: state.currentUser?.id || 'guest',
                    timestamp: 'Just now',
                    likes: 0,
                    replies: 0,
                    tags: post.tags || []
                }
            });
        }
    };

    return (
        <DataContext.Provider value={{ state, dispatch, isAdmin: state.currentUser?.role === 'admin', actions }}>
            {children}
        </DataContext.Provider>
    );
}

export function useData() {
    const context = useContext(DataContext);
    if (context === undefined) {
        throw new Error('useData must be used within a DataProvider');
    }
    return context;
}