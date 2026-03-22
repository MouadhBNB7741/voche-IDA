# 🏗️ PHASE 2 ACTIONS — RBAC & Advanced Systems

**Scope:** Phase 2 Extensions Only (MVP actions are in `actions.md`)
**Golden Rule:** *Every action enforces RBAC, logs audit trails for admin operations, and triggers notifications where applicable.*

> **Legend**
> * **Auth:** `🔒` Requires Login | `🌍` Public | `🛡️` Admin Only | `🩺` Verified HCP Only | `🏢` Org Admin Only
> * **Middleware:** `auth_required` · `admin_required` · `verified_hcp_required` · `org_admin_required`

**Alignment:**
- [MVP Actions](./actions.md) — Base format reference
- [Phase 2 Spec](./phase2.md) — Full architecture spec
- [DB Structure](./dbStrucutre.md) — Table schemas
- [Endpoints](./endPoint.md) — Existing routes
- [Progress](../../backend/.agent/progress.md) — Current state

---

## 🔐 1. ADVANCED AUTH & SECURITY (EXTENSION)

*Extends MVP auth with session control, token lifecycle, suspended-user enforcement, and immutable audit logging.*

| Actor | Action | Handler (Route) | Database Tables | System Logic & Data Flow |
|:------|:-------|:----------------|:----------------|:-------------------------|
| **User** `🔒` | Logout (Invalidate Token) | `POST /auth/logout` | `token_blacklist` | 1. `auth_required` middleware.\n2. Extract `jti` (JWT ID) claim from token.\n3. `INSERT INTO token_blacklist (id, jti, user_id, expires_at, blacklisted_at)` with token's original expiry.\n4. Return `200 {"message": "Logged out"}`. |
| **User** `🔒` | List Active Sessions | `GET /auth/sessions` | `user_sessions` | 1. `auth_required`.\n2. `SELECT * FROM user_sessions WHERE user_id = $1 ORDER BY last_active DESC`.\n3. Return array of `{session_id, device_info, ip_address, created_at, last_active}`. |
| **User** `🔒` | Revoke Session | `DELETE /auth/sessions/{session_id}` | `user_sessions`, `token_blacklist` | 1. `auth_required`.\n2. Verify `user_sessions.user_id = current_user` (ownership check).\n3. Fetch `jti` from session record.\n4. Insert `jti` into `token_blacklist`.\n5. `DELETE FROM user_sessions WHERE session_id = $1`.\n6. Return `200`. |
| **System** | Enforce Suspended Users | All authenticated endpoints | `users` | 1. **Upgrade to `auth_required` middleware:** after JWT validation, `SELECT status, suspended_until, suspended_reason FROM users WHERE id = $1`.\n2. If `status = 'suspended'`: check `suspended_until`. If `suspended_until IS NOT NULL AND suspended_until < NOW()` → auto-unsuspend (`UPDATE users SET status='active'`). Else → return `403 {"detail": "Account suspended", "reason": "...", "until": "..."}`. |
| **System** | Check Token Blacklist | All authenticated endpoints | `token_blacklist` | 1. **Upgrade to `auth_required` middleware:** after JWT decode, extract `jti`.\n2. `SELECT 1 FROM token_blacklist WHERE jti = $1`.\n3. If found → `401 {"detail": "Token revoked"}`.\n4. If not found → proceed. |
| **System** | Write Audit Log | Internal (called by middleware/services) | `audit_logs` | 1. Called by admin middleware and critical endpoints.\n2. `INSERT INTO audit_logs (log_id, user_id, action, target_type, target_id, metadata, ip_address, created_at)` VALUES `(uuid4(), $actor_id, $action_name, $entity_type, $entity_id, $jsonb_context, $request_ip, NOW())`.\n3. **Append-only table** — no UPDATE/DELETE permitted.\n4. Actions logged: `login`, `password_change`, `hcp_verified`, `hcp_rejected`, `user_suspended`, `user_unsuspended`, `report_resolved`, `trial_imported`, `trial_created`, `trial_updated`, `resource_approved`, `resource_rejected`, `content_featured`, `member_approved`, `member_rejected`. |
| **System** | Cleanup Expired Tokens | Cron (daily 03:00 UTC) | `password_reset_tokens`, `token_blacklist` | 1. `DELETE FROM password_reset_tokens WHERE expires_at < NOW() AND used = TRUE`.\n2. `DELETE FROM token_blacklist WHERE expires_at < NOW()`.\n3. Log cleanup count to application logger. |
| **System** | Track Session Activity | Login + every auth request | `user_sessions` | 1. **On login (`POST /auth/login`):** Insert `user_sessions` record with `jti`, parsed `User-Agent`, IP.\n2. **On each authenticated request:** `UPDATE user_sessions SET last_active = NOW() WHERE jti = $1` (async, non-blocking). |

