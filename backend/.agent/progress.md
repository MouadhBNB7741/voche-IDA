# Backend Progress Tracking

## Completed Tasks

* ✅ Auth endpoints implemented (`app/api/v1/auth.py`)
* ✅ Profile endpoints implemented (`app/api/v1/users.py`)
* ✅ JWT integration
* ✅ Raw SQL integration via Model Layer
* ✅ Existing DB schema respected

---

## 🆕 Architecture Enhancements

* ✅ Introduced model layer abstraction (Raw SQL encapsulated) in `app/models/`

  * `base_model.py`: Base DB logic
  * `user_model.py`: User CRUD
  * `profile_model.py`: Profile logic
  * `password_reset_model.py`: Token logic
* ✅ Refactored Pydantic Schemas to `app/schemas/`

  * `auth.py`: Authentication schemas
  * `user.py`: User/Profile schemas
  * Removed duplicate logic from `models/schemas.py`
  * Fixed type hinting (`Optional`, `Union`, `List`)
* ✅ Removed SQL from route layer (`auth.py`, `users.py`)
* ✅ Centralized query logic in models
* ✅ Added full pytest test suite in `app/tests/`
* ✅ Added QA validation pass
* ✅ Improved error handling consistency
* ✅ Verified DB schema compliance

---

## Testing Coverage

* ✅ Auth endpoints fully tested (`test_auth.py`)

  * Register, Login, Me, Update Password
* ✅ Profile endpoints fully tested (`test_users.py`)

  * Update, Completion Logic
* ✅ Schema validation tested (`test_schemas.py`)
* ✅ Edge cases covered (invalid emails, bad passwords)
* ✅ Token lifecycle covered (reset flow basics)
* ✅ Security flows validated

---


## Clinical Domain Implementation (Completed)

### 🔍 Analysis & Refactoring
*   **Architecture**: PASS. Follows Model-Service-Controller pattern.
*   **Router**: Fixed prefix issue. Now serves `/trials`, `/alerts/trials`, `/users/me/saved-trials` correctly as per documentation.
*   **Database Compliance**: PASS. 
    *   Strict adherence to `clinical_trials`, `trial_sites`, `trial_saves`, `trial_alerts`.
    *   Removed reference to non-existent `sponsors` and `trial_disease_areas` tables.
    *   Used `jsonb` columns for `countries` and `metadata`.
*   **Schema Validation**: PASS.
    *   Added `Literal` types for Phases, Statuses, Frequencies.
    *   Ensured `TrialDetail` matches DB columns.
*   **Security**: PASS.
    *   Authenticated routes for Save, Alert, Interest.
    *   `is_saved` flag computed securely for logged-in users.

### 🧪 Testing
*   Created `app/tests/test_clinical.py`.
*   **Result**: ✅ ALL PASS (5/5 tests)
*   **Coverage**:
    *   ✅ Trial Search (Filters, Keyword, Pagination) - *Fixed Query params binding*
    *   ✅ Trial Details (Valid/Invalid ID) - *Fixed ID alias*
    *   ✅ Save/Unsave Trial (Auth, Duplicates)
    *   ✅ Saved Trials List
    *   ✅ Alerts (Create, List, Update, Delete) - *Fixed JSON deserialization*
    *   ✅ Express Interest (Mocked Email Service)

---

## Notes

* **Architecture**: Clean "Model-Service-Controller" style.
* **Schemas**: Separated into domain-specific files for better maintainability.
* **Security**: Security is hardened. No PII leaks in responses.
* **Testing**: Tests use the dev database currently; ensure a separate test DB is configured for CI.

---

## Notification & Verification Implementation (Completed)

### 🔍 Features
*   **Notification Preferences**:
    *   Added `notification_preferences` JSONB column to `users` table.
    *   Implemented `PATCH /api/v1/users/me/notifications`.
    *   Added `NotificationPreferences` Pydantic schema with deep merge logic.
*   **HCP Verification**:
    *   Added `verification` JSONB column to `users` table.
    *   Implemented `POST /api/v1/users/me/verification` with file upload.
    *   Restricted to HCP role only.
    *   Added basic file storage and validation.

### 🧪 Testing
*   Created `app/tests/test_users_preferences.py`.
*   **Coverage**:
    *   ✅ Update Notification Preferences (Persistence, Validation, Deep Merge).
    *   ✅ Submit Verification (HCP Role Check, File Upload, Status Update).
    *   ✅ Access Control (Patient cannot verify).

### 📝 Documentation
*   Updated `docs/conception/dbStrucutre.md` to reflect new schema columns.
*   Updated `app/db/schema.sql` for test database consistency.

## Database Infrastructure (Updated)

