# 🏗️ VOCE Platform | Phase 2 Backend Conception — RBAC & Advanced Systems

> **Document Purpose:** Defines the backend architecture for Phase 2: router structure, middleware stack, service layer, dependency injection, and background jobs. Engineers should implement directly from this document.
>
> **Prerequisite:** Phase 1 backend is fully implemented (see `backend/.agent/progress.md`).
>
> **Stack:** Python (FastAPI) · PostgreSQL 16+ · asyncpg · Pydantic v2 · JWT (PyJWT)

---

## 1. Phase 2 Folder Structure

Building on the existing Phase 1 structure:

```
backend/
├─ app/
│  ├─ api/
│  │  ├─ middleware/
│  │  │  ├─ auth_middleware.py          ← MODIFY (add blacklist + suspension checks)
│  │  │  ├─ org_admin_middleware.py     ← EXISTS (extend for WG ownership)
│  │  │  ├─ admin_middleware.py         ← NEW (platform admin enforcement)
│  │  │  └─ hcp_middleware.py           ← NEW (verified HCP enforcement)
│  │  ├─ v1/
│  │  │  ├─ auth.py                     ← MODIFY (add logout, sessions)
│  │  │  ├─ doctors.py                  ← EXISTS (extend admin verifications)
│  │  │  ├─ clinical_observations.py    ← EXISTS or NEW
│  │  │  ├─ organizations.py            ← EXISTS (extend admin actions)
│  │  │  ├─ resources.py                ← MODIFY (add upload + approval)
│  │  │  ├─ admin.py                    ← NEW (admin panel routes)
│  │  │  └─ analytics.py               ← NEW (analytics routes)
│  ├─ models/
│  │  ├─ audit_model.py                 ← NEW
│  │  ├─ session_model.py              ← NEW
│  │  ├─ token_blacklist_model.py      ← NEW
│  │  ├─ clinical_observation_model.py ← NEW
│  │  └─ analytics_model.py            ← NEW
│  ├─ schemas/
│  │  ├─ admin.py                       ← NEW
│  │  ├─ analytics.py                   ← NEW
│  │  ├─ clinical_observations.py       ← NEW
│  │  └─ sessions.py                    ← NEW
│  ├─ services/
│  │  ├─ audit_service.py               ← NEW
│  │  ├─ admin_service.py               ← NEW
│  │  ├─ analytics_service.py           ← NEW
│  │  ├─ notification_service.py        ← NEW (event-driven notifications)
│  │  └─ scheduler_service.py           ← NEW (cron/background jobs)
│  ├─ tasks/
│  │  ├─ trial_alert_task.py            ← NEW (trial alert matching)
│  │  ├─ digest_task.py                 ← NEW (daily/weekly digests)
│  │  ├─ reminder_task.py               ← NEW (event reminders)
│  │  └─ cleanup_task.py                ← NEW (token/notification cleanup)
│  └─ main.py                           ← MODIFY (register new routers + startup tasks)
```

---

## 2. Middleware Stack

### 2.1 `auth_required` — MODIFY

**File:** `app/api/middleware/auth_middleware.py`

**Existing behavior:** Validates JWT, injects `user_id` into request state.

**Phase 2 additions:**

```
Flow:
1. Extract JWT from Authorization header
2. Decode JWT (verify signature + expiration)
3. Extract `jti` claim
4. ─── NEW ─── Check token_blacklist:
   │  SELECT 1 FROM token_blacklist WHERE jti = $1
   │  If found → 401 {"detail": "Token revoked"}
5. Fetch user: SELECT id, user_type, is_verified, status,
   │            suspended_until, suspended_reason FROM users WHERE id = $1
6. ─── NEW ─── Suspended user check:
   │  If status = 'suspended':
   │    If suspended_until IS NOT NULL AND suspended_until < NOW():
   │      → Auto-unsuspend: UPDATE users SET status='active',
   │        suspended_reason=NULL, suspended_until=NULL
   │    Else:
   │      → 403 {"detail": "Account suspended",
   │             "reason": suspended_reason,
   │             "until": suspended_until}
7. Inject into request.state:
   - user_id (UUID)
   - user_type (str)
   - is_verified (bool)
```

**Dependencies:** `TokenBlacklistModel`, `UserModel`