---

## 🩺 2. HCP SYSTEM (NEW MODULE)

*Complete healthcare professional lifecycle: credential submission → admin review → clinical tool access.*

| Actor | Action | Handler (Route) | Database Tables | System Logic & Data Flow |
|:------|:-------|:----------------|:----------------|:-------------------------|
| **HCP** `🔒` | Submit Verification Request | `POST /doctors/verification` | `users`, `audit_logs`, `notifications` | 1. `auth_required`.\n2. Require `user_type IN ('hcp', 'patient')` — reject org_member/admin.\n3. Check `users.verification->>'status' != 'pending'` — reject if already pending.\n4. Body: `{license_number, institution, country, specialization, supporting_docs}`.\n5. Update `users.verification` JSONB: `{"status":"pending", "license_number":"...", "institution":"...", "country":"...", "specialization":"...", "submitted_at":"NOW()"}`. \n6. If `user_type = 'patient'` → `UPDATE users SET user_type = 'hcp'`.\n7. `INSERT INTO audit_logs` action=`hcp_verification_submitted`.\n8. Create notification for ALL users WHERE `user_type='admin'`: "New HCP verification pending". |
| **HCP** `🔒` | Check Verification Status | `GET /doctors/verification/status` | `users` | 1. `auth_required`.\n2. `SELECT verification FROM users WHERE id = $1`.\n3. Return JSONB: `{status, license_number, institution, submitted_at, reviewed_at, reviewed_by, rejection_reason}`. If no verification → `{"status": "none"}`. |
| **Admin** `🛡️` | List Pending Verifications | `GET /doctors/admin/verifications` | `users`, `user_profiles` | 1. `admin_required` middleware.\n2. `SELECT u.id, u.display_name, u.email, u.verification, u.created_at FROM users u WHERE u.verification->>'status' = 'pending' ORDER BY u.verification->>'submitted_at' ASC`.\n3. Paginated (`page`, `limit`). Join with `user_profiles` for specialization context. |
| **Admin** `🛡️` | Approve/Reject Verification | `PATCH /doctors/admin/verifications/{user_id}` | `users`, `notifications`, `audit_logs` | 1. `admin_required`.\n2. Validate target user has `verification->>'status' = 'pending'`.\n3. Body: `{status: "approved"|"rejected", notes: "..."}`.\n4. **If approved:** Update verification JSONB `{status:'approved', reviewed_at:NOW(), reviewed_by:admin_id}`. Set `users.is_verified = TRUE`, `users.user_type = 'hcp'`.\n5. **If rejected:** Update verification JSONB `{status:'rejected', reviewed_at:NOW(), reviewed_by:admin_id, rejection_reason:notes}`.\n6. Create notification for target user with decision.\n7. `INSERT INTO audit_logs` action=`hcp_verified` or `hcp_rejected`, target_type=`user`, target_id=user_id, metadata=`{notes, admin_id}`. |
| **HCP (Verified)** `🩺` | Submit Clinical Observation | `POST /clinical-observations/` | `clinical_observations`, `audit_logs`, `notifications` | 1. `verified_hcp_required` middleware (checks `auth_required` + `user_type='hcp'` + `is_verified=TRUE`).\n2. Body: `{trial_id, severity, summary, data}`.\n3. Validate `trial_id` exists in `clinical_trials`.\n4. Validate `severity IN ('low','medium','high','critical')`.\n5. `INSERT INTO clinical_observations (observation_id, doctor_id, trial_id, severity, summary, data, is_flagged, created_at)`.\n6. **If severity = 'critical':** set `is_flagged = TRUE` + create admin notification "Critical observation on trial {title}".\n7. `INSERT INTO audit_logs` action=`clinical_observation_submitted`. |
| **HCP (Verified)** `🩺` | View Trial Observations | `GET /clinical-observations/trial/{trial_id}` | `clinical_observations`, `users` | 1. `verified_hcp_required` OR `admin_required`.\n2. Validate `trial_id` exists.\n3. `SELECT co.*, u.display_name AS doctor_name FROM clinical_observations co JOIN users u ON co.doctor_id = u.id WHERE co.trial_id = $1 ORDER BY co.created_at DESC`.\n4. Paginated. Include `severity`, `is_flagged`, `summary`. |
| **HCP (Verified)** `🩺` | Access HCP Resources | `GET /hcp/resources` | `resources` | 1. `verified_hcp_required` middleware.\n2. `SELECT * FROM resources WHERE (metadata->>'hcp_only')::boolean = TRUE AND status = 'published'`.\n3. Optional filters: `?type=toolkit&category=clinical_protocols`.\n4. Paginated, sorted by `published_date DESC`. |

