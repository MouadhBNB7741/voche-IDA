/**
 * Voche Database Schema & API Types
 * * TRUTH SOURCE: backend/app/db/schema.sql
 * * Standards:
 * 1. Snake_case naming to match PostgreSQL columns and FastAPI responses.
 * 2. Strict type alignment with backend constants and constraints.
 * 3. Dates and Timestamps are represented as strings (ISO 8601) for JSON serialization.
 */

// ============================================================================
// 1. CORE ENUMS & CONSTANTS
// ============================================================================

// User & Auth
export type UserType = 'patient' | 'hcp' | 'org_member' | 'admin';
export type UserStatus = 'active' | 'suspended' | 'pending' | 'deleted';
export type ProfileVisibility = 'public' | 'community_only' | 'private';

// Organizations & Groups
export type OrgType = 'hospital' | 'research_institution' | 'advocacy_group' | 'pharma' | 'other';
export type OrgMembershipStatus = 'pending' | 'partner' | 'affiliated' | 'verified';
export type WorkingGroupType = 'research' | 'advocacy' | 'patient_support';
export type PrivacyLevel = 'public' | 'private' | 'invitation_only';
export type MemberRole = 'admin' | 'moderator' | 'member';
export type MemberStatus = 'pending' | 'approved' | 'rejected';

// Clinical Trials
export type TrialPhase = 'Phase 1' | 'Phase 2' | 'Phase 3' | 'Phase 4' | 'Post-Market';
export type TrialStatus = 'Recruiting' | 'Active' | 'Completed' | 'Suspended' | 'Not yet recruiting';
export type AlertFrequency = 'instant' | 'daily' | 'weekly';
export type SeverityLevel = 'low' | 'medium' | 'high' | 'critical';

// Community & Moderation
export type CommunityType = 'disease_specific' | 'general' | 'hcp_only';
export type ModerationLevel = 'open' | 'pre_moderated' | 'restricted';
export type ModerationStatus = 'pending' | 'approved' | 'flagged' | 'removed';
export type PostType = 'question' | 'story' | 'discussion' | 'announcement';
export type ReportTargetType = 'post' | 'comment' | 'user';
export type ReportReason = 'misinformation' | 'harassment' | 'spam' | 'medical_advice' | 'other';
export type ReportStatus = 'pending' | 'reviewed' | 'resolved';

// Events & Resources
export type EventType = 'webinar' | 'conference' | 'training' | 'roundtable';
export type EventStatus = 'upcoming' | 'ongoing' | 'completed' | 'cancelled';
export type EventRegistrationStatus = 'registered' | 'attended' | 'no_show' | 'cancelled';
export type ResourceType = 'video' | 'document' | 'toolkit' | 'course';

// Surveys
export type SurveyStatus = 'draft' | 'active' | 'closed';
export type QuestionType = 'multiple_choice' | 'scale' | 'open_text' | 'yes_no';

// System
export type NotificationType = 
  | 'trial_match' | 'trial_alert' 
  | 'community_reply' | 'community_like' 
  | 'event_reminder' | 'event_update' 
  | 'org_request_update' | 'resource_update' 
  | 'survey_available' | 'system_announcement';
export type FeedbackCategory = 'platform' | 'trial' | 'patient' | 'feature' | 'bug' | 'other';


// ============================================================================
// 2. DATABASE MODELS
// ============================================================================

// --- USER MANAGEMENT ---
export interface User {
  id: string;
  email: string;
  user_type: UserType;
  display_name: string;
  first_name: string;
  last_name: string;
  country: string | null;
  location: string;
  bio: string;
  interests: string[];
  avatar: string;
  language_preference: string;
  is_verified: boolean;
  is_active: boolean;
  profile_completed: boolean;
  profile_visibility: ProfileVisibility;
  notification_enabled: boolean;
  email_alerts: boolean;
  push_notifications: boolean;
  notification_preferences: {
    frequency: 'instant' | 'daily' | 'weekly';
    emailAlerts: boolean;
    notificationTypes: Record<string, boolean>;
    pushNotifications: boolean;
  };
  verification: {
    role: string;
    status: string;
  };
  created_at: string;
  updated_at: string;
  last_login?: string;
  deletion_scheduled_at?: string | null;
}

