-- Migration 006: account states, onboarding and social sign-in accounts
-- Runs on every startup, so every statement is safe to run again.

-- 1. Users ------------------------------------------------------------------

-- Suspension details. A suspension with no end date is a ban.
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_until TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason TEXT;

-- Set when the user finishes (or skips) the onboarding wizard
ALTER TABLE users ADD COLUMN IF NOT EXISTS onboarding_completed_at TIMESTAMPTZ;

-- Google sign-in users have no password, and pick their role during onboarding
ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL;
ALTER TABLE users ALTER COLUMN user_type DROP NOT NULL;

-- New role: caregiver (same rights as patient)
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_type;
ALTER TABLE users ADD CONSTRAINT check_user_type
    CHECK (user_type IN ('patient', 'caregiver', 'hcp', 'org_member', 'admin'));

-- New state: onboarding (signed in with Google, role not chosen yet)
ALTER TABLE users DROP CONSTRAINT IF EXISTS check_user_status;
ALTER TABLE users ADD CONSTRAINT check_user_status
    CHECK (status IN ('active', 'onboarding', 'suspended', 'pending', 'deleted'));

-- 2. Social sign-in accounts (no Google tokens are stored) ------------------
CREATE TABLE IF NOT EXISTS user_oauth_accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,
    provider_user_id VARCHAR(255) NOT NULL,
    provider_email VARCHAR(255),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_oauth_provider_user UNIQUE (provider, provider_user_id),
    CONSTRAINT check_oauth_provider CHECK (provider IN ('google'))
);
CREATE INDEX IF NOT EXISTS idx_user_oauth_accounts_user ON user_oauth_accounts(user_id);

-- 3. Keep posts, comments and reports when their author's account is removed
-- (their foreign keys are ON DELETE SET NULL, which failed on NOT NULL columns)
ALTER TABLE forum_posts ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE comments ALTER COLUMN user_id DROP NOT NULL;
ALTER TABLE content_reports ALTER COLUMN reporter_id DROP NOT NULL;

-- 4. Doctor verification: the uploaded licence and its details --------------
ALTER TABLE doctor_verifications ADD COLUMN IF NOT EXISTS document_url TEXT;
ALTER TABLE doctor_verifications ADD COLUMN IF NOT EXISTS issuing_region VARCHAR(100);
ALTER TABLE doctor_verifications ADD COLUMN IF NOT EXISTS expiration_date DATE;

-- 5. Notification types for verification results and moderation decisions --
ALTER TABLE notifications DROP CONSTRAINT IF EXISTS check_notification_type;
ALTER TABLE notifications ADD CONSTRAINT check_notification_type CHECK (type IN (
    'trial_match', 'trial_alert',
    'community_reply', 'community_like',
    'event_reminder', 'event_update', 'org_request_update',
    'resource_update', 'survey_available', 'system_announcement',
    'verification_update', 'moderation_action'
));