---

## 🏢 3. ORGANIZATION MANAGEMENT (EXTENSION)

*Extends MVP org module with self-service membership management and working group lifecycle.*

| Actor | Action | Handler (Route) | Database Tables | System Logic & Data Flow |
|:------|:-------|:----------------|:----------------|:-------------------------|
| **Org Admin** `🏢` | View Join Requests | `GET /organizations/{org_id}/requests` | `organization_members`, `users` | 1. `org_admin_required(org_id)` middleware — validates: `user_type='admin'` OR `organization_members.role='admin' AND .status='approved'` for this org_id.\n2. Optional filter: `?status=pending` (default: all).\n3. `SELECT om.*, u.display_name, u.email FROM organization_members om JOIN users u ON om.user_id = u.id WHERE om.org_id = $1` + status filter.\n4. Paginated, sorted by `joined_at ASC`. |
| **Org Admin** `🏢` | Accept/Reject Member | `POST /organizations/{org_id}/members/{user_id}/decide` | `organization_members`, `organizations`, `notifications`, `audit_logs` | 1. `org_admin_required(org_id)`.\n2. Validate record exists: `SELECT * FROM organization_members WHERE org_id=$1 AND user_id=$2 AND status='pending'` — 404 if not found.\n3. Body: `{decision: "approved"|"rejected", reason: "..."}`.\n4. `UPDATE organization_members SET status=$decision, updated_at=NOW() WHERE org_id=$1 AND user_id=$2`.\n5. **If approved:** `UPDATE organizations SET member_count = member_count + 1 WHERE org_id=$1`.\n6. Create notification for user: "Your request to join {org_name} was {decision}".\n7. `INSERT INTO audit_logs` action=`member_approved` or `member_rejected`, target_type=`organization`, target_id=org_id, metadata=`{user_id, decision, reason, decided_by}`. |
| **Org Admin** `🏢` | Create Working Group | `POST /organizations/working-groups` | `working_groups`, `working_group_members`, `audit_logs` | 1. `org_admin_required(body.organization_id)` — validate admin owns the org specified.\n2. Body: `{name, description, type, privacy_level, organization_id}`.\n3. Validate `type IN ('research','advocacy','patient_support')`, `privacy_level IN ('public','private','invitation_only')`.\n4. `INSERT INTO working_groups` → get `group_id`.\n5. Auto-add creator: `INSERT INTO working_group_members (group_id, user_id, role='admin', status='approved')`.\n6. `INSERT INTO audit_logs` action=`working_group_created`. |
| **Org Admin** `🏢` | Update Working Group | `PATCH /organizations/working-groups/{group_id}` | `working_groups`, `audit_logs` | 1. Fetch group's `organization_id`. `org_admin_required(organization_id)` — validate admin owns the parent org.\n2. Updatable fields: `name`, `description`, `type`, `privacy_level`, `is_active`.\n3. `UPDATE working_groups SET ... WHERE group_id=$1`. Update `updated_at`.\n4. `INSERT INTO audit_logs` action=`working_group_updated`, metadata=`{changed_fields}`. |
| **Org Admin** `🏢` | View WG Join Requests | `GET /organizations/working-groups/{group_id}/requests` | `working_group_members`, `users` | 1. Fetch group's `organization_id`. `org_admin_required(organization_id)`.\n2. `SELECT wgm.*, u.display_name, u.email FROM working_group_members wgm JOIN users u ON wgm.user_id=u.id WHERE wgm.group_id=$1` + optional `?status=pending`.\n3. Paginated. |
| **Org Admin** `🏢` | Accept/Reject WG Member | `POST /organizations/working-groups/{group_id}/members/{user_id}/decide` | `working_group_members`, `working_groups`, `notifications` | 1. Fetch group's `organization_id`. `org_admin_required(organization_id)`.\n2. Validate pending request: `SELECT * FROM working_group_members WHERE group_id=$1 AND user_id=$2 AND status='pending'` — 404 if not found.\n3. Body: `{decision: "approved"|"rejected"}`.\n4. `UPDATE working_group_members SET status=$decision`.\n5. **If approved:** `UPDATE working_groups SET member_count = member_count + 1 WHERE group_id=$1`.\n6. Notify user. |
| **Org Member** `🔒` | Upload Resource (Pending) | `POST /resources` | `resources`, `notifications` | 1. `auth_required`.\n2. Validate user is approved org member: `SELECT org_id FROM organization_members WHERE user_id=$1 AND status='approved'` — 403 if not found.\n3. Body: `{title, type, category, description, url, language, tags}`.\n4. `INSERT INTO resources (..., status='pending', organization_id=$org_id, uploaded_by=$user_id)`.\n5. Create notification for ALL `admin` users: "New resource pending approval from {org_name}". |

