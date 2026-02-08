-- ============================================================================
-- VOCE Platform - Database Indexes
-- ============================================================================
--
-- Purpose: Create performance indexes for the VOCE platform
-- Strategy: MVP-level indexing - not over-optimized
-- Focus: Foreign keys, search fields, high-frequency lookups
--
-- Index Types:
-- - B-tree: Default for most lookups (user_id, email, status)
-- - GIN: Full-text search on text/JSONB fields
-- - Unique: Prevent duplicate entries (email, user+trial saves)
--
-- Notes:
-- - All primary key UUIDs are auto-indexed
-- - Foreign keys are indexed for join performance
-- - Partial indexes used where appropriate (e.g., WHERE is_active = TRUE)
--
-- See: docs/conception/dbStrucutre.md for full specification
-- ============================================================================


-- ============================================================================
-- 1. USER MANAGEMENT INDEXES
-- ============================================================================

-- users table
-- Purpose: Fast login lookups, role-based queries, active user filtering
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_user_type ON users(user_type);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_users_created_at ON users(created_at DESC); -- Recent users

COMMENT ON INDEX idx_users_email IS 'Fast login credential lookup';
COMMENT ON INDEX idx_users_user_type IS 'Filter users by role (patient, hcp, admin)';
COMMENT ON INDEX idx_users_status IS 'Query active, suspended, or deleted users';


-- password_reset_tokens table
-- Purpose: Fast token validation, expiry cleanup
CREATE INDEX idx_password_reset_tokens_token ON password_reset_tokens(token);
CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id);
CREATE INDEX idx_password_reset_tokens_expires_at ON password_reset_tokens(expires_at);
CREATE INDEX idx_password_reset_tokens_used ON password_reset_tokens(used) WHERE used = FALSE;

COMMENT ON INDEX idx_password_reset_tokens_token IS 'Fast token lookup for password reset validation';
COMMENT ON INDEX idx_password_reset_tokens_expires_at IS 'Used for cleanup jobs to remove old tokens';


-- user_profiles table
-- Purpose: One-to-one lookups, organization membership queries
CREATE INDEX idx_user_profiles_user_id ON user_profiles(user_id);
CREATE INDEX idx_user_profiles_organization_id ON user_profiles(organization_id);
CREATE INDEX idx_user_profiles_location ON user_profiles(location); -- Trial matching by location

COMMENT ON INDEX idx_user_profiles_location IS 'Geographic matching for trial site proximity';


-- ============================================================================
-- 2. ORGANIZATIONS INDEXES
-- ============================================================================

-- organizations table
-- Purpose: Filter by type, country, verification status
CREATE INDEX idx_organizations_org_type ON organizations(org_type);
CREATE INDEX idx_organizations_country ON organizations(country);
CREATE INDEX idx_organizations_membership_status ON organizations(membership_status);

COMMENT ON INDEX idx_organizations_org_type IS 'Filter hospitals, research institutions, advocacy groups';
COMMENT ON INDEX idx_organizations_membership_status IS 'Find verified/partner organizations';


-- organization_members table
-- Purpose: Lookup members by org or user, check membership status
CREATE INDEX idx_organization_members_org_id ON organization_members(org_id);
CREATE INDEX idx_organization_members_user_id ON organization_members(user_id);
CREATE INDEX idx_organization_members_status ON organization_members(org_id, status);

COMMENT ON INDEX idx_organization_members_org_id IS 'List all members of an organization';
COMMENT ON INDEX idx_organization_members_user_id IS 'Find all organizations a user belongs to';


-- ============================================================================
-- 3. CLINICAL TRIALS INDEXES
-- ============================================================================

-- clinical_trials table
-- Purpose: Search, filter by disease/status/phase, NCT ID lookup
CREATE INDEX idx_clinical_trials_nct_id ON clinical_trials(nct_id);
CREATE INDEX idx_clinical_trials_disease_area ON clinical_trials(disease_area);
CREATE INDEX idx_clinical_trials_status ON clinical_trials(status);
CREATE INDEX idx_clinical_trials_phase ON clinical_trials(phase);
CREATE INDEX idx_clinical_trials_sponsor ON clinical_trials(sponsor);
CREATE INDEX idx_clinical_trials_last_updated ON clinical_trials(last_updated DESC);