---

### 2.2 `admin_required` — NEW

**File:** `app/api/middleware/admin_middleware.py`

```python
async def admin_required(request: Request) -> dict:
    """
    1. Calls auth_required (gets user context)
    2. Checks user_type == 'admin'
    3. Returns user context if admin
    4. Raises 403 if not admin
    """
    user = await auth_required(request)
    if user["user_type"] != "admin":
        raise HTTPException(403, "Platform admin access required")
    return user
```

**Used by:** All `/admin/*` and `/admin/analytics/*` endpoints.

---

### 2.3 `verified_hcp_required` — NEW

**File:** `app/api/middleware/hcp_middleware.py`

```python
async def verified_hcp_required(request: Request) -> dict:
    """
    1. Calls auth_required
    2. Checks user_type == 'hcp'
    3. Checks is_verified == True
    4. Returns user context if verified HCP
    """
    user = await auth_required(request)
    if user["user_type"] != "hcp":
        raise HTTPException(403, "HCP role required")
    if not user["is_verified"]:
        raise HTTPException(403, "HCP verification required")
    return user
```

**Used by:** `POST /clinical-observations/`, `GET /clinical-observations/trial/{id}`, `GET /hcp/resources`

---

### 2.4 `org_admin_required` — EXTEND

**File:** `app/api/middleware/org_admin_middleware.py`

**Existing behavior:** Validates platform admin OR org-level admin for specific `org_id`.

**Phase 2 extension:** Also support working group ownership validation by resolving a `group_id` to its parent `organization_id` before checking admin status.

---

## 3. Router Structure

### 3.1 Auth & Security Router — MODIFY

**File:** `app/api/v1/auth.py`

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `POST` | `/auth/logout` | `auth_required` | `logout()` | `SessionService.invalidate_token(jti)` |
| `GET` | `/auth/sessions` | `auth_required` | `list_sessions()` | `SessionService.get_user_sessions(user_id)` |
| `DELETE` | `/auth/sessions/{session_id}` | `auth_required` | `revoke_session()` | `SessionService.revoke_session(session_id, user_id)` |

**Login modification:** After successful login, also insert `user_sessions` record.

---

### 3.2 HCP System Router

**File:** `app/api/v1/doctors.py` (extend existing)

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `POST` | `/doctors/verification` | `auth_required` | `submit_verification()` | `DoctorService.submit_verification(user_id, data)` |
| `GET` | `/doctors/verification/status` | `auth_required` | `get_verification_status()` | `DoctorService.get_status(user_id)` |
| `GET` | `/doctors/admin/verifications` | `admin_required` | `list_pending_verifications()` | `DoctorService.list_pending(page, limit)` |
| `PATCH` | `/doctors/admin/verifications/{user_id}` | `admin_required` | `review_verification()` | `DoctorService.review(user_id, decision, admin_id)` |

**File:** `app/api/v1/clinical_observations.py`

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `POST` | `/clinical-observations/` | `verified_hcp_required` | `submit_observation()` | `ClinicalObservationService.create(doctor_id, data)` |
| `GET` | `/clinical-observations/trial/{trial_id}` | `verified_hcp_required` | `get_trial_observations()` | `ClinicalObservationService.list_by_trial(trial_id, page, limit)` |

**File:** `app/api/v1/resources.py` (extend — add HCP filter)

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `GET` | `/hcp/resources` | `verified_hcp_required` | `get_hcp_resources()` | `ResourceService.list_hcp_only(page, limit, filters)` |

---

### 3.3 Organization Management Router — EXTEND

**File:** `app/api/v1/organizations.py` (extend existing)

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `GET` | `/organizations/{org_id}/requests` | `org_admin_required` | `get_join_requests()` | `OrgService.list_requests(org_id, status, page, limit)` |
| `POST` | `/organizations/{org_id}/members/{user_id}/decide` | `org_admin_required` | `decide_membership()` | `OrgService.decide_member(org_id, user_id, decision, admin_id)` |
| `POST` | `/organizations/working-groups` | `org_admin_required` | `create_working_group()` | `OrgService.create_working_group(data, admin_id)` |
| `PATCH` | `/organizations/working-groups/{group_id}` | `org_admin_required` | `update_working_group()` | `OrgService.update_working_group(group_id, data, admin_id)` |
| `GET` | `/organizations/working-groups/{group_id}/requests` | `org_admin_required` | `get_wg_requests()` | `OrgService.list_wg_requests(group_id, status)` |
| `POST` | `/organizations/working-groups/{group_id}/members/{user_id}/decide` | `org_admin_required` | `decide_wg_membership()` | `OrgService.decide_wg_member(group_id, user_id, decision)` |
| `POST` | `/resources` | `auth_required` | `upload_resource()` | `ResourceService.create_pending(data, user_id)` |

