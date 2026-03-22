# 🏗️ VOCE Backend — Phase 2: RBAC & Advanced Systems

> **Document Purpose:** This is the production-readiness specification for the VOCE backend. Phase 2 transforms the working MVP into a fully governed, role-enforced, enterprise-grade platform ready for real-world deployment.
>
> **Prerequisite:** All MVP modules are implemented and tested (see `progress.md`).
>
> **Stack:** Python (FastAPI) · PostgreSQL 16+ · asyncpg · Pydantic · JWT

---

## 1. Overview

### What Phase 2 Is

Phase 2 is the **system expansion layer** that sits on top of the working MVP. While the MVP proved the platform works (auth, trials, community, events, surveys, resources, organizations), Phase 2 makes it **production-ready** by adding:

1. **RBAC (Role-Based Access Control)** — Formal enforcement of who can do what, at every endpoint
2. **Admin Governance** — Complete administrative tooling for platform oversight
3. **HCP System** — Full healthcare professional lifecycle (verification → clinical tools → exclusive access)
4. **Organization Management** — Membership approval workflows, working group leadership
5. **Analytics & Intelligence** — Platform health metrics, usage patterns, data-driven decisions
6. **Advanced Notifications** — Background jobs, scheduled alerts, event reminders

### What Phase 2 Is NOT

- ❌ Not a rewrite of MVP endpoints
- ❌ Not real-time chat, payment processing, or mobile native apps
- ❌ Not EHR/FHIR integration (deferred to Phase 3)
- ❌ Not advanced AI/LLM features (deferred to Phase 3)

### Success Criteria

After Phase 2 completion:
- Every endpoint enforces role-based access control
- Platform admins have full governance capability
- HCPs have a complete verification-to-access pipeline
- Organizations can self-manage membership
- All critical actions produce audit trails
- Platform analytics are available for strategic decisions

---

## 2. Role-Based Access Control (RBAC)

### 2.1 Role Definitions

| Role | `user_type` Value | Description | Granted By |
|:-----|:------------------|:------------|:-----------|
| **Patient** | `patient` | Default user. Browses trials, joins communities, completes surveys. | Self-registration |
| **Caregiver** | `caregiver` | Same as Patient. Acts on behalf of a care recipient. | Self-registration |
| **Healthcare Professional (HCP)** | `hcp` | Elevated clinical access. Locked behind `is_verified = TRUE`. | Admin approval via verification flow |
| **Organization Member** | `org_member` | Belongs to a partner organization. Can contribute resources. | Self-registration + org admin approval |
| **Organization Admin** | `org_member` + `role='admin'` in `organization_members` | Manages a specific organization's membership and working groups. | Promoted by Platform Admin |
| **Platform Admin** | `admin` | Global governer. Moderates content, verifies HCPs, manages trials, views analytics. | Database-level or Super Admin |

### 2.2 Role Hierarchy

```
Platform Admin (God Mode)
  └── Organization Admin (Scoped to their org_id)
        └── Organization Member (Scoped participation)
  └── HCP (Verified) → Inherits Patient + clinical tools
        └── HCP (Unverified) → Same as Patient until approved
  └── Patient / Caregiver (Base tier)
```

**Key Rule:** Higher roles **inherit** all permissions of lower roles. An HCP can do everything a Patient can do, plus HCP-specific actions. A Platform Admin can do everything.

### 2.3 Permissions Matrix

| Permission | Patient | Caregiver | HCP (Unverified) | HCP (Verified) | Org Member | Org Admin | Platform Admin |
|:-----------|:-------:|:---------:|:-----------------:|:--------------:|:----------:|:---------:|:--------------:|
| Register / Login | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manage own profile | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Search trials | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Save/bookmark trials | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Express trial interest | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Create trial alerts | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Browse communities | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Post in public communities | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Post in HCP-only communities | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Report content | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Register for events | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Download resources | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Complete surveys | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Request HCP verification | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ |
| Submit clinical observations | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Access HCP-only resources | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| Upload org resources | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ |
| Approve/reject org join requests | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Create/edit working groups | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Verify HCPs | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Suspend/ban users | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Moderate content | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Import/create/edit trials | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Approve uploaded resources | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| View platform analytics | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |

### 2.4 Middleware Stack

All middleware lives in `app/api/middleware/` and is composable.

#### `auth_required` (Existing — Harden)
```python
# File: app/api/middleware/auth_middleware.py
# Already implemented. Validates JWT, injects user_id into request.
# Phase 2: Add suspended-user check → 403 if users.status == 'suspended'
```

#### `verified_hcp_required` (NEW)
```python
# File: app/api/middleware/hcp_middleware.py
# Logic:
# 1. Call auth_required first
# 2. Check users.user_type == 'hcp'
# 3. Check users.is_verified == TRUE
# 4. If not verified → 403 {"detail": "HCP verification required"}
# 5. If not HCP → 403 {"detail": "HCP role required"}
```

