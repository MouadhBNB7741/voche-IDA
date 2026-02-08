-- ============================================================================
-- VOCE Platform - Database Schema (MVP)
-- ============================================================================
--
-- Purpose: Create all database tables for the VOCE clinical trials platform
-- Architecture: PostgreSQL 16+ with native async SQL (no ORM)
-- Standards: UUID primary keys, TIMESTAMP WITH TIME ZONE, JSONB for flexibility
--
-- Table Creation Order: Respects foreign key dependencies
-- 1. Core (users, organizations)
-- 2. User profiles and authentication
-- 3. Clinical trials
-- 4. Community and forums
-- 5. Collaboration (working groups)
-- 6. Events and resources
-- 7. Surveys and research
-- 8. System and engagement
--
-- See: docs/conception/dbStrucutre.md for full specification
-- ============================================================================

-- Enable required PostgreSQL extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";      -- UUID generation
CREATE EXTENSION IF NOT EXISTS "pg_trgm";        -- Full-text search support

-- Set timezone to UTC for all timestamps
SET timezone = 'UTC';

-- ============================================================================
-- 1. USER MANAGEMENT
-- ============================================================================

-- -----------------------------------------------------------------------------
-- users: Core identity and access control
-- -----------------------------------------------------------------------------
-- Purpose: Main user authentication and profile data
-- Roles: patient, hcp (healthcare professional), org_member, admin
-- Notes: Email is primary login credential, password_hash uses Argon2/Bcrypt
-- -----------------------------------------------------------------------------

CREATE TABLE users (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Authentication
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    
    -- User Identity
    user_type VARCHAR(50) NOT NULL,              -- patient, hcp, org_member, admin
    display_name VARCHAR(100) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    
    -- Localization
    country VARCHAR(100),
    language_preference VARCHAR(10) DEFAULT 'en',
    
    -- Account Status
    status VARCHAR(50) DEFAULT 'active',          -- active, suspended, pending, deleted
    is_verified BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    profile_completed BOOLEAN DEFAULT FALSE,
    consent_given BOOLEAN DEFAULT FALSE,
    
    -- Profile
    avatar TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_user_type CHECK (user_type IN ('patient', 'hcp', 'org_member', 'admin')),
    CONSTRAINT check_user_status CHECK (status IN ('active', 'suspended', 'pending', 'deleted'))
);

COMMENT ON TABLE users IS 'Core user authentication and identity management';
COMMENT ON COLUMN users.user_type IS 'User role: patient, hcp, org_member, or admin';
COMMENT ON COLUMN users.consent_given IS 'GDPR/HIPAA consent acknowledgment flag';


-- -----------------------------------------------------------------------------
-- password_reset_tokens: Secure password recovery
-- -----------------------------------------------------------------------------
-- Purpose: Manage password reset tokens with expiration
-- Security: Tokens expire after 1 hour, marked as used to prevent reuse
-- Cleanup: Old tokens should be periodically removed via scheduled job
-- -----------------------------------------------------------------------------

CREATE TABLE password_reset_tokens (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User Reference
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Token Details
    token VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    used BOOLEAN DEFAULT FALSE,
    used_at TIMESTAMPTZ
);

COMMENT ON TABLE password_reset_tokens IS 'Password reset tokens with expiration tracking';
COMMENT ON COLUMN password_reset_tokens.expires_at IS 'Token typically expires 1 hour after creation';


-- ============================================================================
-- 2. ORGANIZATIONS (required before user_profiles)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- organizations: Institutional partners and verified organizations
-- -----------------------------------------------------------------------------
-- Purpose: Hospitals, research institutions, advocacy groups, pharma companies
-- Membership: Pending → Partner/Affiliated/Verified
-- -----------------------------------------------------------------------------

