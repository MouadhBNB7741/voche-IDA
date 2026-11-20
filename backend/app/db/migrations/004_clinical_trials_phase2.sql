-- D1-DB-02: trial sync, lifecycle states, structured eligibility, HCP referrals, sync logs.
-- Idempotent: init_db re-runs every migration on each startup.
-- Reuses what the schema already has instead of duplicating it:
--   nct_id = ClinicalTrials.gov id, status = lifecycle state,
--   trial_sites + countries = locations, trial_alerts = alert subscriptions.

ALTER TABLE clinical_trials
    ADD COLUMN IF NOT EXISTS sync_source VARCHAR(50) NOT NULL DEFAULT 'manual',
    ADD COLUMN IF NOT EXISTS last_synced_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS eligibility_rules JSONB NOT NULL DEFAULT '{}';

-- Lifecycle: add Draft (not public yet) and Terminated to the existing states.
ALTER TABLE clinical_trials DROP CONSTRAINT IF EXISTS check_trial_status;
ALTER TABLE clinical_trials ADD CONSTRAINT check_trial_status
    CHECK (status IN ('Draft', 'Not yet recruiting', 'Recruiting', 'Active', 'Completed', 'Suspended', 'Terminated'));

CREATE TABLE IF NOT EXISTS trial_referrals (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    trial_id UUID NOT NULL REFERENCES clinical_trials(trial_id) ON DELETE CASCADE,
    hcp_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    patient_user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    patient_email VARCHAR(255),                   -- for patients without a Voche account yet
    clinical_notes TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'sent',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_referral_status CHECK (status IN ('sent', 'viewed', 'consent_pending', 'enrolled', 'declined', 'ineligible')),
    CONSTRAINT check_referral_patient CHECK (patient_user_id IS NOT NULL OR patient_email IS NOT NULL)
);

CREATE TABLE IF NOT EXISTS trial_sync_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    sync_completed_at TIMESTAMPTZ,
    records_fetched INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(20) NOT NULL DEFAULT 'running',
    error_details TEXT,
    CONSTRAINT check_sync_status CHECK (status IN ('running', 'success', 'failed'))
);

CREATE INDEX IF NOT EXISTS idx_trial_referrals_hcp ON trial_referrals(hcp_user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_trial_referrals_patient ON trial_referrals(patient_user_id);
