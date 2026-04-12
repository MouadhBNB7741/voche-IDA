# 🏛 VochePlatform | Phase 2 Database Schema — RBAC & Advanced Systems

> **Architecture:** PERN Stack (PostgreSQL, FastAPI, React, Python)
> **Standards:** Relational Integrity + AI-Ready JSONB + UUID Primary Keys
> **Dependency:** Phase 1 schema must be applied before Phase 2 migrations.

---

## 🛠 Technical Specification

| Feature         | Standard                            |
| :-------------- | :---------------------------------- |
| **Database**    | PostgreSQL 16+                      |
| **Driver**      | asyncpg (raw SQL, parameterized)    |
| **Identity**    | UUID v4                             |
| **Timezone**    | UTC                                 |
| **Flexibility** | JSONB for unstructured data         |

---

## 📋 Table of Contents

### Phase 2 — New Tables

1. [clinical_observations](#clinical_observations)
2. [audit_logs](#audit_logs)
3. [token_blacklist](#token_blacklist)
4. [user_sessions](#user_sessions)

### Phase 2 — Modified Tables

5. [users (modifications)](#users-modifications)
6. [resources (modifications)](#resources-modifications)
7. [events (modifications)](#events-modifications)

### Reference — Phase 1 Tables (Unchanged)

8. [Phase 1 Tables Summary](#phase-1-tables-summary)

---

## Phase 2 — New Tables

---

### `clinical_observations`

*Structured real-world evidence from verified HCPs about clinical trials.*

| Field | Type | Constraints | Notes |
| :---- | :--- | :---------- | :---- |
| 🔑 `observation_id` | `UUID` | `PRIMARY KEY` | Observation identifier (v4) |
| 👤 `doctor_id` | `UUID` | `FOREIGN KEY, NOT NULL` | References `users(id)` ON DELETE CASCADE |
| 🔬 `trial_id` | `UUID` | `FOREIGN KEY, NOT NULL` | References `clinical_trials(trial_id)` ON DELETE CASCADE |
| ⚠️ `severity` | `VARCHAR(50)` | `NOT NULL` | `low`, `medium`, `high`, `critical` |
| 📝 `summary` | `TEXT` | `NOT NULL` | Plain-language observation summary |
| 📦 `data` | `JSONB` | `DEFAULT '{}'` | Structured feedback fields (flexible schema) |
| 🚩 `is_flagged` | `BOOLEAN` | `DEFAULT FALSE` | Auto-set `TRUE` when severity = `critical` |
| 📅 `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Submission timestamp (UTC) |
| 🔄 `updated_at` | `TIMESTAMP` | `DEFAULT NOW()` | Last update timestamp |

**Indexes:**

- `idx_clinical_obs_doctor_id` on `doctor_id`
- `idx_clinical_obs_trial_id` on `trial_id`
- `idx_clinical_obs_severity` on `severity`
- `idx_clinical_obs_is_flagged` on `is_flagged` WHERE `is_flagged = TRUE` (partial index)

**Constraints:**

- `CHECK (severity IN ('low', 'medium', 'high', 'critical'))`
- `FOREIGN KEY (doctor_id) REFERENCES users(id) ON DELETE CASCADE`
- `FOREIGN KEY (trial_id) REFERENCES clinical_trials(trial_id) ON DELETE CASCADE`

**Migration Note:**

```sql
CREATE TABLE IF NOT EXISTS clinical_observations (
    observation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doctor_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    trial_id UUID NOT NULL REFERENCES clinical_trials(trial_id) ON DELETE CASCADE,
    severity VARCHAR(50) NOT NULL CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    summary TEXT NOT NULL,
    data JSONB DEFAULT '{}',
    is_flagged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_clinical_obs_doctor_id ON clinical_observations(doctor_id);
CREATE INDEX idx_clinical_obs_trial_id ON clinical_observations(trial_id);
CREATE INDEX idx_clinical_obs_severity ON clinical_observations(severity);
CREATE INDEX idx_clinical_obs_is_flagged ON clinical_observations(is_flagged) WHERE is_flagged = TRUE;
```

---

### `audit_logs`

*Immutable, append-only record of all security-sensitive platform actions.*

| Field | Type | Constraints | Notes |
| :---- | :--- | :---------- | :---- |
| 🔑 `log_id` | `UUID` | `PRIMARY KEY` | Log entry identifier (v4) |
| 👤 `user_id` | `UUID` | `FOREIGN KEY, NULL` | References `users(id)` ON DELETE SET NULL. NULL for system actions |
| 🎬 `action` | `VARCHAR(100)` | `NOT NULL` | Action name (e.g. `user_suspended`, `hcp_verified`) |
| 🏷️ `target_type` | `VARCHAR(50)` | `NULL` | Entity type: `user`, `trial`, `report`, `resource`, `organization`, `working_group` |
| 🎯 `target_id` | `UUID` | `NULL` | ID of entity acted upon |
| 📦 `metadata` | `JSONB` | `DEFAULT '{}'` | Context: old/new values, reason, notes, filenames |
| 🌐 `ip_address` | `VARCHAR(50)` | `NULL` | Actor's IP address |
| 📅 `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Immutable timestamp (UTC) |

**Indexes:**

- `idx_audit_logs_user_id` on `user_id`
- `idx_audit_logs_action` on `action`
- `idx_audit_logs_target` on (`target_type`, `target_id`)
- `idx_audit_logs_created_at` on `created_at` DESC

**Constraints:**

- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL`

**Important:** This table is **append-only**. Application code must NEVER issue `UPDATE` or `DELETE` on this table. A database-level rule can enforce this:

```sql
CREATE TABLE IF NOT EXISTS audit_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL,
    target_type VARCHAR(50),
    target_id UUID,
    metadata JSONB DEFAULT '{}',
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user_id ON audit_logs(user_id);
CREATE INDEX idx_audit_logs_action ON audit_logs(action);
CREATE INDEX idx_audit_logs_target ON audit_logs(target_type, target_id);
CREATE INDEX idx_audit_logs_created_at ON audit_logs(created_at DESC);

-- Optional: Prevent updates/deletes at DB level
CREATE RULE audit_logs_no_update AS ON UPDATE TO audit_logs DO INSTEAD NOTHING;
CREATE RULE audit_logs_no_delete AS ON DELETE TO audit_logs DO INSTEAD NOTHING;
```

**Logged Actions Reference:**

| Action Value | Trigger | target_type | metadata Contains |
| :----------- | :------ | :---------- | :---------------- |
| `login` | User login | `user` | `{ip, device}` |
| `password_change` | Password update | `user` | `{}` |
| `hcp_verification_submitted` | HCP submits docs | `user` | `{license_number}` |
| `hcp_verified` | Admin approves HCP | `user` | `{admin_id, notes}` |
| `hcp_rejected` | Admin rejects HCP | `user` | `{admin_id, reason}` |
| `user_suspended` | Admin suspends user | `user` | `{admin_id, reason, duration}` |
| `user_unsuspended` | Admin reinstates user | `user` | `{admin_id}` |
| `report_resolved` | Admin resolves report | `report` | `{action, notes, target_type, target_id}` |
| `trial_imported` | Bulk import | `trial` | `{imported, updated, failed, filename}` |
| `trial_created` | Manual trial entry | `trial` | `{trial_id, title}` |
| `trial_updated` | Trial edit | `trial` | `{changed_fields, old_values}` |
| `resource_approved` | Admin publishes resource | `resource` | `{resource_id, notes}` |
| `resource_rejected` | Admin rejects resource | `resource` | `{resource_id, notes}` |
| `content_featured` | Admin features content | varies | `{content_type, content_id, until}` |
| `member_approved` | Org join approved | `organization` | `{user_id, org_id, decided_by}` |
| `member_rejected` | Org join rejected | `organization` | `{user_id, org_id, decided_by, reason}` |
| `working_group_created` | Org admin creates WG | `working_group` | `{group_id, org_id}` |
| `working_group_updated` | Org admin edits WG | `working_group` | `{changed_fields}` |

---

### `token_blacklist`

*Invalidated JWT tokens for logout and session revocation.*

| Field | Type | Constraints | Notes |
| :---- | :--- | :---------- | :---- |
| 🔑 `id` | `UUID` | `PRIMARY KEY` | Record identifier (v4) |
| 🎫 `jti` | `VARCHAR(255)` | `UNIQUE, NOT NULL` | JWT ID claim (`jti`) |
| 👤 `user_id` | `UUID` | `FOREIGN KEY, NOT NULL` | References `users(id)` ON DELETE CASCADE |
| ⏳ `expires_at` | `TIMESTAMP` | `NOT NULL` | Token's original expiry (for row cleanup) |
| 📅 `blacklisted_at` | `TIMESTAMP` | `DEFAULT NOW()` | When token was invalidated |

**Indexes:**

- `idx_token_blacklist_jti` on `jti` (unique — used in auth middleware hot path)
- `idx_token_blacklist_expires_at` on `expires_at` (for cleanup cron)

**Constraints:**

- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `UNIQUE (jti)`

```sql
CREATE TABLE IF NOT EXISTS token_blacklist (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    jti VARCHAR(255) UNIQUE NOT NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMP NOT NULL,
    blacklisted_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_token_blacklist_jti ON token_blacklist(jti);
CREATE INDEX idx_token_blacklist_expires_at ON token_blacklist(expires_at);
```

**Maintenance:** Daily cron job must `DELETE FROM token_blacklist WHERE expires_at < NOW()` to prevent unbounded growth.

---

### `user_sessions`

*Active session tracking for multi-device management.*

| Field | Type | Constraints | Notes |
| :---- | :--- | :---------- | :---- |
| 🔑 `session_id` | `UUID` | `PRIMARY KEY` | Session identifier (v4) |
| 👤 `user_id` | `UUID` | `FOREIGN KEY, NOT NULL` | References `users(id)` ON DELETE CASCADE |
| 🎫 `jti` | `VARCHAR(255)` | `UNIQUE, NOT NULL` | Associated JWT ID claim |
| 🖥️ `device_info` | `VARCHAR(255)` | `NULL` | Parsed User-Agent string |
| 🌐 `ip_address` | `VARCHAR(50)` | `NULL` | Login IP address |
| 📅 `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Session start time |
| 🕒 `last_active` | `TIMESTAMP` | `DEFAULT NOW()` | Last API call timestamp |

**Indexes:**

- `idx_user_sessions_user_id` on `user_id`
- `idx_user_sessions_jti` on `jti` (unique)

**Constraints:**

- `FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE`
- `UNIQUE (jti)`

```sql
CREATE TABLE IF NOT EXISTS user_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    jti VARCHAR(255) UNIQUE NOT NULL,
    device_info VARCHAR(255),
    ip_address VARCHAR(50),
    created_at TIMESTAMP DEFAULT NOW(),
    last_active TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_user_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_user_sessions_jti ON user_sessions(jti);
```

---

## Phase 2 — Modified Tables

---

### `users` (Modifications)

**New Columns:**

| Column | Type | Default | Purpose |
| :----- | :--- | :------ | :------ |
| `suspended_until` | `TIMESTAMP` | `NULL` | Auto-unsuspend date. `NULL` = permanent suspension |
| `suspended_reason` | `TEXT` | `NULL` | Admin-provided reason for suspension |

**Migration:**

```sql
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_until TIMESTAMP NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS suspended_reason TEXT NULL;

CREATE INDEX idx_users_suspended_until ON users(suspended_until)
    WHERE suspended_until IS NOT NULL;
```

**Behavior:**
- On suspend: set `status='suspended'`, `suspended_reason`, and optionally `suspended_until`.
- On each auth request: if `status='suspended'` AND `suspended_until IS NOT NULL` AND `suspended_until < NOW()` → auto-unsuspend (set `status='active'`, clear fields).

---

### `resources` (Modifications)

**New Columns:**

| Column | Type | Default | Purpose |
| :----- | :--- | :------ | :------ |
| `status` | `VARCHAR(50)` | `'published'` | Content approval status: `pending`, `published`, `rejected` |
| `uploaded_by` | `UUID` | `NULL` | FK → `users(id)` — who uploaded the resource |

**Migration:**

```sql
ALTER TABLE resources ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'published'
    CHECK (status IN ('pending', 'published', 'rejected'));
ALTER TABLE resources ADD COLUMN IF NOT EXISTS uploaded_by UUID REFERENCES users(id) ON DELETE SET NULL;

CREATE INDEX idx_resources_status ON resources(status);
CREATE INDEX idx_resources_uploaded_by ON resources(uploaded_by);
```

**Behavior:**
- Existing resources default to `published` (backward compatible).
- Org-uploaded resources are created with `status='pending'` — admin must approve via `PUT /resources/{id}/status`.

---

### `events` (Modifications)

**New Columns:**

| Column | Type | Default | Purpose |
| :----- | :--- | :------ | :------ |
| `reminder_sent` | `BOOLEAN` | `FALSE` | Tracks if 24h reminder notification was sent |

**Migration:**

```sql
ALTER TABLE events ADD COLUMN IF NOT EXISTS reminder_sent BOOLEAN DEFAULT FALSE;
```

**Behavior:**
- Hourly cron checks for events starting within 24 hours where `reminder_sent = FALSE`.
- After sending notifications, set `reminder_sent = TRUE`.

---

## Phase 1 Tables Summary

*These tables remain unchanged. Listed for completeness and cross-referencing.*

| Table | Domain | Phase | Key Relationships |
| :---- | :----- | :---- | :---------------- |
| `users` | User Management | 1 (+ P2 mods) | Central identity. FK target for most tables |
| `user_profiles` | User Management | 1 | 1:1 with `users` |
| `password_reset_tokens` | User Management | 1 | N:1 with `users` |
| `clinical_trials` | Clinical Trials | 1 | FK target for saves, alerts, observations |
| `trial_sites` | Clinical Trials | 1 | N:1 with `clinical_trials` |
| `trial_saves` | Clinical Trials | 1 | M:N bridge: `users` ↔ `clinical_trials` |
| `trial_alerts` | Clinical Trials | 1 | N:1 with `users` |
| `communities` | Community | 1 | FK target for `forum_posts` |
| `forum_posts` | Community | 1 | N:1 with `communities`, `users` |
| `comments` | Community | 1 | N:1 with `forum_posts`, `users` |
| `content_reports` | Community | 1 | Polymorphic: targets posts/comments/users |
| `organizations` | Organizations | 1 | FK target for members, working groups |
| `working_groups` | Organizations | 1 | N:1 with `organizations` |
| `organization_members` | Organizations | 1 | M:N bridge: `users` ↔ `organizations` |
| `working_group_members` | Organizations | 1 | M:N bridge: `users` ↔ `working_groups` |
| `events` | Events | 1 (+ P2 mod) | FK target for registrations |
| `event_registrations` | Events | 1 | M:N bridge: `users` ↔ `events` |
| `resources` | Resources | 1 (+ P2 mods) | N:1 with `organizations` |
| `resource_ratings` | Resources | 1 | M:N bridge: `users` ↔ `resources` |
| `resource_progress` | Resources | 1 | Tracks user completion |
| `surveys` | Surveys | 1 | FK target for questions, responses |
| `survey_questions` | Surveys | 1 | N:1 with `surveys` |
| `survey_responses` | Surveys | 1 | N:1 with `surveys`, `survey_questions` |
| `survey_completions` | Surveys | 1 | N:1 with `surveys`, `users` |
| `notifications` | System | 1 | N:1 with `users` |
| `user_activity_log` | System | 1 | N:1 with `users` |

---

## 📊 Phase 2 Relationships Summary

```
users (1) ←→ (N) clinical_observations   (as doctor_id)
users (1) ←→ (N) audit_logs              (as actor)
users (1) ←→ (N) token_blacklist         (token owner)
users (1) ←→ (N) user_sessions           (session owner)
users (1) ←→ (N) resources               (as uploaded_by)  [P2 new FK]

clinical_trials (1) ←→ (N) clinical_observations

audit_logs → polymorphic via target_type + target_id
    → users, clinical_trials, resources,
      content_reports, organizations, working_groups
```

---

## 🔐 Security & Compliance Notes (Phase 2 Additions)

### Audit Trail Integrity
- `audit_logs` is append-only — `RULE` prevents UPDATE/DELETE at DB level
- All admin actions produce audit records
- IP addresses captured for forensic analysis
- GDPR: audit logs may contain user references — must cascade to SET NULL on user deletion

### Token Security
- `token_blacklist` entries checked on every authenticated request (hot path)
- `jti` column is UNIQUE indexed for O(1) lookup
- Expired blacklist entries cleaned daily to prevent table bloat

### Suspension Architecture
- `suspended_until` allows time-bounded suspensions with auto-recovery
- Middleware enforces suspension check — no bypasses possible
- All user tokens blacklisted on suspension (immediate effect)

---

## 🚀 Migration Execution Order

Apply Phase 2 migrations in this order to respect foreign key dependencies:

```
1. ALTER TABLE users      → Add suspended_until, suspended_reason
2. ALTER TABLE resources  → Add status, uploaded_by
3. ALTER TABLE events     → Add reminder_sent
4. CREATE TABLE audit_logs
5. CREATE TABLE token_blacklist
6. CREATE TABLE user_sessions
7. CREATE TABLE clinical_observations
8. CREATE INDEXES (all new indexes)
9. CREATE RULES (audit_logs protection)
```

> **Note:** All migrations use `IF NOT EXISTS` / `IF NOT EXISTS` guards for idempotency.

---

> **Document Version:** 1.0
> **Last Updated:** 2026-03-22
> **Status:** Ready for Engineering Implementation