---

### 3.4 Admin Panel Router — NEW

**File:** `app/api/v1/admin.py`

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `GET` | `/admin/users` | `admin_required` | `list_users()` | `AdminService.list_users(filters, page, limit)` |
| `GET` | `/admin/users/{user_id}` | `admin_required` | `get_user_details()` | `AdminService.get_user_detail(user_id)` |
| `POST` | `/admin/users/{user_id}/suspend` | `admin_required` | `suspend_user()` | `AdminService.suspend(user_id, duration, reason, admin_id)` |
| `POST` | `/admin/users/{user_id}/unsuspend` | `admin_required` | `unsuspend_user()` | `AdminService.unsuspend(user_id, admin_id)` |
| `POST` | `/admin/users/{user_id}/verify-hcp` | `admin_required` | `verify_hcp()` | `AdminService.verify_hcp(user_id, approved, notes, admin_id)` |
| `GET` | `/admin/moderation/queue` | `admin_required` | `get_moderation_queue()` | `AdminService.get_moderation_queue(status, type, page, limit)` |
| `POST` | `/admin/moderation/{report_id}/resolve` | `admin_required` | `resolve_report()` | `AdminService.resolve_report(report_id, action, notes, admin_id)` |
| `POST` | `/admin/trials/import` | `admin_required` | `import_trials()` | `AdminService.bulk_import(file)` |
| `POST` | `/admin/trials` | `admin_required` | `create_trial()` | `AdminService.create_trial(data, admin_id)` |
| `PATCH` | `/admin/trials/{trial_id}` | `admin_required` | `update_trial()` | `AdminService.update_trial(trial_id, data, admin_id)` |
| `PUT` | `/resources/{resource_id}/status` | `admin_required` | `approve_resource()` | `AdminService.set_resource_status(resource_id, status, notes, admin_id)` |
| `POST` | `/admin/content/feature` | `admin_required` | `feature_content()` | `AdminService.feature_content(content_type, content_id, featured, until)` |

---

### 3.5 Analytics Router — NEW

**File:** `app/api/v1/analytics.py`

| Method | Route | Middleware | Handler | Service Method |
| :----- | :---- | :--------- | :------ | :------------- |
| `GET` | `/admin/analytics` | `admin_required` | `get_overview()` | `AnalyticsService.get_overview(period)` |
| `GET` | `/admin/analytics/users` | `admin_required` | `get_user_metrics()` | `AnalyticsService.get_user_metrics(period)` |
| `GET` | `/admin/analytics/trials` | `admin_required` | `get_trial_metrics()` | `AnalyticsService.get_trial_metrics(period)` |
| `GET` | `/admin/analytics/community` | `admin_required` | `get_community_metrics()` | `AnalyticsService.get_community_metrics(period)` |
| `GET` | `/admin/analytics/top-diseases` | `admin_required` | `get_top_diseases()` | `AnalyticsService.get_top_diseases(limit)` |

---

## 4. Service Layer

### 4.1 Service Structure

Each service encapsulates business logic and delegates database operations to the model layer.

```
Router (HTTP handling)
  └─→ Middleware (auth, role check)
      └─→ Service (business logic, orchestration)
          ├─→ Model (database queries)
          ├─→ AuditService (audit logging side effect)
          └─→ NotificationService (notification side effect)
```

### 4.2 Service Definitions

#### `AuditService` — NEW

**File:** `app/services/audit_service.py`

| Method | Parameters | Logic |
| :----- | :--------- | :---- |
| `log(user_id, action, target_type, target_id, metadata, ip)` | All params | Insert into `audit_logs`. Called by all admin-level services. |

