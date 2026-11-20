-- D1-DB-03: survey branching, new question types and survey assignments.
-- Idempotent: init_db re-runs every migration on each startup.
-- Reuses existing columns: survey_questions.required = is_required,
-- and the existing types 'scale' and 'open_text' cover likert scales and free text.

ALTER TABLE survey_questions
    ADD COLUMN IF NOT EXISTS branching_rules JSONB NOT NULL DEFAULT '[]';
    -- e.g. [{"condition": "equals", "value": "yes", "next_question_id": "<uuid>"}]

ALTER TABLE survey_questions DROP CONSTRAINT IF EXISTS check_question_type;
ALTER TABLE survey_questions ADD CONSTRAINT check_question_type
    CHECK (question_type IN ('single_choice', 'multiple_choice', 'scale', 'open_text', 'yes_no', 'number', 'date'));

CREATE TABLE IF NOT EXISTS survey_assignments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    survey_id UUID NOT NULL REFERENCES surveys(survey_id) ON DELETE CASCADE,
    patient_user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    assigned_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
    trial_id UUID REFERENCES clinical_trials(trial_id) ON DELETE SET NULL,
    due_date TIMESTAMPTZ,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    draft_answers JSONB NOT NULL DEFAULT '{}',    -- {"<question_id>": <answer>} saved while in progress
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_assignment_status CHECK (status IN ('pending', 'in_progress', 'completed', 'expired')),
    CONSTRAINT unique_survey_assignment UNIQUE (survey_id, patient_user_id)
);

CREATE INDEX IF NOT EXISTS idx_survey_assignments_patient ON survey_assignments(patient_user_id, status);
-- Reminder and expiry jobs only look at open assignments.
CREATE INDEX IF NOT EXISTS idx_survey_assignments_open_due ON survey_assignments(due_date)
    WHERE status IN ('pending', 'in_progress');