CREATE TABLE organizations (
    -- Primary Key
    org_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Organization Details
    org_name VARCHAR(255) UNIQUE NOT NULL,
    org_type VARCHAR(100) NOT NULL,              -- hospital, research_institution, advocacy_group, pharma
    description TEXT,
    country VARCHAR(100) NOT NULL,
    website VARCHAR(255),
    logo VARCHAR(255),
    
    -- Membership
    membership_status VARCHAR(50) DEFAULT 'pending', -- pending, partner, affiliated, verified
    joined_date DATE DEFAULT NOW(),
    contact_email VARCHAR(255) NOT NULL,
    
    -- Statistics
    member_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_org_type CHECK (org_type IN ('hospital', 'research_institution', 'advocacy_group', 'pharma', 'other')),
    CONSTRAINT check_membership_status CHECK (membership_status IN ('pending', 'partner', 'affiliated', 'verified'))
);

COMMENT ON TABLE organizations IS 'Institutional partners and verified organizations';
COMMENT ON COLUMN organizations.membership_status IS 'Organization verification status on platform';


-- -----------------------------------------------------------------------------
-- user_profiles: Extended user information and preferences
-- -----------------------------------------------------------------------------
-- Purpose: One-to-one with users table, stores additional profile data
-- Privacy: profile_visibility controls public display of information
-- Preferences: Notification settings, trial matching preferences
-- -----------------------------------------------------------------------------

CREATE TABLE user_profiles (
    -- Primary Key
    profile_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User Reference (one-to-one)
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Role-Specific Fields
    condition VARCHAR(255),                       -- For patients
    specialization VARCHAR(255),                  -- For HCPs
    license_number VARCHAR(100),                  -- For HCPs
    organization_id UUID REFERENCES organizations(org_id),
    
    -- Profile Content
    bio TEXT,
    interests JSONB DEFAULT '[]',                 -- Array of disease areas/topics
    location VARCHAR(255),                        -- City/region for trial matching
    
    -- Privacy Settings
    profile_visibility VARCHAR(50) DEFAULT 'public', -- public, community_only, private
    show_saved_trials BOOLEAN DEFAULT FALSE,
    
    -- Notification Preferences
    notification_enabled BOOLEAN DEFAULT TRUE,
    email_alerts BOOLEAN DEFAULT TRUE,
    push_notifications BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_profile_visibility CHECK (profile_visibility IN ('public', 'community_only', 'private'))
);

COMMENT ON TABLE user_profiles IS 'Extended user information and preferences (one-to-one with users)';
COMMENT ON COLUMN user_profiles.interests IS 'JSONB array of disease areas/topics user is interested in';
COMMENT ON COLUMN user_profiles.location IS 'Used for geographic matching against trial sites';


-- ============================================================================
-- 3. CLINICAL TRIALS
-- ============================================================================

-- -----------------------------------------------------------------------------
-- clinical_trials: Central registry of clinical trial information
-- -----------------------------------------------------------------------------
-- Purpose: Store trial data from ClinicalTrials.gov and other sources
-- Search: Title and summary are indexed for full-text search
-- Metadata: JSONB field stores additional flexible trial data
-- -----------------------------------------------------------------------------

CREATE TABLE clinical_trials (
    -- Primary Key
    trial_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Trial Identifiers
    nct_id VARCHAR(50) UNIQUE,                    -- ClinicalTrials.gov NCT ID
    
    -- Trial Description  
    title VARCHAR(500) NOT NULL,
    summary TEXT,
    disease_area VARCHAR(255) NOT NULL,
    
    -- Trial Status
    phase VARCHAR(50) NOT NULL,                   -- Phase 1, Phase 2, Phase 3, Phase 4, Post-Market
    status VARCHAR(50) NOT NULL,                  -- Recruiting, Active, Completed, Suspended, Not yet recruiting
    
    -- Organization
    sponsor VARCHAR(255) NOT NULL,
    countries JSONB DEFAULT '[]',                 -- Array of countries where trial runs
    
    -- Eligibility
    eligibility_criteria TEXT,
    
    -- Timeline
    start_date DATE,
    estimated_completion DATE,
    
    -- Enrollment
    enrollment INTEGER DEFAULT 0,
    max_enrollment INTEGER,
    
    -- Contact
    contact VARCHAR(255),
    
    -- Additional Data
    metadata JSONB DEFAULT '{}',                  -- Flexible additional trial data
    
    -- Timestamps
    last_updated TIMESTAMPTZ DEFAULT NOW(),       -- Last data sync/update
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_trial_phase CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Post-Market')),
    CONSTRAINT check_trial_status CHECK (status IN ('Recruiting', 'Active', 'Completed', 'Suspended', 'Not yet recruiting'))
);