#### `org_admin_required` (Existing — Extend)
```python
# File: app/api/middleware/org_admin_middleware.py
# Already implemented. Phase 2 enhancements:
# 1. Extract org_id from path params
# 2. Check: user is Platform Admin (user_type == 'admin') → PASS
# 3. OR: user has organization_members record with role='admin' AND status='approved' for this org_id → PASS
# 4. Else → 403 {"detail": "Organization admin access required"}
```

#### `admin_required` (NEW)
```python
# File: app/api/middleware/admin_middleware.py
# Logic:
# 1. Call auth_required first
# 2. Check users.user_type == 'admin'
# 3. If not admin → 403 {"detail": "Platform admin access required"}
# 4. Log admin action to audit_logs table
```

---

## 3. Phase 2 Modules — Complete Action Tables

> **Format:** Every action has a defined Actor, Action, Endpoint, Tables touched, and System Logic. This is the implementation contract.

---

### 🔐 MODULE 1: Advanced Auth & Security

**Goal:** Session hardening, role validation enforcement, audit trail, and token lifecycle management.

| Actor | Action | Endpoint | Tables | Logic |
|:------|:-------|:---------|:-------|:------|
| **System** | Enforce suspended check | All authenticated endpoints | `users` | Middleware reads `users.status`. If `suspended` → 403 with suspension reason and `suspended_until` date. Applied globally via `auth_required` middleware upgrade. |
| **System** | Enforce role validation | Role-gated endpoints | `users`, `organization_members` | Each middleware checks `user_type` + supplementary flags (`is_verified`, org membership `role`). Reject with specific 403 message. |
| **User** 🔒 | Logout (token invalidation) | `POST /auth/logout` | `token_blacklist` | 1. Extract JWT `jti` claim. 2. Insert into `token_blacklist` with `expires_at`. 3. Return 200. Middleware checks blacklist on every request. |
| **User** 🔒 | List active sessions | `GET /auth/sessions` | `user_sessions` | Return device info, IP, last_active for all active sessions. Ordered by `last_active DESC`. |
| **User** 🔒 | Revoke session | `DELETE /auth/sessions/{session_id}` | `user_sessions`, `token_blacklist` | 1. Verify ownership. 2. Blacklist associated token. 3. Delete session record. |
| **System** | Write audit log | Internal (called by middleware) | `audit_logs` | Auto-logged for: login, password change, role change, admin actions, HCP verification decisions, user suspension. Captures `user_id`, `action`, `target_type`, `target_id`, `metadata` (JSONB), `ip_address`, `timestamp`. |
| **System** | Cleanup expired tokens | Cron (daily) | `password_reset_tokens`, `token_blacklist` | Delete rows where `expires_at < NOW()`. Prevents table bloat. |

**New Middleware Behavior for `auth_required`:**
```
1. Extract JWT from Authorization header
2. Verify JWT signature and expiration
3. Check jti NOT in token_blacklist → 401 if blacklisted
4. Fetch users.status → 403 if 'suspended' or 'deleted'
5. Inject user_id, user_type, is_verified into request state
```

---

### 🩺 MODULE 2: HCP System

**Goal:** Complete healthcare professional lifecycle — from credential submission to clinical tool access.

**Prerequisite:** `verified_hcp_required` middleware must be implemented.

| Actor | Action | Endpoint | Tables | Logic |
|:------|:-------|:---------|:-------|:------|
| **HCP** 🔒 | Submit verification request | `POST /doctors/verification` | `users` (verification JSONB), `audit_logs` | 1. Require `user_type IN ('hcp', 'patient')`. 2. Check no existing `pending` request. 3. Store as `verification = {"status": "pending", "license_number": ..., "institution": ..., "country": ..., "specialization": ..., "submitted_at": ...}`. 4. If user_type is `patient`, upgrade to `hcp`. 5. Log to `audit_logs`. 6. Create notification for all Platform Admins. |
| **HCP** 🔒 | Check verification status | `GET /doctors/verification/status` | `users` | Return `verification` JSONB from user record. Includes: `status`, `submitted_at`, `reviewed_at`, `reviewed_by`, `rejection_reason`. |
| **Admin** 🛡️ | List pending verifications | `GET /doctors/admin/verifications` | `users` | `SELECT * FROM users WHERE verification->>'status' = 'pending'`. Paginated. Includes user profile details. Sort by `verification->>'submitted_at' ASC` (oldest first). |
| **Admin** 🛡️ | Approve/reject verification | `PATCH /doctors/admin/verifications/{verification_id}` | `users`, `audit_logs`, `notifications` | 1. If approved: set `verification.status = 'approved'`, `is_verified = TRUE`, `user_type = 'hcp'`, add `reviewed_at` and `reviewed_by`. 2. If rejected: set `verification.status = 'rejected'`, add `rejection_reason`. 3. Create notification for user. 4. Log to `audit_logs` with admin_id and decision. |
| **HCP (Verified)** 🔒 | Submit clinical observation | `POST /clinical-observations/` | `clinical_observations`, `audit_logs` | 1. `verified_hcp_required` middleware. 2. Validate `trial_id` exists. 3. Create observation record: `doctor_id`, `trial_id`, `severity` (low/medium/high/critical), `summary`, `data` (JSONB). 4. If `severity == 'critical'` → set `is_flagged = TRUE` + create admin notification. 5. Log to `audit_logs`. |
| **HCP (Verified)** 🔒 | Get trial observations | `GET /clinical-observations/trial/{trial_id}` | `clinical_observations`, `users` | 1. `verified_hcp_required` or `admin_required`. 2. Fetch observations joined with doctor display_name. 3. Paginated, sorted by `created_at DESC`. 4. Include `severity`, `is_flagged` status. |
| **HCP (Verified)** 🔒 | Access HCP-exclusive resources | `GET /hcp/resources` | `resources` | 1. `verified_hcp_required` middleware. 2. Return resources where `type IN ('toolkit', 'document', 'course')` AND tagged with `hcp_only = true` in metadata. 3. Paginated, filterable by category. |