-- Full-text search on title and summary
-- Using GIN index with pg_trgm for fuzzy matching
CREATE INDEX idx_clinical_trials_title_search ON clinical_trials USING GIN (title gin_trgm_ops);
CREATE INDEX idx_clinical_trials_summary_search ON clinical_trials USING GIN (summary gin_trgm_ops);

-- JSONB index for countries array
CREATE INDEX idx_clinical_trials_countries ON clinical_trials USING GIN (countries);

COMMENT ON INDEX idx_clinical_trials_nct_id IS 'Fast lookup by ClinicalTrials.gov NCT identifier';
COMMENT ON INDEX idx_clinical_trials_disease_area IS 'Filter trials by disease/condition';
COMMENT ON INDEX idx_clinical_trials_status IS 'Find active/recruiting trials';
COMMENT ON INDEX idx_clinical_trials_title_search IS 'Full-text search on trial titles with fuzzy matching';
COMMENT ON INDEX idx_clinical_trials_countries IS 'Filter trials by country (JSONB array)';


-- trial_sites table
-- Purpose: Geographic filtering, site availability
CREATE INDEX idx_trial_sites_trial_id ON trial_sites(trial_id);
CREATE INDEX idx_trial_sites_country ON trial_sites(country);
CREATE INDEX idx_trial_sites_city ON trial_sites(city);
CREATE INDEX idx_trial_sites_country_city ON trial_sites(country, city); -- Compound for location queries
CREATE INDEX idx_trial_sites_is_recruiting ON trial_sites(trial_id, is_recruiting) WHERE is_recruiting = TRUE;

COMMENT ON INDEX idx_trial_sites_trial_id IS 'Lookup all sites for a trial';
COMMENT ON INDEX idx_trial_sites_country_city IS 'Geographic filtering for trial matching';
COMMENT ON INDEX idx_trial_sites_is_recruiting IS 'Find actively recruiting sites';


-- trial_saves table
-- Purpose: User's saved trials, prevent duplicates
CREATE INDEX idx_trial_saves_user_id ON trial_saves(user_id);
CREATE INDEX idx_trial_saves_trial_id ON trial_saves(trial_id);
CREATE INDEX idx_trial_saves_saved_at ON trial_saves(user_id, saved_at DESC); -- Recent saves

COMMENT ON INDEX idx_trial_saves_user_id IS 'Get all trials saved by a user';
COMMENT ON INDEX idx_trial_saves_trial_id IS 'Find users who saved a specific trial';


