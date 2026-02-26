export interface User {
  id: string;
  name: string;
  email: string;
  role: 'patient' | 'caregiver' | 'hcp' | 'cso' | 'coalition';
  organization?: string;
  location: string;
  language: string;
  avatar: string;
  createdAt: string;
}

export interface Trial {
  id: string;
  title: string;
  description: string;
  sponsor: string;
  disease: string;
  phase: string;
  location: string;
  eligibility: string[];
  contact: string;
  enrollment: number;
  maxEnrollment: number;
  startDate: string;
  estimatedCompletion: string;
}

export interface ForumPost {
  id: string;
  title: string;
  content: string;
  author: string;
  category: string;
  replies: number;
  likes: number;
  timestamp: string;
  tags: string[];
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
  distance: string;
}

export interface Resource {
  id: string;
  title: string;
  type: 'video' | 'document' | 'toolkit' | 'course';
  category: string;
  description: string;
  duration?: string;
  language: string;
  downloads?: number;
  rating: number;
}

// Mock current user
export const currentUser: User = {
  id: '1',
  name: 'Maria Rodriguez',
  email: 'maria.rodriguez@email.com',
  role: 'patient',
  location: 'São Paulo, Brazil',
  language: 'Portuguese',
  avatar: '/api/placeholder/40/40',
  createdAt:'2024-01-01',
};

// Mock trials data
export const mockTrials: Trial[] = [
  {
    id: '1',
    title: 'Phase III HIV Prevention Trial',
    description: 'Evaluating the efficacy of new pre-exposure prophylaxis for HIV prevention in high-risk populations.',
    sponsor: 'Global Health Initiative',
    disease: 'HIV/AIDS',
    phase: 'Phase III',
    location: 'São Paulo, Brazil',
    eligibility: ['Age 18-65', 'HIV negative', 'High-risk exposure'],
    contact: 'Dr. Ana Silva - ana.silva@ghi.org',
    enrollment: 450,
    maxEnrollment: 600,
    startDate: '2024-06-01',
    estimatedCompletion: '2026-12-31'
  },
  {
    id: '2',
    title: 'Tuberculosis Drug Resistance Study',
    description: 'Multi-center study investigating new treatment protocols for drug-resistant tuberculosis.',
    sponsor: 'WHO Collaborative Research',
    disease: 'Tuberculosis',
    phase: 'Phase II',
    location: 'Multiple sites - Africa, Asia',
    eligibility: ['Confirmed MDR-TB', 'Age 16+', 'Treatment naive'],
    contact: 'Prof. James Mwangi - j.mwangi@who.int',
    enrollment: 120,
    maxEnrollment: 200,
    startDate: '2024-03-15',
    estimatedCompletion: '2025-09-30'
  },
  {
    id: '3',
    title: 'Malaria Vaccine Efficacy Trial',
    description: 'Testing next-generation malaria vaccine in endemic regions.',
    sponsor: 'PATH Malaria Vaccine Initiative',
    disease: 'Malaria',
    phase: 'Phase III',
    location: 'Accra, Ghana',
    eligibility: ['Age 6 months - 5 years', 'Malaria endemic area', 'Parental consent'],
    contact: 'Dr. Kwame Asante - k.asante@path.org',
    enrollment: 2100,
    maxEnrollment: 3000,
    startDate: '2024-01-10',
    estimatedCompletion: '2026-06-30'
  }
];

// Mock forum posts
export const mockForumPosts: ForumPost[] = [
  {
    id: '1',
    title: 'Navigating Clinical Trial Participation - Your Experience?',
    content: 'I recently joined a Phase III HIV prevention trial and wanted to share my experience and hear from others...',
    author: 'Carlos M.',
    category: 'HIV/AIDS',
    replies: 23,
    likes: 45,
    timestamp: '2 hours ago',
    tags: ['clinical-trials', 'prevention', 'experience']
  },
  {
    id: '2',
    title: 'Understanding Informed Consent: Key Questions to Ask',
    content: 'As someone who has participated in multiple studies, here are the essential questions I always ask...',
    author: 'Dr. Sarah Chen',
    category: 'General',
    replies: 18,
    likes: 67,
    timestamp: '5 hours ago',
    tags: ['informed-consent', 'guidance', 'patient-rights']
  },
  {
    id: '3',
    title: 'TB Treatment Side Effects - Managing Daily Life',
    content: 'Currently on a new TB treatment protocol. Has anyone dealt with similar side effects?',
    author: 'Anonymous User',
    category: 'Tuberculosis',
    replies: 12,
    likes: 28,
    timestamp: '1 day ago',
    tags: ['tuberculosis', 'treatment', 'side-effects']
  }
];

