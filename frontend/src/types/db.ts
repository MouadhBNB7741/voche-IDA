export type Role = 'patient' | 'hcp' | 'caregiver' | 'cso' | 'coalition' | 'admin';

export interface User {
    id: string;
    email: string;
    name: string;
    role: Role;
    organization?: string;
    location?: string;
    language?: string;
    avatar?: string;
    bio?: string;
    verified?: boolean;
    createdAt: string;
}

export interface Trial {
    id: string;
    title: string;
    summary: string;
    phase: string;
    status: 'Recruiting' | 'Active' | 'Completed' | 'Not yet recruiting';
    disease: string;
    sponsor: string;
    location: string;
    enrollment: number;
    maxEnrollment: number;
    startDate: string;
    estimatedCompletion: string;
    eligibility: string[];
    contact: string;
    // Senior Dev: Added proper relational fields if needed later, kept flat for MVP
}

export interface Event {
    id: string;
    title: string;
    description: string;
    date: string;
    time: string;
    type: 'webinar' | 'conference' | 'training' | 'roundtable';
    organizer: string;
    participants: number;
    maxParticipants?: number;
    tags: string[];
    location?: string; // virtual or city/country
    distance?: string; // calculated field in frontend usually, but added here for mock compatibility
}

export interface Resource {
    id: string;
    title: string;
    type: 'video' | 'document' | 'toolkit' | 'course';
    category: string;
    description: string;
    url?: string;
    duration?: string;
    language: string;
    downloads?: number;
    rating: number;
    tags?: string[];
    featured?: boolean;
    requiresAuth?: boolean;
    author?: string;
}

export interface ForumPost {
    id: string;
    topicId?: string; // category
    userId: string;
    author: string; // In real DB this is joined, but flat for MVP
    title: string;
    content: string;
    category: string;
    timestamp: string;
    likes: number;
    replies: number; // Count
    tags: string[];
    replyData?: ForumReply[];
}

export interface ForumReply {
    id: string;
    postId: string;
    userId: string;
    author: string;
    content: string;
    timestamp: string;
    likes: number;
}

export interface Notification {
    id: string;
    userId: string;
    type: 'trial' | 'community' | 'event' | 'system';
    title: string;
    message: string;
    time: string; // ISO string preferred in real app, keeping display string for match
    read: boolean;
    link?: string;
}

// Application State Interface
export interface AppState {
    users: User[];
    trials: Trial[];
    events: Event[];
    resources: Resource[];
    forumPosts: ForumPost[];
    notifications: Notification[];
    currentUser: User | null;
    // Relationships/Join tables would be simulated here
    savedTrials: string[]; // Trial IDs
    registeredEvents: string[]; // Event IDs
}