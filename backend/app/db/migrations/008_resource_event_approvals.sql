-- Migration 008: approval of submitted resources and suggested events
-- Runs on every startup, so every statement is safe to run again.
-- Existing resources and events default to 'approved' so everything already live stays visible.

-- 1. Resources ----------------------------------------------------------------
ALTER TABLE resources ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'approved';
ALTER TABLE resources DROP CONSTRAINT IF EXISTS check_resource_approval_status;
ALTER TABLE resources ADD CONSTRAINT check_resource_approval_status
    CHECK (approval_status IN ('draft', 'pending', 'approved', 'rejected', 'archived'));

ALTER TABLE resources ADD COLUMN IF NOT EXISTS submitted_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE resources ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE resources ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE resources ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

-- An uploaded file lives in private storage; it is served through the API only once approved
ALTER TABLE resources ADD COLUMN IF NOT EXISTS file_key VARCHAR(500);
ALTER TABLE resources ADD COLUMN IF NOT EXISTS file_name VARCHAR(255);
ALTER TABLE resources ADD COLUMN IF NOT EXISTS file_type VARCHAR(100);
ALTER TABLE resources ADD COLUMN IF NOT EXISTS file_size INTEGER;

CREATE INDEX IF NOT EXISTS idx_resources_approval_created ON resources(approval_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_resources_submitted_by ON resources(submitted_by);

-- 2. Events (events.status keeps upcoming/ongoing/completed/cancelled) -------
ALTER TABLE events ADD COLUMN IF NOT EXISTS approval_status VARCHAR(20) NOT NULL DEFAULT 'approved';
ALTER TABLE events DROP CONSTRAINT IF EXISTS check_event_approval_status;
ALTER TABLE events ADD CONSTRAINT check_event_approval_status
    CHECK (approval_status IN ('pending', 'approved', 'rejected'));

ALTER TABLE events ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE events ADD COLUMN IF NOT EXISTS reviewed_by UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE events ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMPTZ;
ALTER TABLE events ADD COLUMN IF NOT EXISTS rejection_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_events_approval_created ON events(approval_status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_events_created_by ON events(created_by);