**Dependency Injection:** Injected into `AdminService`, `DoctorService`, `OrgService`, and admin middleware.

---

#### `SessionService` — NEW

**File:** `app/services/session_service.py` (or in auth service)

| Method | Parameters | Logic |
| :----- | :--------- | :---- |
| `create_session(user_id, jti, device_info, ip)` | From login | Insert `user_sessions` record |
| `get_user_sessions(user_id)` | user_id | SELECT from `user_sessions` ORDER BY last_active DESC |
| `revoke_session(session_id, user_id)` | Both | Verify ownership → blacklist token → delete session |
| `invalidate_token(jti)` | jti | Insert into `token_blacklist` |
| `invalidate_all_user_tokens(user_id)` | user_id | Bulk-blacklist all sessions → delete all sessions |
| `is_token_blacklisted(jti)` | jti | SELECT 1 FROM `token_blacklist` WHERE jti = $1 |
| `update_last_active(jti)` | jti | UPDATE `user_sessions` SET last_active = NOW() |

---

#### `AdminService` — NEW

**File:** `app/services/admin_service.py`

| Method | Parameters | Logic |
| :----- | :--------- | :---- |
| `list_users(role, status, q, page, limit)` | Filters | Query `users` + `user_profiles` with filters |
| `get_user_detail(user_id)` | user_id | Full JOIN: user + profile + audit logs + report counts |
| `suspend(user_id, duration, reason, admin_id)` | All | Guard: no admin-on-admin. Update status. Blacklist tokens. Notify. Audit log. |
| `unsuspend(user_id, admin_id)` | Both | Validate suspended. Update status. Notify. Audit log. |
| `verify_hcp(user_id, approved, notes, admin_id)` | All | Delegates to `DoctorService.review()` |
| `get_moderation_queue(status, type, page, limit)` | Filters | Query `content_reports` with aggregates |
| `resolve_report(report_id, action, notes, admin_id)` | All | Update report. Execute action on target. Notify. Audit log. |
| `bulk_import(file)` | UploadFile | Parse CSV/JSON. Validate rows. Upsert trials. Return report. |
| `create_trial(data, admin_id)` | Trial data | Insert `clinical_trials`. Audit log. |
| `update_trial(trial_id, data, admin_id)` | Partial update | Update fields. Audit log with diff. |
| `set_resource_status(resource_id, status, notes, admin_id)` | All | Update `resources.status`. Notify uploader. Audit log. |
| `feature_content(content_type, content_id, featured, until)` | All | Update target table `featured` column. Audit log. |

---

#### `AnalyticsService` — NEW

**File:** `app/services/analytics_service.py`

| Method | Parameters | Logic |
| :----- | :--------- | :---- |
| `get_overview(period)` | period string | Calls all sub-methods, returns unified object |
| `get_user_metrics(period)` | period | Aggregate COUNT queries on `users` with date filtering |
| `get_trial_metrics(period)` | period | Aggregate on `clinical_trials`, `trial_saves`, `user_activity_log` |
| `get_community_metrics(period)` | period | Aggregate on `forum_posts`, `comments`, `content_reports` |
| `get_top_diseases(limit)` | limit (default 20) | GROUP BY disease_area with save/search counts |

**Period calculation:** `day` → NOW() - 1 day, `week` → NOW() - 7 days, `month` → NOW() - 30 days, `all` → no filter.

---

#### `NotificationService` — NEW

**File:** `app/services/notification_service.py`

| Method | Parameters | Logic |
| :----- | :--------- | :---- |
| `notify_user(user_id, type, title, message, link)` | All | INSERT INTO `notifications` |
| `notify_admins(title, message, link)` | All | SELECT admin user_ids → bulk insert notifications |
| `notify_org_admins(org_id, title, message, link)` | All | SELECT org admin user_ids → bulk insert |

---

## 5. Background Jobs & Scheduled Tasks

### 5.1 Architecture

