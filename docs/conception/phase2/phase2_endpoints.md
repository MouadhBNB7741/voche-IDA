# 📡 VOCE Platform | Phase 2 API Endpoints — RBAC & Advanced Systems

> **Base URL:** `/api/v1`
> **Auth:** JWT Bearer token in `Authorization` header
> **Format:** JSON request/response (except file uploads: multipart/form-data)
> **Pagination:** `?page=1&limit=20` (default limit: 20, max: 100)

---

## 📋 Table of Contents

1. [Auth & Security](#1-auth--security-extension)
2. [HCP System](#2-hcp-system-new-module)
3. [Organization Management](#3-organization-management-extension)
4. [Admin Panel](#4-admin-panel-new-module)
5. [Analytics](#5-analytics-new-module)
6. [Notifications Engine](#6-notifications-engine-background-system)

---

## 1. Auth & Security (Extension)

### `POST /auth/logout`

> Invalidates the current JWT token.

| Property | Value |
| :------- | :---- |
| **Middleware** | `auth_required` |
| **Tables** | `token_blacklist` |
| **Audit Log** | No (standard user action) |

**Request:** No body required. JWT extracted from Authorization header.

**Response `200`:**
```json
{ "message": "Successfully logged out" }
```

**Notes:** Extracts `jti` claim from JWT and inserts into `token_blacklist`. Token immediately becomes invalid for all subsequent requests.

---

### `GET /auth/sessions`

> Lists all active sessions for the authenticated user.

| Property | Value |
| :------- | :---- |
| **Middleware** | `auth_required` |
| **Tables** | `user_sessions` |

**Request:** No body. No query params.

**Response `200`:**
```json
{
  "sessions": [
    {
      "session_id": "uuid",
      "device_info": "Chrome 120 / Windows",
      "ip_address": "192.168.1.1",
      "created_at": "2026-03-20T10:00:00Z",
      "last_active": "2026-03-22T14:30:00Z",
      "is_current": true
    }
  ]
}
```

---

### `DELETE /auth/sessions/{session_id}`

> Revokes a specific session (logs out that device).

| Property | Value |
| :------- | :---- |
| **Middleware** | `auth_required` |
| **Tables** | `user_sessions`, `token_blacklist` |

**Response `200`:**
```json
{ "message": "Session revoked" }
```

**Errors:** `404` if session not found or not owned by user. `403` if attempting to revoke another user's session.

---

## 2. HCP System (New Module)

### `POST /doctors/verification`

> Submit HCP verification request with credentials.

| Property | Value |
| :------- | :---- |
| **Middleware** | `auth_required` |
| **Tables** | `users`, `audit_logs`, `notifications` |
| **Audit Log** | `hcp_verification_submitted` |
| **Notification** | → All platform admins |

**Request Body:**
```json
{
  "license_number": "MED-2024-12345",
  "institution": "Nairobi General Hospital",
  "country": "Kenya",
  "specialization": "Infectious Disease"
}
```

**Response `201`:**
```json
{
  "message": "Verification request submitted",
  "status": "pending",
  "submitted_at": "2026-03-22T20:00:00Z"
}
```

**Errors:** `400` if user already has a pending request. `403` if user_type not in (`patient`, `hcp`).

**Side Effects:** If `user_type='patient'`, auto-upgrades to `hcp` (unverified).

---

### `GET /doctors/verification/status`

> Check current verification status.

| Property | Value |
| :------- | :---- |
| **Middleware** | `auth_required` |
| **Tables** | `users` |

**Response `200`:**
```json
{
  "status": "pending|approved|rejected|none",
  "license_number": "MED-2024-12345",
  "institution": "Nairobi General Hospital",
  "submitted_at": "2026-03-22T20:00:00Z",
  "reviewed_at": null,
  "reviewed_by": null,
  "rejection_reason": null
}
```

---

### `GET /doctors/admin/verifications`

> List all pending HCP verification requests.

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `user_profiles` |
| **Query Params** | `?status=pending&page=1&limit=20` |

**Response `200`:**
```json
{
  "data": [
    {
      "user_id": "uuid",
      "display_name": "Dr. Jane Smith",
      "email": "jane@hospital.org",
      "verification": { "status": "pending", "license_number": "...", "institution": "...", "submitted_at": "..." },
      "created_at": "2026-03-20T10:00:00Z"
    }
  ],
  "meta": { "total": 5, "page": 1, "limit": 20 }
}
```

---

### `PATCH /doctors/admin/verifications/{user_id}`

> Approve or reject an HCP verification.

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `notifications`, `audit_logs` |
| **Audit Log** | `hcp_verified` or `hcp_rejected` |
| **Notification** | → Target HCP user |

**Request Body:**
```json
{
  "status": "approved|rejected",
  "notes": "License verified against national registry"
}
```

**Response `200`:**
```json
{ "message": "Verification approved", "user_id": "uuid", "is_verified": true }
```

**Side Effects (approved):** Sets `is_verified=TRUE`, `user_type='hcp'`. **Side Effects (rejected):** Sets rejection reason. User can re-submit.

---

### `POST /clinical-observations/`

> Submit a clinical observation about a trial.

| Property | Value |
| :------- | :---- |
| **Middleware** | `verified_hcp_required` |
| **Tables** | `clinical_observations`, `audit_logs`, `notifications` |
| **Audit Log** | `clinical_observation_submitted` |
| **Notification** | → Admins (only if severity = `critical`) |

**Request Body:**
```json
{
  "trial_id": "uuid",
  "severity": "low|medium|high|critical",
  "summary": "Observed increased adverse events in cohort B",
  "data": { "patient_count": 12, "adverse_event_type": "nausea", "onset_days": 3 }
}
```

**Response `201`:**
```json
{
  "observation_id": "uuid",
  "trial_id": "uuid",
  "severity": "high",
  "is_flagged": false,
  "created_at": "2026-03-22T20:00:00Z"
}
```

**Errors:** `404` if trial_id not found. `400` if invalid severity.

---

### `GET /clinical-observations/trial/{trial_id}`

> List all observations for a specific trial.

| Property | Value |
| :------- | :---- |
| **Middleware** | `verified_hcp_required` OR `admin_required` |
| **Tables** | `clinical_observations`, `users` |
| **Query Params** | `?page=1&limit=20&severity=critical` |

**Response `200`:**
```json
{
  "data": [
    {
      "observation_id": "uuid",
      "doctor_name": "Dr. Jane Smith",
      "severity": "critical",
      "summary": "Observed increased adverse events...",
      "is_flagged": true,
      "created_at": "2026-03-22T20:00:00Z"
    }
  ],
  "meta": { "total": 8, "page": 1, "limit": 20 }
}
```

---

### `GET /hcp/resources`

> Access HCP-exclusive resources.

| Property | Value |
| :------- | :---- |
| **Middleware** | `verified_hcp_required` |
| **Tables** | `resources` |
| **Query Params** | `?type=toolkit&category=clinical_protocols&page=1&limit=20` |

**Response `200`:** Same shape as `GET /resources` but filtered to `hcp_only = true`.

---

## 3. Organization Management (Extension)

### `GET /organizations/{org_id}/requests`

| Property | Value |
| :------- | :---- |
| **Middleware** | `org_admin_required(org_id)` |
| **Tables** | `organization_members`, `users` |
| **Query Params** | `?status=pending&page=1&limit=20` |

**Response `200`:**
```json
{
  "data": [
    { "user_id": "uuid", "display_name": "John Doe", "email": "john@example.com", "status": "pending", "joined_at": "2026-03-20T10:00:00Z" }
  ],
  "meta": { "total": 3, "page": 1, "limit": 20 }
}
```

---

### `POST /organizations/{org_id}/members/{user_id}/decide`

| Property | Value |
| :------- | :---- |
| **Middleware** | `org_admin_required(org_id)` |
| **Tables** | `organization_members`, `organizations`, `notifications`, `audit_logs` |
| **Audit Log** | `member_approved` or `member_rejected` |
| **Notification** | → Requesting user |

**Request Body:**
```json
{ "decision": "approved|rejected", "reason": "Welcome aboard!" }
```

**Response `200`:**
```json
{ "message": "Membership approved", "user_id": "uuid", "org_id": "uuid" }
```

---

### `POST /organizations/working-groups`

| Property | Value |
| :------- | :---- |
| **Middleware** | `org_admin_required(body.organization_id)` |
| **Tables** | `working_groups`, `working_group_members`, `audit_logs` |
| **Audit Log** | `working_group_created` |

**Request Body:**
```json
{
  "name": "HIV Vaccine Research",
  "description": "Collaborative group for HIV vaccine trials",
  "type": "research|advocacy|patient_support",
  "privacy_level": "public|private|invitation_only",
  "organization_id": "uuid"
}
```

**Response `201`:**
```json
{ "group_id": "uuid", "name": "HIV Vaccine Research", "message": "Working group created" }
```

**Side Effect:** Creator auto-added as group admin.

---

### `PATCH /organizations/working-groups/{group_id}`

| Property | Value |
| :------- | :---- |
| **Middleware** | `org_admin_required(group.organization_id)` |
| **Tables** | `working_groups`, `audit_logs` |
| **Audit Log** | `working_group_updated` |

**Request Body (partial):**
```json
{ "name": "Updated Name", "privacy_level": "private", "is_active": false }
```

**Response `200`:**
```json
{ "message": "Working group updated", "group_id": "uuid" }
```

---

### `POST /resources` (Org Member Upload)

| Property | Value |
| :------- | :---- |
| **Middleware** | `auth_required` |
| **Tables** | `resources`, `organization_members`, `notifications` |
| **Notification** | → All platform admins |

**Request Body:**
```json
{
  "title": "Patient Consent Template",
  "type": "document|toolkit|video|course",
  "category": "patient_rights",
  "description": "Standard consent template for clinical trials",
  "url": "https://storage.example.com/template.pdf",
  "language": "en",
  "tags": ["consent", "clinical_trials"]
}
```

**Response `201`:**
```json
{ "resource_id": "uuid", "status": "pending", "message": "Resource submitted for approval" }
```

**Validation:** User must have `organization_members.status = 'approved'` in any org. Resource created with `status='pending'`.

---

## 4. Admin Panel (New Module)

### `GET /admin/users`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `user_profiles` |
| **Query Params** | `?role=hcp&status=active&q=search_term&page=1&limit=20` |

**Response `200`:**
```json
{
  "data": [
    { "id": "uuid", "display_name": "Jane Smith", "email": "jane@example.com", "user_type": "hcp", "status": "active", "is_verified": true, "created_at": "...", "last_login": "..." }
  ],
  "meta": { "total": 1250, "page": 1, "limit": 20 }
}
```

---

### `GET /admin/users/{user_id}`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `user_profiles`, `audit_logs`, `content_reports` |

**Response `200`:**
```json
{
  "user": { "id": "uuid", "display_name": "...", "email": "...", "user_type": "...", "status": "...", "is_verified": false, "verification": {}, "created_at": "...", "last_login": "..." },
  "profile": { "bio": "...", "interests": [], "specialization": "..." },
  "activity": { "total_posts": 12, "total_reports_filed": 2, "total_reports_against": 0 },
  "recent_audit_logs": [ { "action": "login", "created_at": "...", "metadata": {} } ]
}
```

---

### `POST /admin/users/{user_id}/suspend`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `token_blacklist`, `user_sessions`, `notifications`, `audit_logs` |
| **Audit Log** | `user_suspended` |
| **Notification** | → Suspended user |

**Request Body:**
```json
{ "duration_days": 7, "reason": "Community guidelines violation" }
```

`duration_days: null` = permanent suspension.

**Response `200`:**
```json
{ "message": "User suspended", "user_id": "uuid", "suspended_until": "2026-03-29T20:00:00Z" }
```

**Guard:** Cannot suspend users where `user_type = 'admin'`. Returns `400`.

**Side Effects:** All user tokens blacklisted. All sessions deleted. User immediately locked out.

---

### `POST /admin/users/{user_id}/unsuspend`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `notifications`, `audit_logs` |
| **Audit Log** | `user_unsuspended` |
| **Notification** | → Reinstated user |

**Response `200`:**
```json
{ "message": "User reinstated", "user_id": "uuid" }
```

---

### `GET /admin/moderation/queue`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `content_reports`, `users` |
| **Query Params** | `?status=pending&type=post&page=1&limit=20` |

**Response `200`:**
```json
{
  "data": [
    {
      "report_id": "uuid", "target_type": "post", "target_id": "uuid",
      "reason": "misinformation", "description": "Contains unverified medical claims",
      "reporter_name": "John Doe", "total_reports": 5,
      "status": "pending", "created_at": "..."
    }
  ],
  "meta": { "total": 12, "page": 1, "limit": 20 }
}
```

---

### `POST /admin/moderation/{report_id}/resolve`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `content_reports`, `forum_posts`/`comments`, `users`, `notifications`, `audit_logs` |
| **Audit Log** | `report_resolved` |
| **Notification** | → Content author (if `notify_user=true`) |

**Request Body:**
```json
{
  "action": "approve|remove_content|warn_user|ban_user",
  "notes": "Content violates community guidelines",
  "notify_user": true
}
```

**Response `200`:**
```json
{ "message": "Report resolved", "report_id": "uuid", "action_taken": "remove_content" }
```

---

### `POST /admin/trials/import`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `clinical_trials`, `trial_sites`, `audit_logs` |
| **Content-Type** | `multipart/form-data` |
| **Audit Log** | `trial_imported` |

**Request:** File upload (CSV or JSON).

**Response `200`:**
```json
{ "imported": 45, "updated": 12, "failed": 3, "errors": [{"row": 5, "field": "phase", "message": "Invalid value 'Phase X'"}] }
```

---

### `POST /admin/trials`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `clinical_trials`, `audit_logs` |
| **Audit Log** | `trial_created` |

**Request Body:**
```json
{
  "title": "Study of Drug X for HIV Prevention",
  "nct_id": "NCT00000001",
  "disease_area": "HIV",
  "phase": "Phase 3",
  "status": "recruiting",
  "sponsor": "WHO",
  "countries": ["Kenya", "South Africa"],
  "eligibility_criteria": "Adults 18-65, HIV-negative",
  "start_date": "2026-04-01",
  "max_enrollment": 500,
  "contact_email": "trials@who.int"
}
```

**Response `201`:**
```json
{ "trial_id": "uuid", "title": "Study of Drug X...", "message": "Trial created" }
```

---

### `PATCH /admin/trials/{trial_id}`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `clinical_trials`, `audit_logs` |
| **Audit Log** | `trial_updated` (includes changed fields) |

**Request Body (partial):**
```json
{ "status": "active", "current_enrollment": 120 }
```

**Response `200`:**
```json
{ "message": "Trial updated", "trial_id": "uuid" }
```

---

### `PUT /resources/{resource_id}/status`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `resources`, `notifications`, `audit_logs` |
| **Audit Log** | `resource_approved` or `resource_rejected` |
| **Notification** | → Uploader |

**Request Body:**
```json
{ "status": "published|rejected", "notes": "Content verified and approved" }
```

**Response `200`:**
```json
{ "message": "Resource published", "resource_id": "uuid" }
```

---

### `POST /admin/content/feature`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `resources`/`forum_posts`/`events`, `audit_logs` |
| **Audit Log** | `content_featured` |

**Request Body:**
```json
{
  "content_type": "resource|post|event",
  "content_id": "uuid",
  "featured": true,
  "featured_until": "2026-06-01"
}
```

**Response `200`:**
```json
{ "message": "Content featured", "content_type": "resource", "content_id": "uuid" }
```

---

## 5. Analytics (New Module)

### `GET /admin/analytics`

| Property | Value |
| :------- | :---- |
| **Middleware** | `admin_required` |
| **Tables** | `users`, `clinical_trials`, `trial_saves`, `forum_posts`, `comments`, `events`, `content_reports` |
| **Query Params** | `?period=day\|week\|month\|all` |

**Response `200`:**
```json
{
  "period": "month",
  "generated_at": "2026-03-22T20:00:00Z",
  "users": { "total": 1250, "active_30d": 450, "new_30d": 78, "by_role": {"patient": 980, "hcp": 120, "org_member": 100, "admin": 5, "caregiver": 45}, "verified_hcps": 85 },
  "trials": { "total": 340, "saves": 892, "by_phase": {"Phase 1": 45, "Phase 2": 89, "Phase 3": 156, "Phase 4": 50} },
  "community": { "posts": 234, "replies": 891, "reports_pending": 12 },
  "events": { "upcoming": 5, "registrations": 234 }
}
```

### `GET /admin/analytics/users`

Same middleware/params. Returns only `users` section of above response.

### `GET /admin/analytics/trials`

Same middleware/params. Returns only `trials` section.

### `GET /admin/analytics/community`

Same middleware/params. Returns only `community` section.

### `GET /admin/analytics/top-diseases`

| **Query Params** | `?limit=20` |

**Response `200`:**
```json
{
  "data": [
    { "disease": "HIV", "trial_count": 120, "save_count": 456 },
    { "disease": "Malaria", "trial_count": 89, "save_count": 312 }
  ]
}
```

---

## 6. Notifications Engine (Background System)

These are **not HTTP endpoints** — they are system-level background tasks.

| Task | Trigger | Tables | Output |
| :--- | :------ | :----- | :----- |
| Trial Alert Matching | On trial INSERT/UPDATE | `trial_alerts`, `clinical_trials`, `notifications` | In-app notifications for `instant` users; queued for `daily`/`weekly` |
| Daily Digest | Cron 06:00 UTC | `trial_alerts`, `notifications`, `users` | Digest email + notification per user |
| Weekly Roundup | Cron Mon 08:00 UTC | Multiple | Newsletter email with trials + posts + events |
| Event Reminders | Cron hourly | `event_registrations`, `events`, `notifications` | 24h reminder notification |
| Moderation Escalation | On report insert (count ≥ 3) | `content_reports`, `notifications` | Admin notification + auto-flag content |
| HCP Verification Alert | On submit / on decision | `notifications` | Admin notification (submit) / user notification (decision) |
| Org Membership Alert | On join / on decision | `notifications` | Org admin notification (join) / user notification (decision) |
| Token Cleanup | Cron 03:00 UTC | `token_blacklist`, `password_reset_tokens` | DELETE expired rows |
| Notification Cleanup | Cron 04:00 UTC | `notifications` | DELETE expired + old read notifications |
| Auto-Unsuspend | Cron every 15 min | `users` | UPDATE suspended users past their `suspended_until` |

---

## 📋 Endpoint Summary Table

| # | Method | Route | Middleware | Module |
|:--|:-------|:------|:-----------|:-------|
| 1 | `POST` | `/auth/logout` | `auth_required` | Auth |
| 2 | `GET` | `/auth/sessions` | `auth_required` | Auth |
| 3 | `DELETE` | `/auth/sessions/{session_id}` | `auth_required` | Auth |
| 4 | `POST` | `/doctors/verification` | `auth_required` | HCP |
| 5 | `GET` | `/doctors/verification/status` | `auth_required` | HCP |
| 6 | `GET` | `/doctors/admin/verifications` | `admin_required` | HCP |
| 7 | `PATCH` | `/doctors/admin/verifications/{user_id}` | `admin_required` | HCP |
| 8 | `POST` | `/clinical-observations/` | `verified_hcp_required` | HCP |
| 9 | `GET` | `/clinical-observations/trial/{trial_id}` | `verified_hcp_required` | HCP |
| 10 | `GET` | `/hcp/resources` | `verified_hcp_required` | HCP |
| 11 | `GET` | `/organizations/{org_id}/requests` | `org_admin_required` | Org |
| 12 | `POST` | `/organizations/{org_id}/members/{user_id}/decide` | `org_admin_required` | Org |
| 13 | `POST` | `/organizations/working-groups` | `org_admin_required` | Org |
| 14 | `PATCH` | `/organizations/working-groups/{group_id}` | `org_admin_required` | Org |
| 15 | `POST` | `/resources` | `auth_required` | Org |
| 16 | `GET` | `/admin/users` | `admin_required` | Admin |
| 17 | `GET` | `/admin/users/{user_id}` | `admin_required` | Admin |
| 18 | `POST` | `/admin/users/{user_id}/suspend` | `admin_required` | Admin |
| 19 | `POST` | `/admin/users/{user_id}/unsuspend` | `admin_required` | Admin |
| 20 | `GET` | `/admin/moderation/queue` | `admin_required` | Admin |
| 21 | `POST` | `/admin/moderation/{report_id}/resolve` | `admin_required` | Admin |
| 22 | `POST` | `/admin/trials/import` | `admin_required` | Admin |
| 23 | `POST` | `/admin/trials` | `admin_required` | Admin |
| 24 | `PATCH` | `/admin/trials/{trial_id}` | `admin_required` | Admin |
| 25 | `PUT` | `/resources/{resource_id}/status` | `admin_required` | Admin |
| 26 | `POST` | `/admin/content/feature` | `admin_required` | Admin |
| 27 | `GET` | `/admin/analytics` | `admin_required` | Analytics |
| 28 | `GET` | `/admin/analytics/users` | `admin_required` | Analytics |
| 29 | `GET` | `/admin/analytics/trials` | `admin_required` | Analytics |
| 30 | `GET` | `/admin/analytics/community` | `admin_required` | Analytics |
| 31 | `GET` | `/admin/analytics/top-diseases` | `admin_required` | Analytics |

**Total: 31 new/extended endpoints + 10 background tasks**

---

> **Document Version:** 1.0
> **Last Updated:** 2026-03-22
> **Status:** Ready for Engineering Implementation
