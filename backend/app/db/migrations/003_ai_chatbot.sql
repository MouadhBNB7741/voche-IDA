-- D1-DB-01: AI chatbot persistence (conversations, messages, feedback).
-- Idempotent: init_db re-runs every migration on each startup.

CREATE TABLE IF NOT EXISTS chat_conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(255),
    context_type VARCHAR(50) NOT NULL DEFAULT 'general',
    context_reference_id UUID,                    -- trial or resource id, depending on context_type
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_chat_context_type CHECK (context_type IN ('general', 'trial_inquiry', 'symptom_guidance', 'resource_qa'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES chat_conversations(id) ON DELETE CASCADE,
    sender_role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    citations JSONB NOT NULL DEFAULT '[]',        -- [{"type": "trial"|"resource", "id": "<uuid>", "title": "..."}]
    token_count INTEGER,
    safety_flagged BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_chat_sender_role CHECK (sender_role IN ('user', 'assistant', 'system'))
);

CREATE TABLE IF NOT EXISTS chat_feedback (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    message_id UUID NOT NULL REFERENCES chat_messages(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    rating SMALLINT NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT check_chat_feedback_rating CHECK (rating IN (-1, 1)),
    CONSTRAINT unique_chat_feedback_per_user UNIQUE (message_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_chat_conversations_user_updated ON chat_conversations(user_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_chat_messages_conv_created ON chat_messages(conversation_id, created_at ASC);
