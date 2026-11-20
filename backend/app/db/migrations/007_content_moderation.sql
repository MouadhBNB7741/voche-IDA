-- Migration 007: content moderation
-- Runs on every startup, so every statement is safe to run again.

-- 1. Posts and comments -------------------------------------------------------
-- moderation_status keeps its meaning: pending = held for review, approved = published.
-- New values: draft, hidden (by a moderator, can be restored) and removed (by a moderator).
ALTER TABLE forum_posts DROP CONSTRAINT IF EXISTS check_post_moderation_status;
ALTER TABLE forum_posts ADD CONSTRAINT check_post_moderation_status
    CHECK (moderation_status IN ('draft', 'pending', 'approved', 'flagged', 'hidden', 'removed'));
ALTER TABLE forum_posts ADD COLUMN IF NOT EXISTS moderation_score REAL DEFAULT 0;
ALTER TABLE forum_posts ADD COLUMN IF NOT EXISTS flagged_reason VARCHAR(255);
ALTER TABLE forum_posts ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ;

ALTER TABLE comments DROP CONSTRAINT IF EXISTS check_comment_moderation_status;
ALTER TABLE comments ADD CONSTRAINT check_comment_moderation_status
    CHECK (moderation_status IN ('draft', 'pending', 'approved', 'flagged', 'hidden', 'removed'));
ALTER TABLE comments ADD COLUMN IF NOT EXISTS moderation_score REAL DEFAULT 0;
ALTER TABLE comments ADD COLUMN IF NOT EXISTS flagged_reason VARCHAR(255);
ALTER TABLE comments ADD COLUMN IF NOT EXISTS edited_at TIMESTAMPTZ;

-- 2. Reports: new reasons, statuses and targets (old values stay valid) -------
ALTER TABLE content_reports DROP CONSTRAINT IF EXISTS check_target_type;
ALTER TABLE content_reports ADD CONSTRAINT check_target_type
    CHECK (target_type IN ('post', 'comment', 'user', 'resource'));

ALTER TABLE content_reports DROP CONSTRAINT IF EXISTS check_report_reason;
ALTER TABLE content_reports ADD CONSTRAINT check_report_reason
    CHECK (reason IN ('misinformation', 'harassment', 'spam', 'medical_advice', 'other',
                      'self_harm', 'inappropriate_content'));

ALTER TABLE content_reports DROP CONSTRAINT IF EXISTS check_report_status;
ALTER TABLE content_reports ADD CONSTRAINT check_report_status
    CHECK (status IN ('pending', 'reviewed', 'resolved', 'under_review', 'actioned', 'dismissed'));

-- Who raised the report (a user, or the automatic filter with no reporter) and how urgent it is
ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS source VARCHAR(20) DEFAULT 'user';
ALTER TABLE content_reports DROP CONSTRAINT IF EXISTS check_report_source;
ALTER TABLE content_reports ADD CONSTRAINT check_report_source
    CHECK (source IN ('user', 'auto_filter'));

ALTER TABLE content_reports ADD COLUMN IF NOT EXISTS priority VARCHAR(20) DEFAULT 'normal';
ALTER TABLE content_reports DROP CONSTRAINT IF EXISTS check_report_priority;
ALTER TABLE content_reports ADD CONSTRAINT check_report_priority
    CHECK (priority IN ('normal', 'high', 'critical'));

-- 3. Every moderator decision -------------------------------------------------
CREATE TABLE IF NOT EXISTS moderation_actions (
    action_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    moderator_id UUID REFERENCES users(id) ON DELETE SET NULL,
    target_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    report_id UUID REFERENCES content_reports(report_id) ON DELETE SET NULL,
    target_type VARCHAR(20),
    target_id UUID,
    action_type VARCHAR(30) NOT NULL,
    reason TEXT,
    duration_hours INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_moderation_action_type CHECK (action_type IN (
        'approve_content', 'hide_content', 'delete_content',
        'warn_user', 'suspend_user', 'ban_user'
    ))
);

-- 4. Indexes for the moderation queue and an author's history ---------------
CREATE INDEX IF NOT EXISTS idx_content_reports_status_created ON content_reports(status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_forum_posts_moderation_created ON forum_posts(moderation_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_moderation_actions_target_user ON moderation_actions(target_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_moderation_actions_report ON moderation_actions(report_id);