COMMENT ON TABLE clinical_trials IS 'Central registry of clinical trial information from various sources';
COMMENT ON COLUMN clinical_trials.nct_id IS 'ClinicalTrials.gov NCT identifier (e.g., NCT04123456)';
COMMENT ON COLUMN clinical_trials.metadata IS 'Flexible JSONB storage for additional trial-specific data';


-- -----------------------------------------------------------------------------
-- trial_sites: Physical locations where trials are conducted
-- -----------------------------------------------------------------------------
-- Purpose: Geographic locations for trials (one trial can have many sites)
-- Matching: Country and city indexed for location-based trial matching
-- -----------------------------------------------------------------------------

CREATE TABLE trial_sites (
    -- Primary Key
    site_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Trial Reference
    trial_id UUID NOT NULL REFERENCES clinical_trials(trial_id) ON DELETE CASCADE,
    
    -- Site Information
    site_name VARCHAR(255) NOT NULL,
    country VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT,
    
    -- Contact
    contact_email VARCHAR(255),
    contact_phone VARCHAR(50),
    
    -- Status
    is_recruiting BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE trial_sites IS 'Physical locations where clinical trials are conducted';
COMMENT ON COLUMN trial_sites.is_recruiting IS 'Whether this specific site is actively recruiting participants';


-- -----------------------------------------------------------------------------
-- trial_saves: User bookmarks for trials
-- -----------------------------------------------------------------------------
-- Purpose: Allow users to save/favorite trials for later review
-- Privacy: Visibility controlled by user_profiles.show_saved_trials
-- Notes: User can add personal notes about why they saved a trial
-- -----------------------------------------------------------------------------

CREATE TABLE trial_saves (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trial_id UUID NOT NULL REFERENCES clinical_trials(trial_id) ON DELETE CASCADE,
    
    -- User Data
    notes TEXT,
    
    -- Timestamps
    saved_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate saves
    CONSTRAINT unique_user_trial_save UNIQUE(user_id, trial_id)
);

COMMENT ON TABLE trial_saves IS 'User bookmarks/favorites for clinical trials';
COMMENT ON COLUMN trial_saves.notes IS 'User''s personal notes about why they saved this trial';


-- -----------------------------------------------------------------------------
-- trial_alerts: User subscriptions for trial notifications
-- -----------------------------------------------------------------------------
-- Purpose: Subscribe to notifications about new trials matching criteria
-- Criteria: Can be trial-specific OR criteria-based (disease, location, phase)
-- Frequency: Instant, daily, or weekly notifications
-- -----------------------------------------------------------------------------

CREATE TABLE trial_alerts (
    -- Primary Key
    alert_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User Reference
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Alert Criteria
    trial_id UUID REFERENCES clinical_trials(trial_id) ON DELETE CASCADE, -- Specific trial (or NULL for criteria-based)
    disease_area VARCHAR(255),
    location VARCHAR(255),
    phase VARCHAR(50),
    filter_criteria JSONB DEFAULT '{}',          -- Additional flexible filters
    
    -- Notification Settings
    alert_frequency VARCHAR(50) DEFAULT 'weekly', -- instant, daily, weekly
    last_notified TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_alert_frequency CHECK (alert_frequency IN ('instant', 'daily', 'weekly'))
);

COMMENT ON TABLE trial_alerts IS 'User subscriptions for trial notifications based on criteria or specific trials';
COMMENT ON COLUMN trial_alerts.filter_criteria IS 'JSONB for flexible additional filtering (e.g., age range, gender)';


-- ============================================================================
-- 4. COMMUNITY & FORUMS
-- ============================================================================

-- -----------------------------------------------------------------------------
-- communities: Forum categories and discussion groups
-- -----------------------------------------------------------------------------
-- Purpose: Organize forums by disease area, topic, or audience type
-- Moderation: Supports open, pre-moderated, or restricted communities
-- Types: disease_specific, general, hcp_only
-- -----------------------------------------------------------------------------

CREATE TABLE communities (
    -- Primary Key
    community_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Community Identity
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,                    -- disease_specific, general, hcp_only
    icon VARCHAR(255),
    
    -- Moderation
    moderation_level VARCHAR(50) DEFAULT 'open',  -- open, pre_moderated, restricted
    
    -- Statistics
    member_count INTEGER DEFAULT 0,
    post_count INTEGER DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_community_type CHECK (type IN ('disease_specific', 'general', 'hcp_only')),
    CONSTRAINT check_moderation_level CHECK (moderation_level IN ('open', 'pre_moderated', 'restricted'))
);

COMMENT ON TABLE communities IS 'Forum categories and discussion groups organized by topic or disease area';
COMMENT ON COLUMN communities.moderation_level IS 'Level of content moderation required before posts appear';


-- -----------------------------------------------------------------------------
-- forum_posts: User-generated discussion threads
-- -----------------------------------------------------------------------------
-- Purpose: Main discussion threads within communities
-- Moderation: Posts can be pending, approved, flagged, or removed
-- Search: Title and content indexed for full-text search
-- Engagement: Tracks views, replies, upvotes/downvotes
-- -----------------------------------------------------------------------------

CREATE TABLE forum_posts (
    -- Primary Key
    post_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL, -- Preserve content if user deleted
    community_id UUID NOT NULL REFERENCES communities(community_id) ON DELETE CASCADE,
    
    -- Post Content
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    post_type VARCHAR(50) DEFAULT 'discussion',   -- question, story, discussion, announcement
    tags JSONB DEFAULT '[]',
    
    -- Moderation
    moderation_status VARCHAR(50) DEFAULT 'approved', -- pending, approved, flagged, removed
    
    -- Engagement Metrics
    views_count INTEGER DEFAULT 0,
    replies_count INTEGER DEFAULT 0,
    upvotes_count INTEGER DEFAULT 0,
    downvotes_count INTEGER DEFAULT 0,
    
    -- Post Flags
    is_pinned BOOLEAN DEFAULT FALSE,              -- Pinned to top of community
    is_locked BOOLEAN DEFAULT FALSE,              -- Prevents new replies
    is_deleted BOOLEAN DEFAULT FALSE,             -- Soft delete
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_post_type CHECK (post_type IN ('question', 'story', 'discussion', 'announcement')),
    CONSTRAINT check_post_moderation_status CHECK (moderation_status IN ('pending', 'approved', 'flagged', 'removed'))
);

COMMENT ON TABLE forum_posts IS 'User-generated discussion threads in communities';
COMMENT ON COLUMN forum_posts.content IS 'Markdown-formatted post content';
COMMENT ON COLUMN forum_posts.is_deleted IS 'Soft delete preserves data for audit trail';


-- -----------------------------------------------------------------------------
-- comments: Replies to forum posts
-- -----------------------------------------------------------------------------
-- Purpose: Allow users to reply to posts and other comments (nested)
-- Threading: parent_comment_id enables nested comment threads
-- Moderation: Comments can be pending, approved, flagged, or removed
-- -----------------------------------------------------------------------------

CREATE TABLE comments (
    -- Primary Key
    comment_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    post_id UUID NOT NULL REFERENCES forum_posts(post_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    parent_comment_id UUID REFERENCES comments(comment_id) ON DELETE CASCADE, -- For nested replies
    
    -- Content
    content TEXT NOT NULL,
    
    -- Engagement
    likes_count INTEGER DEFAULT 0,
    
    -- Moderation
    moderation_status VARCHAR(50) DEFAULT 'approved',
    is_deleted BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_comment_moderation_status CHECK (moderation_status IN ('pending', 'approved', 'flagged', 'removed'))
);

COMMENT ON TABLE comments IS 'Replies to forum posts with support for nested threading';
COMMENT ON COLUMN comments.parent_comment_id IS 'NULL for top-level comments, references another comment for nested replies';


-- -----------------------------------------------------------------------------
-- content_reports: User-flagged content for moderation
-- -----------------------------------------------------------------------------
-- Purpose: Allow users to report inappropriate content
-- Targets: Can report posts, comments, or users
-- Workflow: pending → reviewed → resolved
-- Moderation: Tracks moderator actions and resolution
-- -----------------------------------------------------------------------------

CREATE TABLE content_reports (
    -- Primary Key
    report_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Reporter
    reporter_id UUID NOT NULL REFERENCES users(id) ON DELETE SET NULL,
    
    -- Target
    target_type VARCHAR(50) NOT NULL,             -- post, comment, user
    target_id UUID NOT NULL,
    target_content TEXT,                           -- Snapshot at report time
    
    -- Report Details
    reason VARCHAR(100) NOT NULL,                  -- misinformation, harassment, spam, medical_advice, other
    description TEXT,
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',          -- pending, reviewed, resolved
    
    -- Moderation
    moderator_id UUID REFERENCES users(id),
    resolution_notes TEXT,
    action_taken VARCHAR(100),                     -- approved, removed, warned, banned
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ,
    
    -- Constraints
    CONSTRAINT check_target_type CHECK (target_type IN ('post', 'comment', 'user')),
    CONSTRAINT check_report_reason CHECK (reason IN ('misinformation', 'harassment', 'spam', 'medical_advice', 'other')),
    CONSTRAINT check_report_status CHECK (status IN ('pending', 'reviewed', 'resolved'))
);

COMMENT ON TABLE content_reports IS 'User reports of inappropriate content for moderator review';
COMMENT ON COLUMN content_reports.target_content IS 'Snapshot of reported content preserved for review';


-- ============================================================================
-- 5. COLLABORATION (Working Groups)
-- ============================================================================

-- -----------------------------------------------------------------------------
-- working_groups: Collaborative research and advocacy groups
-- -----------------------------------------------------------------------------
-- Purpose: Allow users to form groups for collaboration
-- Privacy: public, private, or invitation_only
-- Types: research, advocacy, patient_support
-- -----------------------------------------------------------------------------

CREATE TABLE working_groups (
    -- Primary Key
    group_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Group Identity
    name VARCHAR(255) NOT NULL,
    description TEXT,
    type VARCHAR(50) NOT NULL,                    -- research, advocacy, patient_support
    
    -- Organization Reference
    organization_id UUID REFERENCES organizations(org_id),
    
    -- Privacy
    privacy_level VARCHAR(50) DEFAULT 'public',   -- public, private, invitation_only
    
    -- Statistics
    member_count INTEGER DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_group_type CHECK (type IN ('research', 'advocacy', 'patient_support')),
    CONSTRAINT check_privacy_level CHECK (privacy_level IN ('public', 'private', 'invitation_only'))
);

COMMENT ON TABLE working_groups IS 'Collaborative groups for research, advocacy, or patient support';
COMMENT ON COLUMN working_groups.privacy_level IS 'Controls who can see and join the working group';


-- -----------------------------------------------------------------------------
-- organization_members: User membership in organizations
-- -----------------------------------------------------------------------------
-- Purpose: Link users to organizations with roles
-- Roles: admin, moderator, member
-- Status: pending, approved, rejected
-- -----------------------------------------------------------------------------

CREATE TABLE organization_members (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    org_id UUID NOT NULL REFERENCES organizations(org_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Membership Details
    role VARCHAR(50) DEFAULT 'member',            -- admin, moderator, member
    status VARCHAR(50) DEFAULT 'pending',         -- pending, approved, rejected
    
    -- Timestamps
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate memberships
    CONSTRAINT unique_org_user_membership UNIQUE(org_id, user_id),
    
    -- Constraints
    CONSTRAINT check_org_member_role CHECK (role IN ('admin', 'moderator', 'member')),
    CONSTRAINT check_org_member_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

COMMENT ON TABLE organization_members IS 'User memberships in organizations with roles and approval status';


-- -----------------------------------------------------------------------------
-- working_group_members: User membership in working groups
-- -----------------------------------------------------------------------------
-- Purpose: Link users to working groups with roles
-- Roles: admin, moderator, member
-- Status: pending, approved, rejected (for private/invite-only groups)
-- -----------------------------------------------------------------------------

CREATE TABLE working_group_members (
    -- Primary Key
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    group_id UUID NOT NULL REFERENCES working_groups(group_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Membership Details
    role VARCHAR(50) DEFAULT 'member',
    status VARCHAR(50) DEFAULT 'approved',
    
    -- Timestamps
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate memberships
    CONSTRAINT unique_group_user_membership UNIQUE(group_id, user_id),
    
    -- Constraints
    CONSTRAINT check_group_member_role CHECK (role IN ('admin', 'moderator', 'member')),
    CONSTRAINT check_group_member_status CHECK (status IN ('pending', 'approved', 'rejected'))
);

COMMENT ON TABLE working_group_members IS 'User memberships in working groups with roles';


-- ============================================================================
-- 6. EVENTS & RESOURCES
-- ============================================================================

-- -----------------------------------------------------------------------------
-- events: Educational events, webinars, and conferences
-- -----------------------------------------------------------------------------
-- Purpose: Manage platform events and registrations
-- Types: webinar, conference, training, roundtable
-- Location: Physical location or "Virtual" + virtual_link
-- -----------------------------------------------------------------------------

CREATE TABLE events (
    -- Primary Key
    event_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Event Details
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    type VARCHAR(50) NOT NULL,                    -- webinar, conference, training, roundtable
    organizer VARCHAR(255) NOT NULL,
    
    -- Timing
    event_date DATE NOT NULL,
    event_time TIME NOT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    
    -- Location
    location VARCHAR(255),                        -- Physical location or "Virtual"
    virtual_link VARCHAR(500),
    
    -- Capacity
    participants INTEGER DEFAULT 0,
    max_participants INTEGER,
    registration_deadline TIMESTAMPTZ,
    
    -- Status
    status VARCHAR(50) DEFAULT 'upcoming',        -- upcoming, ongoing, completed, cancelled
    
    -- Additional Info
    tags JSONB DEFAULT '[]',
    banner_image VARCHAR(255),
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_event_type CHECK (type IN ('webinar', 'conference', 'training', 'roundtable')),
    CONSTRAINT check_event_status CHECK (status IN ('upcoming', 'ongoing', 'completed', 'cancelled'))
);

COMMENT ON TABLE events IS 'Educational events, webinars, and conferences';
COMMENT ON COLUMN events.virtual_link IS 'Zoom, Teams, or other virtual meeting link';


-- -----------------------------------------------------------------------------
-- event_registrations: User registrations for events
-- -----------------------------------------------------------------------------
-- Purpose: Track who registered for which events
-- Status: registered, attended, no_show, cancelled
-- -----------------------------------------------------------------------------

CREATE TABLE event_registrations (
    -- Primary Key
    registration_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    event_id UUID NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Registration Details
    status VARCHAR(50) DEFAULT 'registered',      -- registered, attended, no_show, cancelled
    confirmation_sent BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Prevent duplicate registrations
    CONSTRAINT unique_event_user_registration UNIQUE(event_id, user_id),
    
    -- Constraints
    CONSTRAINT check_registration_status CHECK (status IN ('registered', 'attended', 'no_show', 'cancelled'))
);

COMMENT ON TABLE event_registrations IS 'User registrations for events with attendance tracking';


-- -----------------------------------------------------------------------------
-- resources: Educational materials and toolkits
-- -----------------------------------------------------------------------------
-- Purpose: Library of educational content
-- Types: video, document, toolkit, course
-- Ratings: Users can rate resources (average stored here)
-- -----------------------------------------------------------------------------

CREATE TABLE resources (
    -- Primary Key
    resource_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Resource Details
    title VARCHAR(500) NOT NULL,
    type VARCHAR(50) NOT NULL,                    -- video, document, toolkit, course
    category VARCHAR(100) NOT NULL,
    description TEXT NOT NULL,
    url VARCHAR(500),
    
    -- Multi-language
    language VARCHAR(10) DEFAULT 'en',
    
    -- Metadata
    duration VARCHAR(50),                         -- For videos or page count for documents
    author VARCHAR(255),
    organization_id UUID REFERENCES organizations(org_id),
    tags JSONB DEFAULT '[]',
    published_date DATE,
    
    -- Engagement
    downloads INTEGER DEFAULT 0,
    rating DECIMAL(3,2) DEFAULT 0.00,            -- Average rating 0.00-5.00
    
    -- Flags
    featured BOOLEAN DEFAULT FALSE,
    requires_auth BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_resource_type CHECK (type IN ('video', 'document', 'toolkit', 'course')),
    CONSTRAINT check_resource_rating CHECK (rating >= 0 AND rating <= 5)
);

COMMENT ON TABLE resources IS 'Educational materials, videos, documents, and toolkits';
COMMENT ON COLUMN resources.rating IS 'Calculated average rating from resource_ratings table';


-- -----------------------------------------------------------------------------
-- resource_ratings: User ratings and reviews for resources
-- -----------------------------------------------------------------------------
-- Purpose: Allow users to rate and review resources
-- Ratings: 1-5 stars with optional text review
-- One rating per user per resource
-- -----------------------------------------------------------------------------

CREATE TABLE resource_ratings (
    -- Primary Key
    rating_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    resource_id UUID NOT NULL REFERENCES resources(resource_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Rating Details
    rating INTEGER NOT NULL,                      -- 1-5 stars
    review TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One rating per user per resource
    CONSTRAINT unique_resource_user_rating UNIQUE(resource_id, user_id),
    
    -- Constraints
    CONSTRAINT check_rating_value CHECK (rating >= 1 AND rating <= 5)
);

COMMENT ON TABLE resource_ratings IS 'User ratings and reviews for educational resources';


-- ============================================================================
-- 7. SURVEYS & RESEARCH
-- ============================================================================

-- -----------------------------------------------------------------------------
-- surveys: Research surveys and feedback instruments
-- -----------------------------------------------------------------------------
-- Purpose: Platform for academic and patient research surveys
-- Status: draft, active, closed
-- Ethics: consent_text must be acknowledged before participation
-- -----------------------------------------------------------------------------

CREATE TABLE surveys (
    -- Primary Key
    survey_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Survey Details
    title VARCHAR(500) NOT NULL,
    description TEXT NOT NULL,
    consent_text TEXT,
    
    -- Targeting
    target_audience JSONB DEFAULT '[]',           -- Array of user types/roles
    estimated_time VARCHAR(50),
    
    -- Status
    status VARCHAR(50) DEFAULT 'draft',           -- draft, active, closed
    
    -- Incentive
    incentive TEXT,
    
    -- Timeline
    published_date DATE,
    closing_date DATE,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_survey_status CHECK (status IN ('draft', 'active', 'closed'))
);

COMMENT ON TABLE surveys IS 'Research surveys and feedback instruments with consent management';
COMMENT ON COLUMN surveys.consent_text IS 'Required consent statement users must acknowledge';


-- -----------------------------------------------------------------------------
-- survey_questions: Individual questions within surveys
-- -----------------------------------------------------------------------------
-- Purpose: Define questions for each survey
-- Types: multiple_choice, scale, open_text, yes_no
-- Order: order_position determines question sequence
-- -----------------------------------------------------------------------------

CREATE TABLE survey_questions (
    -- Primary Key
    question_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Survey Reference
    survey_id UUID NOT NULL REFERENCES surveys(survey_id) ON DELETE CASCADE,
    
    -- Question Details
    question_text TEXT NOT NULL,
    question_type VARCHAR(50) NOT NULL,           -- multiple_choice, scale, open_text, yes_no
    order_position INTEGER NOT NULL,
    required BOOLEAN DEFAULT FALSE,
    
    -- Options (for multiple choice)
    options JSONB,                                 -- Array of available options
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_question_type CHECK (question_type IN ('multiple_choice', 'scale', 'open_text', 'yes_no'))
);

COMMENT ON TABLE survey_questions IS 'Individual questions within surveys with ordering';
COMMENT ON COLUMN survey_questions.options IS 'JSONB array of choices for multiple_choice questions';


-- -----------------------------------------------------------------------------
-- survey_responses: User responses to surveys
-- -----------------------------------------------------------------------------
-- Purpose: Store individual answers to survey questions
-- Privacy: user_id can be NULL for anonymous responses
-- Flexibility: answer stored as JSONB to handle various question types
-- -----------------------------------------------------------------------------

CREATE TABLE survey_responses (
    -- Primary Key
    response_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- References
    survey_id UUID NOT NULL REFERENCES surveys(survey_id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- NULL for anonymous responses
    question_id UUID NOT NULL REFERENCES survey_questions(question_id) ON DELETE CASCADE,
    
    -- Response Data
    answer JSONB NOT NULL,                         -- Flexible format for different question types
    is_anonymous BOOLEAN DEFAULT FALSE,
    
    -- Timestamps
    submitted_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE survey_responses IS 'User responses to survey questions with anonymity support';
COMMENT ON COLUMN survey_responses.answer IS 'JSONB flexible format to handle various answer types';


-- ============================================================================
-- 8. SYSTEM & ENGAGEMENT
-- ============================================================================

-- -----------------------------------------------------------------------------
-- notifications: User notification inbox
-- -----------------------------------------------------------------------------
-- Purpose: In-app notifications for users
-- Types: trial, community, event, system
-- Lifecycle: Created → Delivered → Read
-- Cleanup: Optional expires_at for temporary notifications
-- -----------------------------------------------------------------------------

CREATE TABLE notifications (
    -- Primary Key
    notification_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User Reference
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    
    -- Notification Content
    type VARCHAR(50) NOT NULL,                    -- trial, community, event, system
    title VARCHAR(255) NOT NULL,
    message TEXT NOT NULL,
    link VARCHAR(500),
    
    -- Status
    read BOOLEAN DEFAULT FALSE,
    expires_at TIMESTAMPTZ,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT check_notification_type CHECK (type IN ('trial', 'community', 'event', 'system'))
);

COMMENT ON TABLE notifications IS 'User notification inbox with read status tracking';
COMMENT ON COLUMN notifications.link IS 'Optional deep link to related content';


-- -----------------------------------------------------------------------------
-- user_activity_log: Audit trail and analytics tracking
-- -----------------------------------------------------------------------------
-- Purpose: Track user actions for analytics and security
-- Privacy: Consider GDPR retention policies for logs
-- Usage: Search, views, downloads, registrations, etc.
-- -----------------------------------------------------------------------------

CREATE TABLE user_activity_log (
    -- Primary Key
    activity_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- User Reference
    user_id UUID REFERENCES users(id) ON DELETE SET NULL, -- NULL for anonymous users
    
    -- Action Details
    action VARCHAR(100) NOT NULL,                  -- e.g., search_trial, view_resource, register_event
    entity_type VARCHAR(50),
    entity_id UUID,
    metadata JSONB DEFAULT '{}',                   -- Additional context (e.g., search query)
    
    -- Technical Details
    ip_address VARCHAR(50),
    user_agent TEXT,
    
    -- Timestamps
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE user_activity_log IS 'Audit trail and analytics for user actions on the platform';
COMMENT ON COLUMN user_activity_log.metadata IS 'JSONB for flexible contextual data (e.g., search terms, filters)';
COMMENT ON COLUMN user_activity_log.ip_address IS 'Store with GDPR considerations and retention policy';


-- ============================================================================
-- SCHEMA CREATION COMPLETE
-- ============================================================================

COMMENT ON SCHEMA public IS 'VOCE Platform MVP Schema - See docs/conception/dbStrucutre.md for full specification';