**HCP Verification State Machine:**
```
[No Request] → POST /doctors/verification → [Pending]
[Pending] → Admin Approves → [Approved] → is_verified=TRUE, user_type='hcp'
[Pending] → Admin Rejects → [Rejected] → User can re-submit
[Approved] → Admin can revoke → [Revoked] → is_verified=FALSE
```

---

### 🏢 MODULE 3: Organization Management

**Goal:** Self-service membership management for org admins, working group lifecycle.

**Prerequisite:** `org_admin_required` middleware is already implemented. Extend with working group ownership validation.

| Actor | Action | Endpoint | Tables | Logic |
|:------|:-------|:---------|:-------|:------|
| **Org Admin** 🛡️ | View join requests | `GET /organizations/{org_id}/requests` | `organization_members`, `users` | 1. `org_admin_required` middleware (validates admin role for this org_id). 2. Fetch `organization_members` WHERE `org_id = {org_id}`. 3. Optional `?status=pending` filter. 4. Join with `users` for display_name, email. 5. Paginated. |
| **Org Admin** 🛡️ | Accept/reject member | `POST /organizations/{org_id}/members/{user_id}/decide` | `organization_members`, `organizations`, `notifications`, `audit_logs` | 1. `org_admin_required`. 2. Validate membership record exists with `status = 'pending'`. 3. Body: `{"decision": "approved" \| "rejected", "reason": "..."}`. 4. Update `organization_members.status`. 5. If approved: increment `organizations.member_count`. 6. Create notification for user. 7. Log to `audit_logs`. |
| **Org Admin** 🛡️ | Create working group | `POST /organizations/working-groups` | `working_groups`, `working_group_members`, `audit_logs` | 1. `org_admin_required` (validate org ownership). 2. Body: `{"name", "description", "type", "privacy_level", "organization_id"}`. 3. Validate `organization_id` matches admin's org. 4. Create working group record. 5. Auto-add creator as group admin in `working_group_members`. 6. Log to `audit_logs`. |
| **Org Admin** 🛡️ | Update working group | `PATCH /organizations/working-groups/{group_id}` | `working_groups`, `audit_logs` | 1. `org_admin_required` (validate group's `organization_id` matches admin's org). 2. Updatable: `name`, `description`, `type`, `privacy_level`, `is_active`. 3. Update `updated_at`. 4. Log to `audit_logs`. |
| **Org Member** 🔒 | Upload resource for org | `POST /resources` | `resources`, `notifications` | 1. `auth_required`. 2. Validate user is approved member of an org (`organization_members.status = 'approved'`). 3. Create resource with `status = 'pending'`, `organization_id` from user's org. 4. Notify Platform Admins for approval. |
| **Org Admin** 🛡️ | View WG join requests | `GET /organizations/working-groups/{group_id}/requests` | `working_group_members`, `users` | 1. `org_admin_required` (validate group's org). 2. Fetch members with optional status filter. 3. Join with users for profile info. |
| **Org Admin** 🛡️ | Accept/reject WG member | `POST /organizations/working-groups/{group_id}/members/{user_id}/decide` | `working_group_members`, `working_groups`, `notifications` | 1. `org_admin_required`. 2. Validate pending request exists. 3. Update status. 4. If approved: increment `working_groups.member_count`. 5. Notify user. |

---

### 🛡️ MODULE 4: Admin Panel

**Goal:** Complete platform governance — user management, content moderation, trial pipeline, resource approval.

**Prerequisite:** `admin_required` middleware. All actions logged to `audit_logs`.

| Actor | Action | Endpoint | Tables | Logic |
|:------|:-------|:---------|:-------|:------|
| **Admin** 🛡️ | Get user details | `GET /admin/users/{user_id}` | `users`, `user_profiles`, `audit_logs`, `content_reports` | 1. `admin_required`. 2. Fetch complete user record + profile. 3. Include: verification status, last login, account status, total posts, total reports filed, total reports against them, recent audit log entries. 4. Return comprehensive user audit object. |
| **Admin** 🛡️ | Verify HCP | `POST /admin/users/{user_id}/verify-hcp` | `users`, `notifications`, `audit_logs` | 1. `admin_required`. 2. Validate user has pending verification. 3. Body: `{"approved": true/false, "notes": "..."}`. 4. If approved: `is_verified = TRUE`, update `verification` JSONB. 5. If rejected: update `verification.status = 'rejected'`, store reason. 6. Notify user. 7. Audit log: `admin_id`, `user_id`, decision, notes. |
| **Admin** 🛡️ | Suspend user | `POST /admin/users/{user_id}/suspend` | `users`, `notifications`, `audit_logs` | 1. `admin_required`. 2. Cannot suspend other admins (self-protection). 3. Body: `{"duration_days": 7 \| null, "reason": "..."}`. 4. Set `users.status = 'suspended'`. 5. Calculate `suspended_until` if duration given (null = permanent). 6. Notify user with reason. 7. Invalidate all user tokens (add to blacklist). 8. Audit log. |
| **Admin** 🛡️ | Unsuspend user | `POST /admin/users/{user_id}/unsuspend` | `users`, `notifications`, `audit_logs` | 1. `admin_required`. 2. Validate `users.status = 'suspended'`. 3. Set `users.status = 'active'`. 4. Notify user. 5. Audit log. |
| **Admin** 🛡️ | Get moderation queue | `GET /admin/moderation/queue` | `content_reports`, `users` | 1. `admin_required`. 2. Fetch reports `WHERE status = 'pending'` (default) or filter by status param. 3. Include: `target_content` snapshot, `reporter_id` display_name, `reports_count` (aggregate of same target), `reason`, `created_at`. 4. Paginated. Sort by `reports_count DESC, created_at ASC` (most-reported + oldest first). |
| **Admin** 🛡️ | Resolve moderation report | `POST /admin/moderation/{report_id}/resolve` | `content_reports`, `forum_posts` or `comments`, `users`, `notifications`, `audit_logs` | 1. `admin_required`. 2. Body: `{"action": "approve" \| "remove_content" \| "warn_user" \| "ban_user", "notes": "...", "notify_user": true}`. 3. Update `content_reports.status = 'resolved'`, `action_taken`, `moderator_id`, `resolved_at`, `resolution_notes`. 4. If `remove_content`: set `target.is_deleted = TRUE` or `moderation_status = 'removed'`. 5. If `warn_user`: create warning notification. 6. If `ban_user`: set `users.status = 'suspended'` + notify. 7. Audit log with full decision chain. |
| **Admin** 🛡️ | Bulk import trials | `POST /admin/trials/import` | `clinical_trials`, `trial_sites`, `audit_logs` | 1. `admin_required`. 2. Accept CSV or JSON (multipart upload). 3. Parse and validate each row against `clinical_trials` schema. 4. For valid rows: `INSERT ... ON CONFLICT (nct_id) DO UPDATE`. 5. For invalid rows: collect errors. 6. Response: `{"imported": N, "updated": N, "failed": N, "errors": [...]}`. 7. Audit log with import summary. |
| **Admin** 🛡️ | Create trial manually | `POST /admin/trials` | `clinical_trials`, `audit_logs` | 1. `admin_required`. 2. Body: full trial object (title, disease_area, phase, status, sponsor, etc.). 3. Validate required fields. 4. Insert into `clinical_trials`. 5. Audit log. |
| **Admin** 🛡️ | Update trial | `PATCH /admin/trials/{trial_id}` | `clinical_trials`, `audit_logs` | 1. `admin_required`. 2. Partial update of trial fields. 3. Update `last_updated` timestamp. 4. Audit log with changed fields. |
| **Admin** 🛡️ | Approve resource | `PUT /resources/{resource_id}/status` | `resources`, `notifications`, `audit_logs` | 1. `admin_required`. 2. Body: `{"status": "published" \| "rejected", "notes": "..."}`. 3. Update `resources` status. 4. If published: resource becomes visible in public library. 5. Notify uploading org/user. 6. Audit log. |
| **Admin** 🛡️ | Feature content | `POST /admin/content/feature` | `resources`, `forum_posts`, `events` | 1. `admin_required`. 2. Body: `{"content_type": "resource" \| "post" \| "event", "content_id": "...", "featured": true, "featured_until": "2026-06-01"}`. 3. Set `featured = TRUE` on target. 4. Audit log. |
| **Admin** 🛡️ | List all users | `GET /admin/users` | `users`, `user_profiles` | 1. `admin_required`. 2. Filterable: `?role=hcp&status=active&q=search_term`. 3. Paginated. 4. Returns: id, display_name, email, user_type, status, is_verified, created_at, last_login. |

---

### 📊 MODULE 5: Analytics & System Intelligence

**Goal:** Data-driven platform governance and strategic insights.

| Actor | Action | Endpoint | Tables | Logic |
|:------|:-------|:---------|:-------|:------|
| **Admin** 🛡️ | Get platform analytics | `GET /admin/analytics` | Multiple tables (aggregation queries) | 1. `admin_required`. 2. Query params: `?period=day\|week\|month\|all` and `?metric=users\|trials\|engagement\|all`. 3. Return aggregated metrics object. |
| **Admin** 🛡️ | Get user growth metrics | `GET /admin/analytics/users` | `users` | `SELECT COUNT(*) total, COUNT(*) FILTER (WHERE created_at > NOW() - interval '30 days') new_30d, COUNT(*) FILTER (WHERE last_login > NOW() - interval '30 days') active_30d, COUNT(*) FILTER (WHERE user_type='hcp' AND is_verified=true) verified_hcps FROM users WHERE status='active'` |
| **Admin** 🛡️ | Get trial engagement | `GET /admin/analytics/trials` | `clinical_trials`, `trial_saves`, `user_activity_log` | Total trials, total saves, total interest expressions, top 10 searched diseases (from `user_activity_log` WHERE action='search_trial'), trials by phase distribution, trials by status distribution. |
| **Admin** 🛡️ | Get community metrics | `GET /admin/analytics/community` | `forum_posts`, `comments`, `content_reports` | Total posts (30d), total replies (30d), active communities (by post count), pending moderation reports, content removal rate. |
| **Admin** 🛡️ | Get top diseases | `GET /admin/analytics/top-diseases` | `clinical_trials`, `trial_saves`, `user_activity_log` | Aggregate most-searched, most-saved, and most-interested disease areas. Return top 20 with counts. |

**Analytics Response Schema:**
```json
{
  "period": "month",
  "generated_at": "2026-03-22T20:00:00Z",
  "users": {
    "total": 1250,
    "active_30d": 450,
    "new_30d": 78,
    "by_role": {"patient": 980, "hcp": 120, "org_member": 100, "admin": 5, "caregiver": 45},
    "verified_hcps": 85
  },
  "trials": {
    "total": 340,
    "saves_30d": 892,
    "interests_30d": 156,
    "top_diseases": [
      {"disease": "HIV", "searches": 2340, "saves": 456},
      {"disease": "Malaria", "searches": 1890, "saves": 312}
    ]
  },
  "community": {
    "total_posts_30d": 234,
    "total_replies_30d": 891,
    "reports_pending": 12,
    "active_communities": 8
  },
  "events": {
    "upcoming": 5,
    "registrations_30d": 234,
    "completed_30d": 3
  }
}
```

---

### 🔔 MODULE 6: Advanced Notifications (Upgrade)

**Goal:** Transform passive notification system into an active, event-driven alert engine.

| Actor | Action | Endpoint / Trigger | Tables | Logic |
|:------|:-------|:-------------------|:-------|:------|
| **System** | Trial alert matching | Background task (on trial insert/update) | `trial_alerts`, `clinical_trials`, `notifications` | 1. On new trial insert: scan active `trial_alerts`. 2. Match `disease_area`, `location`, `phase` criteria. 3. For `instant` frequency: create notification immediately. 4. For `daily`/`weekly`: queue for batch. 5. Create in-app notification record. |
| **System** | Daily digest email | Cron (06:00 UTC daily) | `trial_alerts`, `notifications`, `users` | 1. Fetch users with `alert_frequency = 'daily'`. 2. Compile matching trials since last notification. 3. Send single digest email per user. 4. Update `last_notified` timestamp. |
| **System** | Weekly roundup | Cron (Monday 08:00 UTC) | Multiple tables | 1. Compile: new trials, popular posts, upcoming events, completed surveys. 2. Personalize by user interests. 3. Send newsletter email. |
| **System** | Event reminder | Cron (hourly check) | `event_registrations`, `events`, `notifications` | 1. Find events starting within 24 hours. 2. For registered users not yet reminded: create notification `"Your event '{title}' starts in {hours} hours"`. 3. Set `reminder_sent = TRUE`. |
| **System** | Moderation escalation | Event handler | `content_reports`, `notifications` | 1. On report count exceeding threshold (≥ 3): create urgent admin notification. 2. Auto-flag content (`moderation_status = 'flagged'`). |
| **System** | HCP verification notification | Event handler | `notifications` | 1. On verification submission: notify all admins. 2. On verification decision: notify user with result. |
| **System** | Org membership notification | Event handler | `notifications` | 1. On join request: notify org admin. 2. On decision: notify requesting user. |
| **System** | Cleanup expired notifications | Cron (daily) | `notifications` | Delete notifications where `expires_at < NOW()` OR `created_at < NOW() - interval '90 days'`. |

---

## 4. Data Model Extensions

### 4.1 New Tables

#### `clinical_observations`
*Structured real-world evidence from verified HCPs about clinical trials.*

| Field | Type | Constraints | Notes |
|:------|:-----|:------------|:------|
| 🔑 `observation_id` | `UUID` | `PRIMARY KEY` | Observation identifier |
| 👤 `doctor_id` | `UUID` | `FK → users(id), NOT NULL` | Verified HCP who submitted |
| 🔬 `trial_id` | `UUID` | `FK → clinical_trials(trial_id), NOT NULL` | Associated trial |
| ⚠️ `severity` | `VARCHAR(50)` | `NOT NULL` | `low`, `medium`, `high`, `critical` |
| 📝 `summary` | `TEXT` | `NOT NULL` | Plain-language observation |
| 📦 `data` | `JSONB` | `DEFAULT '{}'` | Structured feedback fields |
| 🚩 `is_flagged` | `BOOLEAN` | `DEFAULT FALSE` | Auto-flagged if severity = critical |
| 📅 `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Submission timestamp |
| 🔄 `updated_at` | `TIMESTAMP` | `DEFAULT NOW()` | Last update |

**Indexes:** `idx_clinical_obs_doctor_id`, `idx_clinical_obs_trial_id`, `idx_clinical_obs_severity`, `idx_clinical_obs_is_flagged`

**Constraints:** `CHECK (severity IN ('low', 'medium', 'high', 'critical'))`

---

#### `audit_logs`
*Immutable record of all security-sensitive actions.*

| Field | Type | Constraints | Notes |
|:------|:-----|:------------|:------|
| 🔑 `log_id` | `UUID` | `PRIMARY KEY` | Log entry identifier |
| 👤 `user_id` | `UUID` | `FK → users(id), NULL` | Actor (NULL for system actions) |
| 🎬 `action` | `VARCHAR(100)` | `NOT NULL` | Action name (e.g., `user_suspended`, `hcp_verified`, `trial_imported`) |
| 🏷️ `target_type` | `VARCHAR(50)` | `NULL` | Entity type acted upon (`user`, `trial`, `report`, `resource`) |
| 🎯 `target_id` | `UUID` | `NULL` | ID of entity acted upon |
| 📦 `metadata` | `JSONB` | `DEFAULT '{}'` | Additional context (old values, new values, reason) |
| 🌐 `ip_address` | `VARCHAR(50)` | `NULL` | Actor's IP |
| 📅 `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Immutable timestamp |

**Indexes:** `idx_audit_logs_user_id`, `idx_audit_logs_action`, `idx_audit_logs_target`, `idx_audit_logs_created_at DESC`

**Important:** This table is **append-only**. No UPDATE or DELETE operations permitted.

---

#### `token_blacklist`
*Invalidated JWT tokens for logout and session revocation.*

| Field | Type | Constraints | Notes |
|:------|:-----|:------------|:------|
| 🔑 `id` | `UUID` | `PRIMARY KEY` | Record identifier |
| 🎫 `jti` | `VARCHAR(255)` | `UNIQUE, NOT NULL` | JWT ID claim |
| 👤 `user_id` | `UUID` | `FK → users(id), NOT NULL` | Token owner |
| ⏳ `expires_at` | `TIMESTAMP` | `NOT NULL` | Token's original expiry (for cleanup) |
| 📅 `blacklisted_at` | `TIMESTAMP` | `DEFAULT NOW()` | When token was invalidated |

**Indexes:** `idx_token_blacklist_jti` (for auth middleware lookup), `idx_token_blacklist_expires_at` (for cleanup cron)

---

#### `user_sessions` (Optional — Device Tracking)
*Active session tracking for multi-device management.*

| Field | Type | Constraints | Notes |
|:------|:-----|:------------|:------|
| 🔑 `session_id` | `UUID` | `PRIMARY KEY` | Session identifier |
| 👤 `user_id` | `UUID` | `FK → users(id), NOT NULL` | Session owner |
| 🎫 `jti` | `VARCHAR(255)` | `UNIQUE, NOT NULL` | Associated JWT ID |
| 🖥️ `device_info` | `VARCHAR(255)` | `NULL` | Parsed User-Agent string |
| 🌐 `ip_address` | `VARCHAR(50)` | `NULL` | Login IP |
| 📅 `created_at` | `TIMESTAMP` | `DEFAULT NOW()` | Session start |
| 🕒 `last_active` | `TIMESTAMP` | `DEFAULT NOW()` | Last API call time |

**Indexes:** `idx_user_sessions_user_id`, `idx_user_sessions_jti`

---

### 4.2 Table Modifications

#### `users` — Add Columns
| Column | Type | Default | Purpose |
|:-------|:-----|:--------|:--------|
| `suspended_until` | `TIMESTAMP` | `NULL` | Auto-unsuspend date (NULL = permanent) |
| `suspended_reason` | `TEXT` | `NULL` | Admin-provided suspension reason |

#### `organization_members` — Already has required fields
- `status` column (`pending`, `approved`, `rejected`) ✅
- `role` column (`admin`, `moderator`, `member`) ✅

#### `resources` — Add Column
| Column | Type | Default | Purpose |
|:-------|:-----|:--------|:--------|
| `status` | `VARCHAR(50)` | `'published'` | `pending`, `published`, `rejected` — for org-uploaded resources |
| `uploaded_by` | `UUID` | `NULL` | FK → users(id) — who uploaded it |

#### `events` — Add Column
| Column | Type | Default | Purpose |
|:-------|:-----|:--------|:--------|
| `reminder_sent` | `BOOLEAN` | `FALSE` | Track if reminder notification was sent |

### 4.3 Relationships Diagram

```
users (1) ←→ (N) clinical_observations (as doctor)
users (1) ←→ (N) audit_logs (as actor)
users (1) ←→ (N) token_blacklist
users (1) ←→ (N) user_sessions

clinical_trials (1) ←→ (N) clinical_observations

audit_logs → references users, clinical_trials, resources, content_reports (polymorphic via target_type + target_id)
```

---

## 5. Security Extensions

### 5.1 RBAC Enforcement

- **Every endpoint** must declare its required access level via middleware
- Middleware is **composable**: `auth_required` → `verified_hcp_required` → endpoint handler
- All role checks happen at the middleware layer, **never in the business logic**
- Suspended users are blocked at the `auth_required` middleware level (not per-endpoint)

### 5.2 Stricter Validation

| Rule | Implementation |
|:-----|:---------------|
| Admin cannot suspend other admins | Check in `POST /admin/users/{id}/suspend` |
| Admin cannot self-delete | Check in `DELETE /users/me` |
| HCP verification requires pending status | Check before PATCH decision |
| Org admin can only manage their org | Validated by `org_admin_required` middleware |
| Rate limiting on auth endpoints | 5 req/min for login, register, reset |
| Rate limiting on admin endpoints | 60 req/min per admin |
| Input size limits | 10KB max for post content, 50MB max for file uploads |

### 5.3 Admin Action Logging

Every admin action inserts into `audit_logs`:

```sql
INSERT INTO audit_logs (log_id, user_id, action, target_type, target_id, metadata, ip_address, created_at)
VALUES ($1, $2, $3, $4, $5, $6, $7, NOW())
```

**Logged Actions:**
- `hcp_verified`, `hcp_rejected`
- `user_suspended`, `user_unsuspended`
- `report_resolved`
- `trial_imported`, `trial_created`, `trial_updated`
- `resource_approved`, `resource_rejected`
- `content_featured`
- `working_group_created`, `working_group_updated`
- `member_approved`, `member_rejected`

### 5.4 Abuse Prevention

| Threat | Mitigation |
|:-------|:-----------|
| Token theft | JWT blacklist on logout, short expiry (24h), jti uniqueness |
| Brute force login | Rate limiting (5 attempts/min), account lockout after 10 failures |
| Spam posts | Auto-flag at 3+ reports, new accounts limited to 5 posts/day |
| HCP impersonation | Verification requires admin approval, periodic re-verification (future) |
| Privilege escalation | Middleware-level enforcement, role checks on every request |
| Data enumeration | Generic error messages (e.g., reset password), no user existence leak |

---

## 6. System Flow Diagrams

### 6.1 HCP Verification Flow

```
┌──────────┐     POST /doctors/verification     ┌──────────┐
│          │ ──────────────────────────────────→ │          │
│   HCP    │   Upload license, credentials      │  System  │
│  (User)  │                                    │          │
│          │ ←────────────────────────────────── │          │
└──────────┘   Status: "pending"                └────┬─────┘
                                                     │
                                              Notification to Admin
                                                     │
                                                     ▼
                                               ┌──────────┐
                                               │  Admin   │
                                               │  Panel   │
                                               └────┬─────┘
                                                     │
                                    GET /doctors/admin/verifications
                                                     │
                                          ┌──────────┴──────────┐
                                          │                     │
                                    ✅ APPROVE              ❌ REJECT
                                          │                     │
                                    is_verified=TRUE      verification.status=
                                    user_type='hcp'       'rejected' + reason
                                          │                     │
                                    Notification:          Notification:
                                    "You're verified!"     "Rejected. Reason: ..."
                                          │                     │
                                    HCP Features           Can Re-Submit
                                    UNLOCKED               After Correction
```

### 6.2 Organization Join Flow

```
┌──────────┐    POST /organizations/{id}/join     ┌──────────┐
│   User   │ ───────────────────────────────────→ │  System  │
│          │                                      │          │
│          │ ←─────────────────────────────────── │          │
└──────────┘   Status: "pending_approval"         └────┬─────┘
                                                       │
                                                Notification to
                                                Org Admin
                                                       │
                                                       ▼
                                                 ┌──────────┐
                                                 │   Org    │
                                                 │  Admin   │
                                                 └────┬─────┘
                                                       │
                         POST /organizations/{org_id}/members/{user_id}/decide
                                                       │
                                            ┌──────────┴──────────┐
                                            │                     │
                                      ✅ APPROVE              ❌ REJECT
                                            │                     │
                                      status='approved'     status='rejected'
                                      member_count++        + reason
                                            │                     │
                                      Notification:          Notification:
                                      "Welcome to XYZ!"     "Request denied"
                                            │
                                      User can now:
                                      - Upload resources
                                      - Join working groups
                                      - Contribute to org
```

### 6.3 Content Moderation Flow

```
┌──────────┐   POST /community/{id}/report     ┌──────────┐
│  User A  │ ─────────────────────────────────→ │  System  │
│(Reporter)│   Reason: "misinformation"         │          │
└──────────┘                                    └────┬─────┘
                                                     │
                                          Report created in
                                          content_reports
                                                     │
                                        ┌────────────┴────────────┐
                                        │                         │
                                   reports < 3              reports ≥ 3
                                        │                         │
                                   Queue for                Auto-flag content
                                   admin review             moderation_status =
                                        │                   'flagged'
                                        │                         │
                                        └────────────┬────────────┘
                                                     │
                                        GET /admin/moderation/queue
                                                     │
                                                     ▼
                                               ┌──────────┐
                                               │  Admin   │
                                               └────┬─────┘
                                                     │
                               POST /admin/moderation/{id}/resolve
                                                     │
                                    ┌─────────┬──────┴──────┬──────────┐
                                    │         │             │          │
                               ✅ Approve  🗑️ Remove    ⚠️ Warn    🚫 Ban
                               (false alarm) Content     User       User
                                    │         │             │          │
                               status=     is_deleted=   Notification users.status=
                               'resolved'  TRUE          to user     'suspended'
```

### 6.4 Resource Upload & Approval Flow

```
┌──────────┐      POST /resources              ┌──────────┐
│   Org    │ ────────────────────────────────→  │  System  │
│  Member  │   File + metadata                 │          │
└──────────┘                                   └────┬─────┘
                                                    │
                                          resources.status = 'pending'
                                          Notify Platform Admins
                                                    │
                                                    ▼
                                              ┌──────────┐
                                              │  Admin   │
                                              └────┬─────┘
                                                    │
                                    PUT /resources/{id}/status
                                                    │
                                         ┌──────────┴──────────┐
                                         │                     │
                                   ✅ PUBLISH              ❌ REJECT
                                         │                     │
                                   status='published'    status='rejected'
                                   Visible in library    Notify org member
                                   Notify uploader       with reason
```

---

## 7. What Is Complete After Phase 2

### Platform Completeness Checklist

| Capability | MVP | Phase 2 | Status After Phase 2 |
|:-----------|:---:|:-------:|:--------------------:|
| User authentication (register, login, reset) | ✅ | — | ✅ Complete |
| User profiles & preferences | ✅ | — | ✅ Complete |
| Clinical trial search & bookmarks | ✅ | — | ✅ Complete |
| Trial alerts & notifications | ✅ | Upgraded with background jobs | ✅ Complete |
| Community forums & moderation | ✅ | Admin moderation pipeline | ✅ Complete |
| Events & webinars | ✅ | Reminders, analytics | ✅ Complete |
| Resources & education | ✅ | Approval flow, org uploads | ✅ Complete |
| Surveys & research data | ✅ | — | ✅ Complete |
| Organizations & working groups | ✅ | Membership approval, WG management | ✅ Complete |
| **RBAC enforcement** | ❌ Partial | ✅ Full middleware stack | ✅ Complete |
| **HCP verification pipeline** | ❌ Partial | ✅ Full lifecycle | ✅ Complete |
| **Clinical observations** | ❌ | ✅ Full CRUD | ✅ Complete |
| **Admin panel governance** | ❌ | ✅ Full tooling | ✅ Complete |
| **Audit logging** | ❌ | ✅ Comprehensive | ✅ Complete |
| **Token management (logout)** | ❌ | ✅ Blacklist + sessions | ✅ Complete |
| **Content approval workflows** | ❌ | ✅ Resources + moderation | ✅ Complete |
| **Platform analytics** | ❌ | ✅ Multi-dimensional | ✅ Complete |
| **Background job engine** | ❌ | ✅ Alerts, reminders, cleanup | ✅ Complete |

### What This Means

After Phase 2:

1. **Every user action is role-gated** — No unauthorized access possible
2. **Every admin action is audited** — Full accountability trail
3. **HCPs have a complete lifecycle** — From application to clinical tools
4. **Organizations are self-managed** — Admins handle their own membership
5. **Content is governed** — Upload → Review → Publish pipeline
6. **Platform health is measurable** — Analytics for strategic decisions
7. **Notifications are proactive** — System alerts users about relevant changes
8. **The platform is production-ready** — Ready for real users, real data, real regulatory scrutiny

### What Remains for Phase 3 (Future)

- 🔄 Real-time messaging / chat
- 🤖 Advanced AI-powered trial matching (LLM integration)
- 🌍 Multi-language support (i18n)
- 📱 Mobile native apps
- 💳 Premium features / payment processing
- 🏥 EHR/FHIR integration
- 📊 Advanced data science & cohort analytics
- 🔐 Electronic consent management

---

## 8. Implementation Priority Order

> **Recommended sequence for maximum value delivery:**

| Priority | Module | Effort Estimate | Dependencies |
|:---------|:-------|:---------------|:-------------|
| **P0** | RBAC Middleware Stack | 2–3 days | None — foundational |
| **P0** | Audit Logs Infrastructure | 1–2 days | RBAC middleware |
| **P1** | Admin Panel (user management, moderation) | 3–4 days | RBAC + Audit logs |
| **P1** | HCP Verification Pipeline | 2–3 days | RBAC + Admin panel |
| **P1** | Token Blacklist + Logout | 1–2 days | RBAC middleware |
| **P2** | Organization Self-Management | 2–3 days | RBAC + Audit logs |
| **P2** | Clinical Observations | 2 days | HCP pipeline |
| **P2** | Resource Approval Workflow | 1–2 days | Admin panel |
| **P3** | Analytics Engine | 2–3 days | Data model in place |
| **P3** | Advanced Notification Engine | 3–4 days | All modules in place |

**Total estimated effort: 20–28 engineering days**

---

> **Document Version:** 1.0
> **Last Updated:** 2026-03-22
> **Author:** Backend Architecture Team
> **Status:** Ready for Implementation