### 🏗 Initialization
*   ✅ Refactored initialization logic out of `main.py` into `app/db/init_db.py`.
*   🚀 Server automatically runs `schema.sql` and `indexes.sql` on fresh setup.
### 🔐 Security & Middleware
*   ✅ Implemented and optimized `auth_middleware` and `_verify_token` in `app/api/middleware/auth_middleware.py`.
*   🛡️ Handles both STRICT (401) and OPTIONAL (None) authentication flows with shared logic.
*   🔄 Updated `auth.py`, `users.py`, and `clinical.py` routes to use the new middleware.
*   🧹 Removed redundant `app/api/dependencies/jwt_auth.py` to eliminate code duplication.

### ⚡ Performance
*   ✅ Added optimized indexes in `app/db/indexes.sql`:
    *   GIN index on `notification_preferences`.
    *   GIN index on `verification`.
    *   B-tree functional index on `verification->>'status'` for fast filtering.


---

## Community & Forums Module (Completed)
Status: ✅ Implemented

### Endpoints (all under `/api/v1/community`)
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/` | Public | List active communities (paginated, filterable, sortable) |
| GET | `/{community_id}` | Public | Get single community |
| GET | `/feed` | Required | Global feed across all communities |
| GET | `/{community_id}/posts` | Required | List posts in a community |
| POST | `/{community_id}/posts` | Required | Create post in community |
| GET | `/{community_id}/posts/{post_id}` | Required | Get post details + replies |
| PATCH | `/{community_id}/posts/{post_id}` | Required | Edit post (author/admin) |
| DELETE | `/{community_id}/posts/{post_id}` | Required | Soft delete post (author/admin) |
| POST | `/{community_id}/posts/{post_id}/replies` | Required | Reply to post |
| PATCH | `/{community_id}/replies/{id}` | Required | Edit reply (author/admin) |
| DELETE | `/{community_id}/replies/{id}` | Required | Delete reply (author/admin) |
| POST | `/{community_id}/posts/{post_id}/like` | Required | Like post |
| POST | `/{community_id}/replies/{id}/like` | Required | Like reply |
| POST | `/{community_id}/report` | Required | Report content (auto-flag at ≥10) |
| GET | `/admin/reports` | Admin | List reports globally (paginated, status filter) |
| PATCH | `/admin/reports/{id}` | Admin | Resolve/review report |
| DELETE | `/admin/reports/{id}` | Admin | Delete report |

### Design Decisions
- **Community-scoped URLs**: All post/reply/like/report endpoints are nested under `/{community_id}/...` for data isolation
- **Likes-only system**: Both `forum_posts` and `comments` use `likes_count` (no upvotes/downvotes)
- **community_id in URL, not body**: `CreatePostRequest` doesn't include `community_id` — it's a path param
- **Admin reports are global**: Admin moderation endpoints don't include community_id (platform-level concern); optional `?community_id=` filter available
- **Route ordering**: Admin routes (`/admin/...`) defined before `/{community_id}/...` routes to prevent UUID matching conflicts
- **Auth**: Uses `auth_middleware` from `app/api/middleware/auth_middleware.py`
- **Auto-flag threshold**: 10 reports on same target → moderation_status = 'flagged'

### Files
- Model: `app/models/community_model.py`
- Schema: `app/schemas/community.py`
- Route: `app/api/v1/community.py`
- Tests: `app/tests/test_community.py`

---


## Healthcare Features Implementation (Completed)
Status: ✅ Implemented

### 🩺 Doctor Verification
*   **Endpoints**: `POST /doctors/verification`, `GET /doctors/verification`, `GET /doctors/admin/verifications`, `PATCH /doctors/admin/verifications/{id}`.
*   **Logic**: `DoctorModel` handles role promotion (to `hcp`) and verification status (JSONB update).
*   **Tests**: `test_doctor_verification.py` - Full flow verified.

### 📋 Clinical Observations
*   **Endpoints**: `POST /clinical-observations/`, `GET /clinical-observations/trial/{id}`.
*   **Logic**: `ClinicalModel` handles observation creation and auto-flagging of critical issues.
*   **Schema**: `clinical_observations` table linked to trials and doctors.
*   **Tests**: `test_clinical_observations.py` - Verified permissions and data integrity.

### 🛡️ Reports & Moderation
*   **Audit**: Confirmed `CommunityModel` and `content_reports` table support robust reporting (posts/comments/users).
*   **System**: Re-usable `target_type` polymorphism.

### 🔧 Improvements
*   **User Profile**: Fixed JSONB merging bug in `ProfileModel` and `get_me` endpoint.
*   **Testing**: Improved test reliability and fixed payload issues.
---

## Resources & Education Module (Completed)
Status: ✅ Implemented

### Endpoints (under `/api/v1/resources`)
| Method | URL | Auth | Description |
|--------|-----|------|-------------|
| GET | `/` | Public | List resources (filterable, sortable, paginated) |
| GET | `/{id}` | Public | Get resource details, ratings, and related items |
| GET | `/{id}/download` | Optional | Get mockup download URL (increments downloads) |
| POST | `/{id}/rating` | Required | Create or update resource rating (updates avg) |
| PATCH | `/{id}/progress` | Required | Update usage progress |

### Details
- **Tests coverage**: ✅ ALL PASS (List, Details, Download Auth/Public, Rating CRUD + Avg, Progress)
- **Security validation**: Enforced auth strictly using `auth_middleware`
- **DB changes**: 
  - Created dedicated `resource_progress` table
  - Added composite PK (resource_id, user_id)
  - Added indexes
  - Added CHECK constraint
---


## Organizations & Working Groups API — Audited & Secured
Status: ✅ Implemented & Audited


### 🏢 Organization Management (`/api/v1/organizations`)

| Method | URL | Auth | Description |
| --- | --- | --- | --- |
| **GET** | `/` | Public | List organizations (filtered by type/country, paginated or "show all") |
| **GET** | `/{org_id}` | Public | Detailed view: includes profile, member list, and active working groups |
| **GET** | `/{org_id}/requests` | Admin | **View Requests** List pending/approved join requests (Admin/Moderator only) |
| **POST** | `/{org_id}/join` | Required | Request to join an organization (requires verified user) |
| **POST** | `/{org_id}/members/{user_id}/decide` | Admin | **Accept/Refuse** membership (Platform Admin, Org Admin, or Moderator) |

---

### 👥 Working Groups (`/api/v1/organizations/working-groups`)

| Method | URL | Auth | Description |
| --- | --- | --- | --- |
| **GET** | `/` | Public | List groups (filtered by org, type, or privacy level, supports "show all") |
| **GET** | `/{group_id}` | Public | Detailed view: includes group details and its approved member list |
| **GET** | `/{group_id}/requests` | Admin | **View Requests** List pending/approved join requests (Admin/Moderator only) |
| **POST** | `/{group_id}/join` | Required | Join group (Auto-approve if **Public**; set to **Pending** if Private) |
| **POST** | `/{group_id}/members/{user_id}/decide` | Admin | **Accept/Refuse** group access (Platform Admin, associated Org Admin, or Moderator) |


### 🛡️ Security & Architecture Fixes (Audit)
*   **Role Logic Validation**: Extracted logic into `app/api/middleware/org_admin_middleware.py`.
    *   Fully validates `admin` user_type OR standard `org_member` with active admin (`role='admin'`) permissions tied to the specific `org_id`.
    *   Inherently blocked non-admin types (`patient`, `hcp`).
*   **Duplicate Membership Protection**: DB-level and query-level rejection of multiple join requests.
*   **Data Restrictions**: Correctly implemented constraints preventing injection attacks. Used direct `$1` parameterized queries across models.

### 🧪 Testing
*   Created and refined `app/tests/test_organizations.py`.
*   **Coverage**:
    *   ✅ List organizations (with filters)
    *   ✅ Get organization details
    *   ✅ Join organization (success, duplicate, unverified checks)
    *   ✅ Decide organization join (Platform Admin / Org Admin / Unauthorized bypass tested)
    *   ✅ List working groups (with filters)
    *   ✅ Join working groups (public auto-approve, private pending)
    *   ✅ Decide working group join (Platform Admin / Org Admin / Unauthorized bypass tested)
*   **Result**: ✅ ALL PASS (14/14 tests)

---

## Guidance for Azzedine

Hi! Here’s a **simple, detailed explanation** of how the backend is structured :

1. **Model Layer**

   * All database logic is in `app/models/`
   * Routes (`auth.py`, `users.py`) **don’t talk to the DB directly**.
     * Instead, they call functions in models like `UserModel.create_user()` or `ProfileModel.get_profile()`

2. **Schemas**

   * Schemas define the **shape of data** that goes in and out of the API.
     * `app/schemas/auth.py` → login/register/reset requests & responses
     * `app/schemas/user.py` → user profile responses and updates
   * Pydantic automatically **validates the data** for you. For example, email must be valid, password must be 8+ chars.

3. **Raw SQL + asyncpg**

   * Instead of using an ORM like SQLAlchemy, we write **safe parameterized queries** in the models.
   * `asyncpg` allows **asynchronous database calls**, which is faster when many users hit the API.

4. **How to continue safely**

   * **Always import schemas from `app.schemas`**, When creating new endpoints:

     1. Add SQL logic in the **model layer**.
     2. Create Pydantic schema in `auth.py` or `user.py`.
     3. Use schema in the route (`api/v1/...`) for validation and response.
     4. Write **pytest tests** to validate your endpoint.
   * **Check `tests/`** to see examples of how requests/responses are validated.

1. **Tips**

   * Use `pytest -v` to run tests and see detailed results.
   * Use `mypy` for type checking if unsure about types.
   * For any data returned from the DB that is JSONB, always **deserialize it** before using in Pydantic models.