-- trial_alerts table
-- Purpose: Active alerts, notification scheduling
CREATE INDEX idx_trial_alerts_user_id ON trial_alerts(user_id);
CREATE INDEX idx_trial_alerts_trial_id ON trial_alerts(trial_id);
CREATE INDEX idx_trial_alerts_is_active ON trial_alerts(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_trial_alerts_disease_area ON trial_alerts(disease_area) WHERE disease_area IS NOT NULL;
CREATE INDEX idx_trial_alerts_alert_frequency ON trial_alerts(alert_frequency, last_notified);

COMMENT ON INDEX idx_trial_alerts_is_active IS 'Find active alert subscriptions for notification jobs';
COMMENT ON INDEX idx_trial_alerts_alert_frequency IS 'Schedule notifications by frequency (instant, daily, weekly)';


-- ============================================================================
-- 4. COMMUNITY & FORUMS INDEXES
-- ============================================================================

-- communities table
-- Purpose: Filter by type, active communities
CREATE INDEX idx_communities_type ON communities(type);
CREATE INDEX idx_communities_is_active ON communities(is_active) WHERE is_active = TRUE;

COMMENT ON INDEX idx_communities_type IS 'Filter disease-specific, general, or HCP-only communities';


-- forum_posts table
-- Purpose: List posts by community/user, search, moderation queue
CREATE INDEX idx_forum_posts_user_id ON forum_posts(user_id);
CREATE INDEX idx_forum_posts_community_id ON forum_posts(community_id);
CREATE INDEX idx_forum_posts_moderation_status ON forum_posts(moderation_status);
CREATE INDEX idx_forum_posts_created_at ON forum_posts(created_at DESC);
CREATE INDEX idx_forum_posts_community_created ON forum_posts(community_id, created_at DESC); -- Recent posts in community
CREATE INDEX idx_forum_posts_is_deleted ON forum_posts(is_deleted) WHERE is_deleted = FALSE;
CREATE INDEX idx_forum_posts_is_pinned ON forum_posts(community_id, is_pinned) WHERE is_pinned = TRUE;

-- Full-text search on title and content
CREATE INDEX idx_forum_posts_title_search ON forum_posts USING GIN (title gin_trgm_ops);
CREATE INDEX idx_forum_posts_content_search ON forum_posts USING GIN (content gin_trgm_ops);

-- JSONB tags index
CREATE INDEX idx_forum_posts_tags ON forum_posts USING GIN (tags);

COMMENT ON INDEX idx_forum_posts_community_created IS 'Get recent posts in a community';
COMMENT ON INDEX idx_forum_posts_moderation_status IS 'Moderation queue (pending/flagged posts)';
COMMENT ON INDEX idx_forum_posts_title_search IS 'Search posts by title';


-- comments table
-- Purpose: Replies to posts, nested threading, user activity
CREATE INDEX idx_comments_post_id ON comments(post_id);
CREATE INDEX idx_comments_user_id ON comments(user_id);
CREATE INDEX idx_comments_parent_comment_id ON comments(parent comment_id);
CREATE INDEX idx_comments_created_at ON comments(post_id, created_at ASC); -- Chronological order
CREATE INDEX idx_comments_is_deleted ON comments(is_deleted) WHERE is_deleted = FALSE;

COMMENT ON INDEX idx_comments_post_id IS 'Get all comments for a post';
COMMENT ON INDEX idx_comments_parent_comment_id IS 'Support nested comment threading';


-- content_reports table
-- Purpose: Moderation queue, report history
CREATE INDEX idx_content_reports_target ON content_reports(target_type, target_id);
CREATE INDEX idx_content_reports_status ON content_reports(status);
CREATE INDEX idx_content_reports_reporter_id ON content_reports(reporter_id);
CREATE INDEX idx_content_reports_moderator_id ON content_reports(moderator_id);
CREATE INDEX idx_content_reports_created_at ON content_reports(created_at DESC);

COMMENT ON INDEX idx_content_reports_target IS 'Find all reports for a specific post/comment/user';
COMMENT ON INDEX idx_content_reports_status IS 'Moderation queue (pending reports)';


-- ============================================================================
-- 5. COLLABORATION (Working Groups) INDEXES
-- ============================================================================

-- working_groups table
-- Purpose: Filter by type, organization, active groups
CREATE INDEX idx_working_groups_organization_id ON working_groups(organization_id);
CREATE INDEX idx_working_groups_type ON working_groups(type);
CREATE INDEX idx_working_groups_is_active ON working_groups(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_working_groups_privacy_level ON working_groups(privacy_level);

COMMENT ON INDEX idx_working_groups_type IS 'Filter by research, advocacy, or patient support groups';


-- working_group_members table
-- Purpose: Membership lookups
CREATE INDEX idx_working_group_members_group_id ON working_group_members(group_id);
CREATE INDEX idx_working_group_members_user_id ON working_group_members(user_id);
CREATE INDEX idx_working_group_members_status ON working_group_members(group_id, status);

COMMENT ON INDEX idx_working_group_members_group_id IS 'List all members of a working group';


-- ============================================================================
-- 6. EVENTS & RESOURCES INDEXES
-- ============================================================================

-- events table
-- Purpose: Upcoming events, filter by type/status
CREATE INDEX idx_events_event_date ON events(event_date);
CREATE INDEX idx_events_type ON events(type);
CREATE INDEX idx_events_status ON events(status);
CREATE INDEX idx_events_upcoming ON events(event_date) WHERE status = 'upcoming';

-- JSONB tags index
CREATE INDEX idx_events_tags ON events USING GIN (tags);

COMMENT ON INDEX idx_events_event_date IS 'List events chronologically';
COMMENT ON INDEX idx_events_upcoming IS 'Partial index for upcoming events only';


-- event_registrations table
-- Purpose: Attendance tracking, user's events
CREATE INDEX idx_event_registrations_event_id ON event_registrations(event_id);
CREATE INDEX idx_event_registrations_user_id ON event_registrations(user_id);
CREATE INDEX idx_event_registrations_status ON event_registrations(event_id, status);

COMMENT ON INDEX idx_event_registrations_event_id IS 'Get all registrations for an event';


-- resources table
-- Purpose: Browse by type/category, search, featured content
CREATE INDEX idx_resources_type ON resources(type);
CREATE INDEX idx_resources_category ON resources(category);
CREATE INDEX idx_resources_language ON resources(language);
CREATE INDEX idx_resources_featured ON resources(featured) WHERE featured = TRUE;
CREATE INDEX idx_resources_organization_id ON resources(organization_id);
CREATE INDEX idx_resources_rating ON resources(rating DESC);

-- JSONB tags index
CREATE INDEX idx_resources_tags ON resources USING GIN (tags);

COMMENT ON INDEX idx_resources_type IS 'Filter by video, document, toolkit, course';
COMMENT ON INDEX idx_resources_featured IS 'Partial index for featured resources';


-- resource_ratings table
-- Purpose: Average rating calculation, user's ratings
CREATE INDEX idx_resource_ratings_resource_id ON resource_ratings(resource_id);
CREATE INDEX idx_resource_ratings_user_id ON resource_ratings(user_id);
CREATE INDEX idx_resource_ratings_rating ON resource_ratings(rating);

COMMENT ON INDEX idx_resource_ratings_resource_id IS 'Calculate average rating per resource';


-- ============================================================================
-- 7. SURVEYS & RESEARCH INDEXES
-- ============================================================================

-- surveys table
-- Purpose: Active surveys, filter by status
CREATE INDEX idx_surveys_status ON surveys(status);
CREATE INDEX idx_surveys_published_date ON surveys(published_date DESC);
CREATE INDEX idx_surveys_active ON surveys(status) WHERE status = 'active';

-- JSONB target_audience index
CREATE INDEX idx_surveys_target_audience ON surveys USING GIN (target_audience);

COMMENT ON INDEX idx_surveys_active IS 'Partial index for active surveys only';


-- survey_questions table
-- Purpose: Questions for a survey, ordered
CREATE INDEX idx_survey_questions_survey_id ON survey_questions(survey_id);
CREATE INDEX idx_survey_questions_order ON survey_questions(survey_id, order_position);

COMMENT ON INDEX idx_survey_questions_order IS 'Return questions in correct order for survey';


-- survey_responses table
-- Purpose: Response analysis, user participation tracking
CREATE INDEX idx_survey_responses_survey_id ON survey_responses(survey_id);
CREATE INDEX idx_survey_responses_user_id ON survey_responses(user_id);
CREATE INDEX idx_survey_responses_question_id ON survey_responses(question_id);
CREATE INDEX idx_survey_responses_submitted_at ON survey_responses(submitted_at DESC);

COMMENT ON INDEX idx_survey_responses_survey_id IS 'Aggregate responses for survey analysis';


-- ============================================================================
-- 8. SYSTEM & ENGAGEMENT INDEXES
-- ============================================================================

-- notifications table
-- Purpose: User inbox, unread notifications, cleanup
CREATE INDEX idx_notifications_user_id ON notifications(user_id);
CREATE INDEX idx_notifications_read ON notifications(user_id, read);
CREATE INDEX idx_notifications_created_at ON notifications(created_at DESC);
CREATE INDEX idx_notifications_expires_at ON notifications(expires_at) WHERE expires_at IS NOT NULL;
CREATE INDEX idx_notifications_unread ON notifications(user_id, created_at DESC) WHERE read = FALSE;

COMMENT ON INDEX idx_notifications_read IS 'Filter read/unread notifications';
COMMENT ON INDEX idx_notifications_unread IS 'Optimized for unread notification queries';


-- user_activity_log table
-- Purpose: Analytics, audit trail, time-series queries
CREATE INDEX idx_user_activity_log_user_id ON user_activity_log(user_id);
CREATE INDEX idx_user_activity_log_action ON user_activity_log(action);
CREATE INDEX idx_user_activity_log_entity ON user_activity_log(entity_type, entity_id);
CREATE INDEX idx_user_activity_log_created_at ON user_activity_log(created_at DESC);
CREATE INDEX idx_user_activity_log_user_action ON user_activity_log(user_id, action, created_at DESC);

-- JSONB metadata index for flexible analytics
CREATE INDEX idx_user_activity_log_metadata ON user_activity_log USING GIN (metadata);

COMMENT ON INDEX idx_user_activity_log_created_at IS 'Time-series analytics queries';
COMMENT ON INDEX idx_user_activity_log_metadata IS 'Analytics on flexible metadata (e.g., search terms)';


-- ============================================================================
-- INDEXES CREATION COMPLETE
-- ============================================================================

-- Performance Statistics
-- Run ANALYZE after index creation to update query planner statistics
ANALYZE;

COMMENT ON SCHEMA public IS 'VOCE Platform - All performance indexes created for MVP';