---

## 🛡️ 4. ADMIN PANEL (NEW CORE MODULE)

*Complete platform governance: user management, moderation, trial pipeline, resource approval.*

| Actor | Action | Handler (Route) | Database Tables | System Logic & Data Flow |
|:------|:-------|:----------------|:----------------|:-------------------------|
| **Admin** `🛡️` | List All Users | `GET /admin/users` | `users`, `user_profiles` | 1. `admin_required` middleware.\n2. Filters: `?role=hcp&status=active&q=search_term&page=1&limit=20`.\n3. Build query with WHERE clauses. Text search on `display_name`, `email`.\n4. Return: `{data: [{id, display_name, email, user_type, status, is_verified, created_at, last_login}], meta: {total, page, limit}}`. |
| **Admin** `🛡️` | Get User Details | `GET /admin/users/{user_id}` | `users`, `user_profiles`, `audit_logs`, `content_reports` | 1. `admin_required`.\n2. Fetch user + profile (JOIN).\n3. Count: posts authored, reports filed, reports against user.\n4. Fetch last 20 `audit_logs` WHERE `user_id=$1` OR `target_id=$1`.\n5. Return comprehensive audit object with verification status, activity summary, moderation history. |
| **Admin** `🛡️` | Suspend User | `POST /admin/users/{user_id}/suspend` | `users`, `token_blacklist`, `notifications`, `audit_logs` | 1. `admin_required`.\n2. **Guard:** target `user_type != 'admin'` — cannot suspend admins.\n3. Body: `{duration_days: 7|null, reason: "..."}`.\n4. `UPDATE users SET status='suspended', suspended_reason=$reason, suspended_until=(NOW() + interval '$days days')` (NULL duration = permanent).\n5. Blacklist ALL user tokens: `INSERT INTO token_blacklist SELECT ... FROM user_sessions WHERE user_id=$1`.\n6. `DELETE FROM user_sessions WHERE user_id=$1`.\n7. Create notification (persisted for when unsuspended): "Account suspended: {reason}".\n8. `INSERT INTO audit_logs` action=`user_suspended`, metadata=`{reason, duration, admin_id}`. |
| **Admin** `🛡️` | Unsuspend User | `POST /admin/users/{user_id}/unsuspend` | `users`, `notifications`, `audit_logs` | 1. `admin_required`.\n2. Validate `users.status = 'suspended'` — 400 if not suspended.\n3. `UPDATE users SET status='active', suspended_reason=NULL, suspended_until=NULL`.\n4. Notify user: "Account reinstated".\n5. `INSERT INTO audit_logs` action=`user_unsuspended`. |
| **Admin** `🛡️` | Get Moderation Queue | `GET /admin/moderation/queue` | `content_reports`, `users` | 1. `admin_required`.\n2. Optional: `?status=pending&type=post&page=1&limit=20`.\n3. `SELECT cr.*, u.display_name AS reporter_name, (SELECT COUNT(*) FROM content_reports cr2 WHERE cr2.target_type=cr.target_type AND cr2.target_id=cr.target_id) AS total_reports FROM content_reports cr JOIN users u ON cr.reporter_id=u.id` + filters.\n4. Sort: `total_reports DESC, created_at ASC` (most reported + oldest first). |
| **Admin** `🛡️` | Resolve Moderation Report | `POST /admin/moderation/{report_id}/resolve` | `content_reports`, `forum_posts`, `comments`, `users`, `notifications`, `audit_logs` | 1. `admin_required`.\n2. Body: `{action: "approve"|"remove_content"|"warn_user"|"ban_user", notes: "...", notify_user: true}`.\n3. `UPDATE content_reports SET status='resolved', action_taken=$action, moderator_id=$admin_id, resolution_notes=$notes, resolved_at=NOW()`.\n4. **If remove_content:** fetch target → if post: `UPDATE forum_posts SET is_deleted=TRUE, moderation_status='removed'`. If comment: `UPDATE comments SET is_deleted=TRUE, moderation_status='removed'`.\n5. **If warn_user:** create notification for content author: "Content warning: {notes}".\n6. **If ban_user:** execute suspend logic (same as suspend endpoint).\n7. `INSERT INTO audit_logs` action=`report_resolved`, metadata=`{report_id, action, target_type, target_id, notes}`. |
| **Admin** `🛡️` | Bulk Import Trials | `POST /admin/trials/import` | `clinical_trials`, `trial_sites`, `audit_logs` | 1. `admin_required`.\n2. Accept multipart: CSV or JSON file.\n3. Parse rows. For each row: validate required fields (title, disease_area, phase, status, sponsor).\n4. For valid rows: `INSERT INTO clinical_trials (...) ON CONFLICT (nct_id) DO UPDATE SET title=$2, ...`.\n5. Collect errors for invalid rows.\n6. Response: `{imported: N, updated: N, failed: N, errors: [{row: 5, field: "phase", message: "Invalid value"}]}`.\n7. `INSERT INTO audit_logs` action=`trial_imported`, metadata=`{imported, updated, failed, filename}`. |
| **Admin** `🛡️` | Create Trial | `POST /admin/trials` | `clinical_trials`, `audit_logs` | 1. `admin_required`.\n2. Body: full trial object `{title, disease_area, phase, status, sponsor, countries, eligibility_criteria, ...}`.\n3. Validate: required fields, `phase IN (...)`, `status IN (...)`.\n4. `INSERT INTO clinical_trials`.\n5. `INSERT INTO audit_logs` action=`trial_created`. |
| **Admin** `🛡️` | Update Trial | `PATCH /admin/trials/{trial_id}` | `clinical_trials`, `audit_logs` | 1. `admin_required`.\n2. Validate `trial_id` exists.\n3. Partial update of provided fields.\n4. `UPDATE clinical_trials SET ..., last_updated=NOW() WHERE trial_id=$1`.\n5. `INSERT INTO audit_logs` action=`trial_updated`, metadata=`{changed_fields, old_values, new_values}`. |
| **Admin** `🛡️` | Approve/Reject Resource | `PUT /resources/{resource_id}/status` | `resources`, `notifications`, `audit_logs` | 1. `admin_required`.\n2. Body: `{status: "published"|"rejected", notes: "..."}`.\n3. Validate resource exists and `status = 'pending'`.\n4. `UPDATE resources SET status=$status, updated_at=NOW()`.\n5. Fetch `uploaded_by` → create notification: "Your resource '{title}' was {status}".\n6. `INSERT INTO audit_logs` action=`resource_approved` or `resource_rejected`, metadata=`{resource_id, notes}`. |
| **Admin** `🛡️` | Feature Content | `POST /admin/content/feature` | `resources`, `forum_posts`, `events` | 1. `admin_required`.\n2. Body: `{content_type: "resource"|"post"|"event", content_id: "uuid", featured: true, featured_until: "2026-06-01"}`.\n3. Based on `content_type`: `UPDATE {table} SET featured=$featured WHERE {pk}=$content_id`.\n4. `INSERT INTO audit_logs` action=`content_featured`, metadata=`{content_type, content_id, featured_until}`. |

