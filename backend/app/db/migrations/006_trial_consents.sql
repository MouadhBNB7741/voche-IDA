-- Digital consent for referred patients: one signed consent per referral.
-- Idempotent: init_db re-runs every migration on each startup.

CREATE TABLE IF NOT EXISTS trial_consents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    referral_id UUID NOT NULL UNIQUE REFERENCES trial_referrals(id) ON DELETE CASCADE,
    trial_id UUID NOT NULL REFERENCES clinical_trials(trial_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    consent_version VARCHAR(20) NOT NULL,
    consent_text TEXT NOT NULL,                    -- exact text the patient agreed to
    signed_name VARCHAR(200) NOT NULL,
    signed_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_trial_consents_user ON trial_consents(user_id);