export interface UserProfile {
  profile_id: string;
  user_id: string;
  condition?: string;
  specialization?: string;
  license_number?: string;
  organization_id?: string;
  bio?: string;
  interests: string[];
  location?: string;
  profile_visibility: ProfileVisibility;
  show_saved_trials: boolean;
  notification_enabled: boolean;
  email_alerts: boolean;
  push_notifications: boolean;
  created_at: string;
  updated_at: string;
}

export interface PasswordResetToken {
  id: string;
  user_id: string;
  token: string;
  created_at: string;
  expires_at: string;
  used: boolean;
  used_at?: string;
}

// --- ORGANIZATIONS ---
export interface Organization {
  org_id: string;
  org_name: string;
  org_type: OrgType;
  description?: string;
  country: string;
  website?: string;
  logo?: string;
  membership_status: OrgMembershipStatus;
  joined_date: string;
  contact_email: string;
  member_count: number;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMember {
  id: string;
  org_id: string;
  user_id: string;
  role: MemberRole;
  status: MemberStatus;
  joined_at: string;
  updated_at: string;
}

// --- CLINICAL TRIALS ---
export interface ClinicalTrial {
  trial_id: string;
  nct_id?: string;
  title: string;
  summary?: string;
  disease_area: string;
  phase: TrialPhase;
  status: TrialStatus;
  sponsor: string;
  countries: string[];
  eligibility_criteria?: string;
  start_date?: string;
  estimated_completion?: string;
  enrollment: number;
  max_enrollment?: number;
  contact?: string;
  metadata: Record<string, any>;
  last_updated: string;
  created_at: string;
  is_saved?: boolean; // UI Convenience
}

export interface TrialSite {
  site_id: string;
  trial_id: string;
  site_name: string;
  country: string;
  city: string;
  address?: string;
  contact_email?: string;
  contact_phone?: string;
  is_recruiting: boolean;
  created_at: string;
}

export interface TrialSave {
  id: string;
  user_id: string;
  trial_id: string;
  notes?: string;
  saved_at: string;
}

export interface TrialAlert {
  alert_id: string;
  user_id: string;
  trial_id?: string;
  disease_area?: string;
  location?: string;
  phase?: string;
  filter_criteria: Record<string, any>;
  alert_frequency: AlertFrequency;
  last_notified?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ClinicalObservation {
  observation_id: string;
  trial_id: string;
  doctor_id: string;
  summary: string;
  feedback_data: Record<string, any>;
  severity_level: SeverityLevel;
  flagged: boolean;
  created_at: string;
  updated_at: string;
}

// --- COMMUNITY & COLLABORATION ---
export interface Community {
  community_id: string;
  name: string;
  description?: string;
  type: CommunityType;
  icon?: string;
  moderation_level: ModerationLevel;
  member_count: number;
  post_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ForumPost {
  post_id: string;
  user_id: string;
  community_id: string;
  title: string;
  content: string;
  post_type: PostType;
  tags: string[];
  moderation_status: ModerationStatus;
  views_count: number;
  replies_count: number;
  likes_count: number;
  is_pinned: boolean;
  is_locked: boolean;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  author_name?: string; // UI convenience
}

export interface Comment {
  comment_id: string;
  post_id: string;
  user_id: string;
  parent_comment_id?: string;
  content: string;
  likes_count: number;
  moderation_status: ModerationStatus;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

export interface ContentReport {
  report_id: string;
  reporter_id: string;
  target_type: ReportTargetType;
  target_id: string;
  target_content?: string;
  reason: ReportReason;
  description?: string;
  status: ReportStatus;
  moderator_id?: string;
  resolution_notes?: string;
  action_taken?: string;
  created_at: string;
  resolved_at?: string;
}

export interface WorkingGroup {
  group_id: string;
  name: string;
  description?: string;
  type: WorkingGroupType;
  organization_id?: string;
  privacy_level: PrivacyLevel;
  member_count: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface WorkingGroupMember {
  id: string;
  group_id: string;
  user_id: string;
  role: MemberRole;
  status: MemberStatus;
  joined_at: string;
}

// --- EVENTS & RESOURCES ---
export interface Event {
  event_id: string;
  title: string;
  description: string;
  type: EventType;
  organizer: string;
  event_date: string;
  event_time: string;
  timezone: string;
  location?: string;
  virtual_link?: string;
  participants: number;
  max_participants?: number;
  registration_deadline?: string;
  status: EventStatus;
  tags: string[];
  banner_image?: string;
  created_at: string;
  updated_at: string;
  is_registered?: boolean; // UI Convenience
}

export interface EventRegistration {
  registration_id: string;
  event_id: string;
  user_id: string;
  status: EventRegistrationStatus;
  confirmation_sent: boolean;
  registered_at: string;
  updated_at: string;
}

export interface Resource {
  resource_id: string;
  title: string;
  type: ResourceType;
  category: string;
  description: string;
  url?: string;
  language: string;
  duration?: string;
  author?: string;
  organization_id?: string;
  tags: string[];
  published_date?: string;
  downloads: number;
  rating: number;
  featured: boolean;
  requires_auth: boolean;
  created_at: string;
  updated_at: string;
}

export interface ResourceRating {
  rating_id: string;
  resource_id: string;
  user_id: string;
  rating: number;
  review?: string;
  created_at: string;
}

export interface ResourceProgress {
  resource_id: string;
  user_id: string;
  progress: number;
  last_position?: string;
  updated_at: string;
}

// --- SURVEYS & RESEARCH ---
export interface Survey {
  survey_id: string;
  title: string;
  description: string;
  consent_text?: string;
  target_audience: string[];
  estimated_time?: string;
  status: SurveyStatus;
  incentive?: string;
  published_date?: string;
  closing_date?: string;
  created_at: string;
  updated_at: string;
}

export interface SurveyQuestion {
  question_id: string;
  survey_id: string;
  question_text: string;
  question_type: QuestionType;
  order_position: number;
  required: boolean;
  options?: any[]; 
  created_at: string;
}

export interface SurveyCompletion {
  completion_id: string;
  survey_id: string;
  user_id?: string;
  submitted_at: string;
  is_anonymous: boolean;
}

export interface SurveyResponse {
  response_id: string;
  survey_id: string;
  user_id?: string;
  question_id: string;
  completion_id: string;
  answer: any;
  is_anonymous: boolean;
  submitted_at: string;
}

// --- SYSTEM & ENGAGEMENT ---
export interface Notification {
  notification_id: string;
  user_id: string;
  type: NotificationType;
  title: string;
  message: string;
  link?: string;
  read: boolean;
  expires_at?: string;
  created_at: string;
}

export interface UserActivityLog {
  activity_id: string;
  user_id?: string;
  action: string;
  entity_type?: string;
  entity_id?: string;
  metadata: Record<string, any>;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface PlatformFeedback {
  feedback_id: string;
  user_id?: string;
  category: FeedbackCategory;
  message: string;
  rating: number;
  ip_address?: string;
  user_agent?: string;
  created_at: string;
}

export interface DoctorVerification {
  verification_id: string;
  user_id: string;
  license_number: string;
  institution: string;
  country: string;
  specialization: string;
  status: MemberStatus; 
  reviewed_by?: string;
  reviewed_at?: string;
  created_at: string;
  rejection_reason?: string;
}

// ============================================================================
// 3. API REQUEST / RESPONSE SCHEMAS
// ============================================================================

export interface RegisterRequest {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  user_type: UserType;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: 'bearer';
  user_type: UserType;
  message?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  pages: number;
}

export interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
}

export interface ApiError {
  message: string;
  code?: string;
  errors?: Record<string, string[]>;
}

// ============================================================================
// 4. FRONTEND APP STATE
// ============================================================================

export interface AuthState {
  user: User | null;
  profile: UserProfile | null; 
  isLoading: boolean;
  isAuthenticated: boolean;
  error: string | null;
  authStatus: 'idle' | 'pending' | 'success' | 'error';
}

export interface AppState {
  users: User[];
  trials: ClinicalTrial[];
  events: Event[];
  resources: Resource[];
  forumPosts: ForumPost[];
  communities: Community[]; 
  workingGroups: WorkingGroup[]; 
  surveys: Survey[]; 
  notifications: Notification[];
  currentUser: User | null;
  savedTrials: string[]; 
  registeredEvents: string[];
}