---

## 📊 5. ANALYTICS (NEW MODULE)

*Aggregation endpoints for platform intelligence and strategic decisions.*

| Actor | Action | Handler (Route) | Database Tables | System Logic & Data Flow |
|:------|:-------|:----------------|:----------------|:-------------------------|
| **Admin** `🛡️` | Get Platform Overview | `GET /admin/analytics` | Multiple tables | 1. `admin_required`.\n2. Params: `?period=day|week|month|all`.\n3. Calculate date boundary from period.\n4. Execute parallel aggregation queries (see sub-endpoints below).\n5. Return unified analytics object: `{period, generated_at, users:{...}, trials:{...}, community:{...}, events:{...}}`. |
| **Admin** `🛡️` | User Growth Metrics | `GET /admin/analytics/users` | `users` | 1. `admin_required`.\n2. `SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE created_at > $boundary) AS new, COUNT(*) FILTER (WHERE last_login > $boundary) AS active, COUNT(*) FILTER (WHERE user_type='hcp' AND is_verified=true) AS verified_hcps FROM users WHERE status='active'`.\n3. Role breakdown: `SELECT user_type, COUNT(*) FROM users WHERE status='active' GROUP BY user_type`. |
| **Admin** `🛡️` | Trial Engagement | `GET /admin/analytics/trials` | `clinical_trials`, `trial_saves`, `user_activity_log` | 1. `admin_required`.\n2. Total trials: `SELECT COUNT(*) FROM clinical_trials`.\n3. Saves in period: `SELECT COUNT(*) FROM trial_saves WHERE saved_at > $boundary`.\n4. By phase: `SELECT phase, COUNT(*) FROM clinical_trials GROUP BY phase`.\n5. By status: `SELECT status, COUNT(*) FROM clinical_trials GROUP BY status`. |
| **Admin** `🛡️` | Top Diseases | `GET /admin/analytics/top-diseases` | `clinical_trials`, `trial_saves` | 1. `admin_required`.\n2. `SELECT ct.disease_area, COUNT(DISTINCT ct.trial_id) AS trials, COUNT(ts.id) AS saves FROM clinical_trials ct LEFT JOIN trial_saves ts ON ct.trial_id = ts.trial_id GROUP BY ct.disease_area ORDER BY saves DESC LIMIT 20`. |
| **Admin** `🛡️` | Community Metrics | `GET /admin/analytics/community` | `forum_posts`, `comments`, `content_reports` | 1. `admin_required`.\n2. Posts in period: `SELECT COUNT(*) FROM forum_posts WHERE created_at > $boundary AND is_deleted=FALSE`.\n3. Replies in period: `SELECT COUNT(*) FROM comments WHERE created_at > $boundary AND is_deleted=FALSE`.\n4. Pending reports: `SELECT COUNT(*) FROM content_reports WHERE status='pending'`.\n5. Active communities: `SELECT community_id, COUNT(*) FROM forum_posts WHERE created_at > $boundary GROUP BY community_id`. |