```
┌──────────────────────────────────────────────┐
│              FastAPI Application             │
│  ┌──────────────┐   ┌─────────────────────┐  │
│  │  API Routes  │   │  BackgroundTasks     │  │
│  │  (sync)      │   │  (async, on-event)   │  │
│  └──────────────┘   └─────────────────────┘  │
│                                              │
│  ┌──────────────────────────────────────────┐│
│  │        Scheduler (APScheduler)           ││
│  │  ┌────────┐ ┌────────┐ ┌──────────────┐ ││
│  │  │ Daily  │ │ Weekly │ │ Hourly       │ ││
│  │  │ Digest │ │ Roundup│ │ Event Remind │ ││
│  │  └────────┘ └────────┘ └──────────────┘ ││
│  │  ┌────────────────┐ ┌─────────────────┐ ││
│  │  │ Daily Cleanup  │ │ Trial Matching  │ ││
│  │  │ (tokens, notif)│ │ (on insert)     │ ││
│  │  └────────────────┘ └─────────────────┘ ││
│  └──────────────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

### 5.2 Task Definitions

**File:** `app/tasks/`

| Task | Trigger | File | Logic |
| :--- | :------ | :--- | :---- |
| Trial Alert Matching | On trial INSERT/UPDATE (background task) | `trial_alert_task.py` | Match new trial against active `trial_alerts`. Create instant notifications. Queue daily/weekly. |
| Daily Digest | Cron: 06:00 UTC daily | `digest_task.py` | Compile matching trials for `daily` frequency users. Send email + in-app notification. |
| Weekly Roundup | Cron: Monday 08:00 UTC | `digest_task.py` | Compile trials + popular posts + upcoming events. Personalize per user interests. |
| Event Reminders | Cron: Hourly | `reminder_task.py` | Find events starting within 24h where `reminder_sent=FALSE`. Notify registered users. Set flag. |
| Token Cleanup | Cron: 03:00 UTC daily | `cleanup_task.py` | DELETE expired `token_blacklist` rows. DELETE expired `password_reset_tokens`. |
| Notification Cleanup | Cron: 04:00 UTC daily | `cleanup_task.py` | DELETE expired notifications. DELETE read notifications older than 90 days. |
| Auto-Unsuspend | Cron: Every 15 min | `cleanup_task.py` | `UPDATE users SET status='active' WHERE status='suspended' AND suspended_until < NOW()`. |

### 5.3 Scheduler Setup

**In `main.py`:**

```python
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def start_scheduler():
    scheduler.add_job(daily_digest, "cron", hour=6, minute=0)
    scheduler.add_job(weekly_roundup, "cron", day_of_week="mon", hour=8)
    scheduler.add_job(event_reminders, "cron", minute=0)  # hourly
    scheduler.add_job(token_cleanup, "cron", hour=3, minute=0)
    scheduler.add_job(notification_cleanup, "cron", hour=4, minute=0)
    scheduler.add_job(auto_unsuspend, "cron", minute="*/15")
    scheduler.start()

@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown()
```

---

## 6. Router Registration in `main.py`

```python
# Phase 2 router additions
from app.api.v1.admin import admin_router
from app.api.v1.analytics import analytics_router

# Register Phase 2 routers
app.include_router(admin_router, prefix="/api/v1", tags=["Admin Panel"])
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])

# Note: HCP, Organization, Auth extensions are added to EXISTING routers
#       (doctors_router, organizations_router, auth_router)
```

---

## 7. Request → Response Flow

### Example: Admin Suspends User

```
1. POST /api/v1/admin/users/{user_id}/suspend
   Headers: Authorization: Bearer <admin_jwt>
   Body: {"duration_days": 7, "reason": "Community guidelines violation"}

2. admin_middleware.py
   → auth_required: validate JWT, check blacklist, check not suspended
   → admin_required: verify user_type == 'admin'

3. admin.py (router)
   → suspend_user(user_id, body, current_user)

4. AdminService.suspend(user_id, 7, "Community guidelines...", admin_id)
   → Guard: target user_type != 'admin'
   → UPDATE users SET status='suspended', suspended_reason=..., suspended_until=NOW()+7d
   → SessionService.invalidate_all_user_tokens(user_id)
   → NotificationService.notify_user(user_id, 'system', 'Account Suspended', reason)
   → AuditService.log(admin_id, 'user_suspended', 'user', user_id, {reason, duration})

5. Response: 200 {"message": "User suspended", "suspended_until": "2026-03-29T..."}
```

---

> **Document Version:** 1.0
> **Last Updated:** 2026-03-22
> **Status:** Ready for Engineering Implementation
