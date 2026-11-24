-- Trial managers and patient self-enrollment.
-- Idempotent: init_db re-runs every migration on each startup.
-- managed_by_id: the verified HCP an admin assigns to run a trial; they may change its lifecycle status.
-- trial_referrals.hcp_user_id is NULL when a patient enrolls themselves after the eligibility screener.

ALTER TABLE clinical_trials
    ADD COLUMN IF NOT EXISTS managed_by_id UUID REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_clinical_trials_managed_by ON clinical_trials(managed_by_id);

ALTER TABLE trial_referrals ALTER COLUMN hcp_user_id DROP NOT NULL;