---

## 🔔 6. NOTIFICATIONS ENGINE (EXTENSION)

*Upgrades passive notifications into an event-driven, scheduled alert system.*

| Actor | Action | Handler (Route) / Trigger | Database Tables | System Logic & Data Flow |
|:------|:-------|:--------------------------|:----------------|:-------------------------|
| **System** | Trial Alert Matching | Background task (on `INSERT INTO clinical_trials`) | `trial_alerts`, `clinical_trials`, `notifications` | 1. Triggered after trial insert/update.\n2. `SELECT * FROM trial_alerts WHERE is_active=TRUE`.\n3. For each alert: match `disease_area`, `location`, `phase` against new trial.\n4. For matches with `alert_frequency='instant'`: `INSERT INTO notifications (user_id, type='trial', title, message, link)` immediately.\n5. For `daily`/`weekly`: mark for batch (update `trial_alerts.last_notified` check in batch job). |
| **System** | Daily Digest Email | Cron (06:00 UTC daily) | `trial_alerts`, `clinical_trials`, `notifications`, `users` | 1. `SELECT DISTINCT user_id FROM trial_alerts WHERE alert_frequency='daily' AND is_active=TRUE`.\n2. For each user: find trials created since `last_notified` that match alert criteria.\n3. If matches found: compile digest → send email (background task) → `INSERT INTO notifications`.\n4. `UPDATE trial_alerts SET last_notified=NOW() WHERE user_id=$1 AND alert_frequency='daily'`. |
| **System** | Weekly Roundup | Cron (Monday 08:00 UTC) | Multiple tables | 1. `SELECT DISTINCT user_id FROM trial_alerts WHERE alert_frequency='weekly' AND is_active=TRUE`.\n2. Compile per-user: new matching trials, popular community posts (top 5 by likes), upcoming events (next 7 days).\n3. Send personalized newsletter email.\n4. Update `last_notified`. |
| **System** | Event Reminder | Cron (hourly) | `event_registrations`, `events`, `notifications` | 1. Find events: `SELECT * FROM events WHERE event_date = CURRENT_DATE + 1 AND status='upcoming'` (24h reminder).\n2. Find registered users: `SELECT user_id FROM event_registrations WHERE event_id=$1 AND status='registered'`.\n3. For each: `INSERT INTO notifications (user_id, type='event', title='Reminder: {event_title}', message='Starts in 24 hours', link='/events/{id}')`.\n4. Mark: `UPDATE events SET reminder_sent=TRUE WHERE event_id=$1`. |
| **System** | Moderation Escalation | Event handler (on report insert) | `content_reports`, `notifications` | 1. After `INSERT INTO content_reports`: count reports for same target.\n2. `SELECT COUNT(*) FROM content_reports WHERE target_type=$1 AND target_id=$2`.\n3. **If count >= 3:** auto-flag content (update `moderation_status='flagged'` on target table).\n4. Create urgent notification for all admins: "Content auto-flagged: {count} reports on {target_type} {target_id}". |
| **System** | HCP Verification Alert | Event handler | `notifications` | 1. **On submission:** `INSERT INTO notifications` for all `admin` users: "New HCP verification request from {display_name}".\n2. **On decision:** `INSERT INTO notifications` for the HCP user: "Verification {approved/rejected}: {notes}". |
| **System** | Org Membership Alert | Event handler | `notifications` | 1. **On join request:** Notify org admins (users with `organization_members.role='admin'` for that org): "New join request from {display_name}".\n2. **On decision:** Notify requesting user: "Your membership request was {approved/rejected}". |
| **System** | Cleanup Old Notifications | Cron (daily 04:00 UTC) | `notifications` | 1. `DELETE FROM notifications WHERE expires_at IS NOT NULL AND expires_at < NOW()`.\n2. `DELETE FROM notifications WHERE created_at < NOW() - INTERVAL '90 days' AND read = TRUE`. |