// Mock events
export const mockEvents: Event[] = [
  {
    id: '1',
    title: 'Strengthening Primary Health Care in LMICs',
    description: 'Hosted by PHCC, focusing on scaling equitable access to essential health services.',
    date: '2025-10-15',
    time: '14:00 UTC',
    type: 'webinar',
    organizer: 'Primary Health Care Coalition',
    participants: 245,
    maxParticipants: 500,
    tags: ['primary-care', 'equity', 'global-health'],
    distance:'100km'
  },
  {
    id: '2',
    title: 'Financing Global Infectious Disease Preparedness',
    description: 'Organized by GHFC, with experts discussing sustainable funding mechanisms.',
    date: '2025-11-05',
    time: '16:00 UTC',
    type: 'roundtable',
    organizer: 'Global Health Finance Coalition',
    participants: 89,
    maxParticipants: 150,
    tags: ['financing', 'preparedness', 'policy'],
    distance:'100km'
  },
  {
    id: '3',
    title: 'Informed Consent in Clinical Trials',
    description: 'Led by IDA patient engagement leaders, offering certification for participants.',
    date: '2025-12-01',
    time: '13:00 UTC',
    type: 'training',
    organizer: 'IDA Patient Engagement',
    participants: 156,
    maxParticipants: 300,
    tags: ['consent', 'training', 'certification'],
    distance:'100km'
  },
  {
    id: '4',
    title: 'Global Forum - Vaccine Equity and Access',
    description: 'Multi-stakeholder event exploring challenges and solutions in vaccine rollout across underserved regions.',
    date: '2026-01-20',
    time: '09:00 UTC',
    type: 'conference',
    organizer: 'Global Vaccine Alliance',
    participants: 1240,
    maxParticipants: 2000,
    tags: ['vaccines', 'equity', 'access'],
    distance:'100km'
  },
  {
    id: '5',
    title: 'Annual IDA Conference on Infectious Diseases Advocacy',
    description: 'A flagship hybrid event with panels, networking, and coalition strategy meetings.',
    date: '2026-03-10',
    time: '08:00 UTC',
    type: 'conference',
    organizer: 'International Development Alliance',
    participants: 890,
    maxParticipants: 1500,
    tags: ['advocacy', 'infectious-diseases', 'networking'],
    distance:'100km'
  }
];

// Mock resources
export const mockResources: Resource[] = [
  {
    id: '1',
    title: 'Clinical Trials 101: A Patient\'s Guide',
    type: 'course',
    category: 'Education',
    description: 'Comprehensive introduction to clinical trials, patient rights, and what to expect.',
    duration: '2 hours',
    language: 'English',
    downloads: 1250,
    rating: 4.8
  },
  {
    id: '2',
    title: 'Informed Consent Toolkit for HCPs',
    type: 'toolkit',
    category: 'Professional Development',
    description: 'Best practices and templates for obtaining meaningful informed consent.',
    language: 'Multiple',
    downloads: 890,
    rating: 4.6
  },
  {
    id: '3',
    title: 'Understanding Antimicrobial Resistance',
    type: 'video',
    category: 'Public Health',
    description: 'Expert panel discussion on the global AMR crisis and prevention strategies.',
    duration: '45 minutes',
    language: 'English',
    downloads: 2100,
    rating: 4.9
  },
  {
    id: '4',
    title: 'Community Advocacy Handbook',
    type: 'document',
    category: 'Advocacy',
    description: 'Step-by-step guide for grassroots health advocacy and policy engagement.',
    language: 'English',
    downloads: 567,
    rating: 4.7
  }
];

// Chat responses for AI Assistant
export const mockChatResponses: Record<string, string> = {
  'trials in kenya': 'I found 3 active clinical trials in Kenya focusing on HIV prevention, malaria treatment, and tuberculosis. Would you like me to show you the eligibility criteria for any of these?',
  'join forum': 'To join a forum discussion, go to the Community tab, select your disease area or topic of interest, and click on any post to read and reply. You can also start a new discussion by clicking the "New Post" button.',
  'informed consent': 'Informed consent is your right to understand and agree to participate in research. Key elements include: understanding the study purpose, knowing potential risks and benefits, voluntary participation, and the right to withdraw anytime. Would you like me to explain any specific aspect?',
  'default': 'I\'m here to help you navigate the VOCE platform. You can ask me about finding clinical trials, joining community discussions, accessing educational resources, or understanding your rights as a participant.'
};