---

## 📝 MIDDLEWARE REFERENCE

*Quick reference for all Phase 2 middleware used in the action tables above.*

| Middleware | File | Checks | Failure Response |
|:-----------|:-----|:-------|:-----------------|
| `auth_required` | `app/api/middleware/auth_middleware.py` | 1. Valid JWT signature + not expired. 2. `jti` NOT in `token_blacklist`. 3. `users.status != 'suspended'` (auto-unsuspend if `suspended_until` passed). | `401` invalid/expired token. `401` revoked token. `403` suspended account with reason. |
| `admin_required` | `app/api/middleware/admin_middleware.py` | 1. Calls `auth_required`. 2. `users.user_type == 'admin'`. 3. Logs action to `audit_logs`. | `403 {"detail": "Platform admin access required"}` |
| `verified_hcp_required` | `app/api/middleware/hcp_middleware.py` | 1. Calls `auth_required`. 2. `users.user_type == 'hcp'`. 3. `users.is_verified == TRUE`. | `403 {"detail": "HCP verification required"}` or `403 {"detail": "HCP role required"}` |
| `org_admin_required(org_id)` | `app/api/middleware/org_admin_middleware.py` | 1. Calls `auth_required`. 2. `user_type == 'admin'` → PASS (platform admin). 3. OR: `organization_members` record with `role='admin'`, `status='approved'` for given `org_id` → PASS. | `403 {"detail": "Organization admin access required"}` |

---

## 📋 NEW DATABASE TABLES SUMMARY

| Table | Purpose | Key Columns | Indexes |
|:------|:--------|:------------|:--------|
| `clinical_observations` | HCP real-world trial feedback | `observation_id`, `doctor_id` (FK→users), `trial_id` (FK→clinical_trials), `severity`, `summary`, `data` (JSONB), `is_flagged` | doctor_id, trial_id, severity, is_flagged |
| `audit_logs` | Immutable admin action trail | `log_id`, `user_id` (FK→users, nullable), `action`, `target_type`, `target_id`, `metadata` (JSONB), `ip_address`, `created_at` | user_id, action, target(type+id), created_at DESC |
| `token_blacklist` | Invalidated JWT tokens | `id`, `jti` (unique), `user_id` (FK→users), `expires_at`, `blacklisted_at` | jti (unique), expires_at |
| `user_sessions` | Active session tracking | `session_id`, `user_id` (FK→users), `jti` (unique), `device_info`, `ip_address`, `created_at`, `last_active` | user_id, jti |

## 📋 TABLE MODIFICATIONS SUMMARY

| Table | Change | Details |
|:------|:-------|:--------|
| `users` | ADD `suspended_until` | `TIMESTAMP NULL` — auto-unsuspend date |
| `users` | ADD `suspended_reason` | `TEXT NULL` — admin-provided reason |
| `resources` | ADD `status` | `VARCHAR(50) DEFAULT 'published'` — pending/published/rejected |
| `resources` | ADD `uploaded_by` | `UUID NULL FK→users(id)` — uploader reference |
| `events` | ADD `reminder_sent` | `BOOLEAN DEFAULT FALSE` — notification tracking |

---

> **Document Version:** 1.0
> **Last Updated:** 2026-03-22
> **Status:** Implementation Contract — Ready for Engineering
