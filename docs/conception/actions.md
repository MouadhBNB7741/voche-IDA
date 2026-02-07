# 📋 VOCE Platform – Complete MVP Action Matrix

**Scope:** MVP (Minimum Viable Product)  
**Golden Rule:** *Every action must either connect a user to a trial, educate them on advocacy, or build community engagement.*

> **Legend**
> * **FE:** Frontend (React) | **BE:** Backend (FastAPI Python) | **DB:** Database (PostgreSQL)
> * **Auth:** `🔒` Private / Requires Login | `🌍` Public / Anonymous | `🛡️` Admin Only

**Related Documentation:**
- [Backend Conception](./backend_conception.md) - Complete backend architecture
- [Database Structure](./dbStrucutre.md) - Full database schema
- [API Endpoints](./endPoint.md) - All API contracts
- [Platform Structure](./platformStructure.md) - Platform overview

---

## 1. AUTHENTICATION & PROFILE MODULE
*The entry point. Handles identity, role selection, and security.*

| Actor           | Action                      | Handler (Route)                | Database Tables                | System Logic & Data Flow                                                                                                                |
| :-------------- | :-------------------------- | :----------------------------- | :----------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------- |
| **Visitor** `🌍` | Register (Sign Up)          | `POST /auth/register`          | `users`, `user_profiles`       | 1. Validate email uniqueness.\n2. Hash password (Argon2).\n3. Create `users` record with role.\n4. Create `user_profiles` record.\n5. Return JWT token. |
| **Visitor** `🌍` | Login                       | `POST /auth/login`             | `users`                        | 1. Validate email exists.\n2. Verify password hash.\n3. Update `last_login`.\n4. Return JWT Access Token.                              |
| **Visitor** `🌍` | Request Password Reset      | `POST /auth/request-reset`     | `users`, `password_reset_tokens` | 1. Check if email exists.\n2. Generate secure token.\n3. Store in `password_reset_tokens` with 1-hour expiry.\n4. Send email (background task). |
| **Visitor** `🌍` | Verify Reset Token          | `GET /auth/verify-reset-token/{token}` | `password_reset_tokens` | 1. Validate token exists.\n2. Check not expired.\n3. Check not used.\n4. Return validity status.                                        |
| **Visitor** `🌍` | Reset Password              | `POST /auth/reset-password`    | `users`, `password_reset_tokens` | 1. Validate token.\n2. Hash new password.\n3. Update `users.password_hash`.\n4. Mark token as used.\n5. Invalidate other user tokens. |
| **User** `🔒`    | Get Current Profile         | `GET /auth/me`                 | `users`, `user_profiles`       | 1. Verify JWT token.\n2. Fetch user record.\n3. Join with profile.\n4. Return complete user object.                                    |
| **User** `🔒`    | Update Password             | `PUT /auth/update-password`    | `users`                        | 1. Verify current password.\n2. Hash new password.\n3. Update `password_hash`.                                                          |
| **User** `🔒`    | Update Profile              | `PATCH /users/me`              | `users`, `user_profiles`       | 1. Validate input.\n2. Update relevant fields.\n3. Recalculate `profile_completed`.\n4. Update timestamps.                            |
| **User** `🔒`    | Set Interests               | `PATCH /users/me`              | `user_profiles.interests`      | Updates `interests` JSONB array. Used for trial matching and personalization.                                                           |
| **User** `🔒`    | Update Notification Preferences | `PATCH /users/me/preferences/notifications` | `user_profiles` | Updates notification settings (email_alerts, push_notifications, frequency).                                                            |
| **User** `🔒`    | Update Privacy Settings     | `PATCH /users/me/preferences/privacy` | `user_profiles`         | Updates privacy preferences (profile_visibility, show_saved_trials, etc.).                                                              |
| **User** `🔒`    | Request Data Export (GDPR)  | `POST /users/me/data-export`   | All user-related tables        | 1. Queue background job.\n2. Compile all user data.\n3. Generate JSON/CSV.\n4. Email download link.                                   |
| **User** `🔒`    | Delete Account (GDPR)       | `DELETE /users/me`             | All user-related tables        | 1. Verify password.\n2. Soft delete user.\n3. Anonymize forum posts.\n4. 30-day grace period before permanent deletion.              |
| **HCP** `🔒`     | Upload Verification Docs    | `POST /hcp/verification`       | `user_profiles`                | 1. Upload license PDF (secure storage).\n2. Store `license_number`.\n3. Set `is_verified = FALSE`.\n4. Notify admin for review.       |
| **HCP** `🔒`     | Check Verification Status   | `GET /hcp/verification/status` | `users`, `user_profiles`       | Returns verification status (pending, approved, rejected) and admin notes.                                                              |

---

## 2. CLINICAL TRIAL NAVIGATOR MODULE
*The "Engine" of the platform. Search, Discovery, and Matching.*

| Actor            | Action                  | Handler (Route)                  | Database Tables                     | System Logic & Data Flow                                                                                                                        |
| :--------------- | :---------------------- | :------------------------------- | :---------------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------- |
| **Any** `🌍`      | Search Trials           | `GET /trials`                    | `clinical_trials`, `trial_sites`    | **Params:** `?disease=HIV&country=Kenya&phase=Phase3`\n**Logic:** PostgreSQL Full-Text Search (GIN index) + filters.\nResults ranked by relevance. |
| **Any** `🌍`      | View Trial Details      | `GET /trials/{id}`               | `clinical_trials`, `trial_sites`    | 1. Fetch trial metadata.\n2. Join with trial sites.\n3. For logged-in users: check if saved.\n4. Include contact info.                         |
| **User** `🔒`     | Save/Bookmark Trial     | `POST /trials/{id}/save`         | `trial_saves`                       | 1. Create record in `trial_saves`.\n2. Optional: user notes.\n3. Trigger notification on trial updates (future).                               |
| **User** `🔒`     | Remove Saved Trial      | `DELETE /trials/{id}/save`       | `trial_saves`                       | Delete record from `trial_saves`.                                                                                                               |
| **User** `🔒`     | Get Saved Trials        | `GET /users/me/saved-trials`     | `trial_saves`, `clinical_trials`    | Fetch all trials bookmarked by user with save timestamp.                                                                                        |
| **User** `🔒`     | Express Interest        | `POST /trials/{id}/interest`     | `user_activity_log`                 | 1. Log user intent.\n2. Email trial coordinator with user contact.\n3. Send confirmation email to user.\n4. Require explicit consent.          |
| **User** `🔒`     | Create Trial Alert      | `POST /alerts/trials`            | `trial_alerts`                      | 1. Define criteria (disease, location, phase).\n2. Set frequency (instant, daily, weekly).\n3. Create alert subscription.                     |
| **User** `🔒`     | List My Alerts          | `GET /alerts/trials`             | `trial_alerts`                      | Fetch all active alert subscriptions for user.                                                                                                  |
| **User** `🔒`     | Update Alert            | `PATCH /alerts/trials/{id}`      | `trial_alerts`                      | Modify alert criteria or frequency.                                                                                                             |
| **User** `🔒`     | Delete Alert            | `DELETE /alerts/trials/{id}`     | `trial_alerts`                      | Remove alert subscription.                                                                                                                      |
| **User** `🔒`     | Pause/Resume Alert      | `PATCH /alerts/trials/{id}/toggle` | `trial_alerts.is_active`          | Toggle alert active status without deleting.                                                                                                    |
| **HCP** `🔒`      | Access HCP Resources    | `GET /hcp/resources`             | `resources`                         | Requires `is_verified = TRUE`. Returns recruitment guides, consent templates, etc.                                                              |

---

## 3. COMMUNITY & FORUMS MODULE
*The "Sticky" features. Peer support and engagement.*

| Actor         | Action              | Handler (Route)                     | Database Tables                                      | System Logic & Data Flow                                                                                                     |
| :------------ | :------------------ | :---------------------------------- | :--------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------- |
| **Any** `🌍`   | List Communities    | `GET /communities`                  | `communities`                                        | Returns all active communities with member/post counts.                                                                      |
| **User** `🔒`  | List Forum Posts    | `GET /community/posts`              | `forum_posts`, `users`, `communities`                | **Params:** `?category=HIV&sort=popular`\nReturns posts with author, likes, replies count. Filters by community.            |
| **User** `🔒`  | View Post Details   | `GET /community/posts/{id}`         | `forum_posts`, `comments`, `users`                   | 1. Fetch post with author info.\n2. Fetch all comments (threaded).\n3. Increment `views_count`.                             |
| **User** `🔒`  | Create Post         | `POST /community/posts`             | `forum_posts`                                        | 1. Validate content.\n2. Auto-moderate (profanity filter).\n3. Set `moderation_status`.\n4. Notify community members.      |
| **User** `🔒`  | Edit Post           | `PATCH /community/posts/{id}`       | `forum_posts`                                        | 1. Verify ownership.\n2. Store edit history (optional).\n3. Update `updated_at`.\n4. Add "edited" flag.                    |
| **User** `🔒`  | Delete Post         | `DELETE /community/posts/{id}`      | `forum_posts.is_deleted`                             | **Auth:** Post author or admin.\nSoft delete (mark `is_deleted = TRUE`). Hide from view.                                    |
| **User** `🔒`  | Reply to Post       | `POST /community/posts/{id}/replies` | `comments`                                          | 1. Create comment record.\n2. Increment `forum_posts.replies_count`.\n3. Notify post author (if enabled).                  |
| **User** `🔒`  | Like Post/Reply     | `POST /community/posts/{id}/like`   | `forum_posts.upvotes_count` or `comments.likes_count` | Toggle like status. Update counter cache.                                                                                    |
| **User** `🔒`  | Report Content      | `POST /community/report`            | `content_reports`                                    | 1. Create report record.\n2. If reports > 3: auto-hide content.\n3. Queue for moderator review.\n4. No notification to reported user. |

---

## 4. EVENTS & WEBINARS MODULE
*Educational programming and networking.*

| Actor        | Action              | Handler (Route)                   | Database Tables                  | System Logic & Data Flow                                                                                         |
| :----------- | :------------------ | :-------------------------------- | :------------------------------- | :--------------------------------------------------------------------------------------------------------------- |
| **Any** `🌍`  | List Events         | `GET /events`                     | `events`                         | **Params:** `?type=webinar&date_from=2024-03-01`\nReturns upcoming and past events. Shows registration status. |
| **Any** `🌍`  | View Event Details  | `GET /events/{id}`                | `events`                         | Fetch complete event info including speakers, agenda, access link. Check user registration status.              |
| **User** `🔒` | Register for Event  | `POST /events/{id}/register`      | `event_registrations`            | 1. Check capacity.\n2. Create registration.\n3. Send confirmation email.\n4. Generate calendar invite (ICS).   |
| **User** `🔒` | Cancel Registration | `DELETE /events/{id}/register`    | `event_registrations`            | Update registration status to `cancelled`. Send cancellation confirmation.                                       |
| **User** `🔒` | Get My Events       | `GET /users/me/events`            | `event_registrations`, `events`  | Fetch all events user is registered for with access links.                                                       |

---

## 5. EDUCATIONAL RESOURCES MODULE
*Knowledge library and toolkits.*

| Actor        | Action              | Handler (Route)                   | Database Tables                     | System Logic & Data Flow                                                                                    |
| :----------- | :------------------ | :-------------------------------- | :---------------------------------- | :---------------------------------------------------------------------------------------------------------- |
| **Any** `🌍`  | List Resources      | `GET /resources`                  | `resources`                         | **Params:** `?type=video&category=patient_rights&language=en`\nReturns filtered resources with ratings.    |
| **Any** `🌍`  | View Resource       | `GET /resources/{id}`             | `resources`, `resource_ratings`     | Fetch complete resource info including ratings, reviews, related resources.                                 |
| **User** `🔒` | Download Resource   | `GET /resources/{id}/download`    | `resources.downloads`               | 1. Check access permissions (some require login).\n2. Increment download counter.\n3. Generate secure URL. |
| **User** `🔒` | Rate Resource       | `POST /resources/{id}/rating`     | `resource_ratings`, `resources`     | 1. Create/update rating (1-5 stars + review).\n2. Recalculate `resources.rating` average.                  |
| **User** `🔒` | Track Progress      | `PATCH /resources/{id}/progress`  | User progress tracking (future)     | For courses/multi-part content: save completion percentage.                                                 |
| **Org** `🔒`  | Upload Resource     | `POST /resources`                 | `resources`                         | 1. Upload file/link.\n2. Set `moderation_status = pending`.\n3. Notify admin for approval.                 |

---

## 6. AI ASSISTANT MODULE
*Intelligent navigation and information triage.*

| Actor        | Action              | Handler (Route)        | Database Tables          | System Logic & Data Flow                                                                                                        |
| :----------- | :------------------ | :--------------------- | :----------------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| **Any** `🌍`  | Send Chat Message   | `POST /ai/chat`        | None (stateless)         | **MVP:** Rule-based decision tree.\n1. Parse intent (trial search, general info, navigation).\n2. Return response + action suggestions.\n**Future:** LLM integration. |
| **Any** `🌍`  | Get Suggestions     | `GET /ai/suggestions`  | None                     | Returns contextual conversation starters based on user profile (if logged in).                                                  |

**Important Note:** 
- MVP assistant is **stateless** (no conversation history stored) for privacy
- Always includes medical disclaimer (no medical advice provided)
- Suggests resources and trials, never provides diagnoses

---

## 7. NOTIFICATIONS MODULE
*In-app alerts and engagement.*

| Actor        | Action                   | Handler (Route)                      | Database Tables   | System Logic & Data Flow                                           |
| :----------- | :----------------------- | :----------------------------------- | :---------------- | :----------------------------------------------------------------- |
| **User** `🔒` | Get Notifications        | `GET /notifications`                 | `notifications`   | Fetch user's notifications with filters (read/unread, type, date). |
| **User** `🔒` | Mark as Read             | `PATCH /notifications/{id}/read`     | `notifications`   | Update `read = TRUE`.                                              |
| **User** `🔒` | Mark All as Read         | `PATCH /notifications/mark-all-read` | `notifications`   | Update all unread notifications for user.                          |
| **User** `🔒` | Delete Notification      | `DELETE /notifications/{id}`         | `notifications`   | Remove notification from user's inbox.                             |
| **User** `🔒` | Clear All Notifications  | `DELETE /notifications`              | `notifications`   | Remove all notifications for user.                                 |

**Notification Types:**
- `trial` - New trial matches, saved trial updates
- `community` - Post replies, likes, mentions
- `event` - Event reminders, registration confirmations
- `system` - Platform updates, important announcements

---

## 8. ORGANIZATIONS & WORKING GROUPS MODULE
*Institutional partnerships and collaboration.*

| Actor         | Action                   | Handler (Route)                    | Database Tables                           | System Logic & Data Flow                                                                           |
| :------------ | :----------------------- | :--------------------------------- | :---------------------------------------- | :------------------------------------------------------------------------------------------------- |
| **Any** `🌍`   | List Organizations       | `GET /organizations`               | `organizations`                           | Returns directory of partner organizations filtered by type, country.                              |
| **Any** `🌍`   | View Organization        | `GET /organizations/{id}`          | `organizations`, `organization_members`   | Fetch organization profile with member list (if public), associated trials, resources.             |
| **User** `🔒`  | Join Organization        | `POST /organizations/{id}/join`    | `organization_members`                    | 1. Create membership request (status: pending).\n2. Notify org admin.\n3. Await approval.         |
| **Any** `🌍`   | List Working Groups      | `GET /working-groups`              | `working_groups`                          | Returns collaborative groups filtered by type, organization.                                       |
| **User** `🔒`  | Join Working Group       | `POST /working-groups/{id}/join`   | `working_group_members`                   | Create membership (status: pending or approved based on privacy level).                            |

---

## 9. SURVEYS & RESEARCH MODULE
*Data collection with informed consent.*

| Actor        | Action                  | Handler (Route)                   | Database Tables                          | System Logic & Data Flow                                                                                      |
| :----------- | :---------------------- | :-------------------------------- | :--------------------------------------- | :------------------------------------------------------------------------------------------------------------ |
| **User** `🔒` | List Available Surveys  | `GET /surveys`                    | `surveys`                                | Returns active surveys user is eligible for. Filters by target audience and completion status.                |
| **User** `🔒` | Get Survey Questions    | `GET /surveys/{id}`               | `surveys`, `survey_questions`            | Fetch complete survey with all questions, consent text, estimated time.                                       |
| **User** `🔒` | Submit Survey Response  | `POST /surveys/{id}/responses`    | `survey_responses`                       | 1. Verify consent.\n2. Validate responses.\n3. Apply anonymization if selected.\n4. Store responses.\n5. Thank user. |

**Privacy Controls:**
- Anonymization option allows submission without linking to user_id
- PII scrubbing pre-processes responses
- Explicit consent required before any data collection

---

## 10. SEARCH & DISCOVERY MODULE
*Global platform search.*

| Actor        | Action              | Handler (Route)            | Database Tables                                      | System Logic & Data Flow                                                                                |
| :----------- | :------------------ | :------------------------- | :--------------------------------------------------- | :------------------------------------------------------------------------------------------------------ |
| **Any** `🌍`  | Global Search       | `GET /search`              | Multiple tables                                      | **Params:** `?q=malaria&type=all`\nSearches across trials, resources, posts, events. Returns unified results. |
| **Any** `🌍`  | Autocomplete        | `GET /search/suggestions`  | Multiple tables                                      | Returns search term suggestions as user types. Fast prefix matching.                                    |

---

## 11. ADMIN & MODERATION MODULE `🛡️`
*Platform governance and content management.*

| Actor          | Action                    | Handler (Route)                        | Database Tables                | System Logic & Data Flow                                                                                           |
| :------------- | :------------------------ | :------------------------------------- | :----------------------------- | :----------------------------------------------------------------------------------------------------------------- |
| **Admin** `🛡️` | View Moderation Queue     | `GET /admin/moderation/queue`          | `content_reports`              | Fetch all pending reports with content snapshots, reporter info, report count.                                     |
| **Admin** `🛡️` | Resolve Report            | `POST /admin/moderation/{id}/resolve`  | `content_reports`, varies      | **Actions:** approve, remove_content, warn_user, ban_user.\nUpdate content, log decision, notify user if needed.  |
| **Admin** `🛡️` | View User Details         | `GET /admin/users/{id}`                | All user tables                | Complete user profile including activity history, reports, verification documents.                                 |
| **Admin** `🛡️` | Verify HCP                | `POST /admin/users/{id}/verify-hcp`    | `users.is_verified`            | 1. Review uploaded license.\n2. Update `is_verified = TRUE`.\n3. Notify user of approval.\n4. Grant HCP features. |
| **Admin** `🛡️` | Suspend/Ban User          | `POST /admin/users/{id}/suspend`       | `users.status`                 | 1. Set status to `suspended`.\n2. Set duration (days or permanent).\n3. Log reason.\n4. Notify user.              |
| **Admin** `🛡️` | Bulk Import Trials        | `POST /admin/trials/import`            | `clinical_trials`, `trial_sites` | **Input:** CSV/JSON file.\n**Logic:** Parse, validate, bulk insert. Return import report (success/failures).      |
| **Admin** `🛡️` | Create/Edit Trial         | `POST/PATCH /admin/trials`             | `clinical_trials`              | Manual trial entry for trials not in automated feeds.                                                              |
| **Admin** `🛡️` | Feature Content           | `POST /admin/content/feature`          | `resources`, `forum_posts`, etc. | Mark content as featured with optional expiration date. Appears on homepage/highlighted sections.                 |
| **Admin** `🛡️` | Platform Analytics        | `GET /admin/analytics`                 | Multiple tables                | Aggregated metrics: user growth, trial searches, top diseases, engagement rates, conversion funnels.               |
| **Admin** `🛡️` | Approve Resource          | `PUT /resources/{id}/status`           | `resources`                    | Change resource status from `pending` to `published`. Content becomes public.                                      |

**Admin Permissions Required:**
- Role must be `admin` or `moderator` in `users.user_type`
- JWT token verified with admin scope

---

## 12. SYSTEM & FEEDBACK MODULE
*Platform health and user feedback.*

| Actor        | Action              | Handler (Route)           | Database Tables        | System Logic & Data Flow                                                                   |
| :----------- | :------------------ | :------------------------ | :--------------------- | :----------------------------------------------------------------------------------------- |
| **Any** `🌍`  | Submit Feedback     | `POST /system/feedback`   | Feedback log (varies)  | 1. Category: bug, feature request, content issue.\n2. Optional screenshot.\n3. Create ticket. Generate ticket number. |
| **Any** `🌍`  | Get System Metadata | `GET /system/metadata`    | None (static config)   | Returns enums for dropdowns: countries, diseases, languages, trial phases, post categories. Ensures frontend/backend alignment. |
| **Any** `🌍`  | Health Check        | `GET /health`             | Database connection    | Verifies API is operational. Returns: status, version, database connectivity, timestamp.   |
| **System**   | System Status       | `GET /system/status`      | None                   | Returns: API version, maintenance mode flag, feature flags.                                |

---

## 13. SYSTEM AUTOMATION (Background Jobs)
*Scheduled tasks and event-driven processes.*

| Trigger              | Action                  | Technology          | Database Tables                | Logic                                                                                                                   |
| :------------------- | :---------------------- | :------------------ | :----------------------------- | :---------------------------------------------------------------------------------------------------------------------- |
| **New Trial Added**  | Trial Alert Matching    | Background Task     | `trial_alerts`, `notifications` | 1. Scan active alerts.\n2. Match new trial against criteria.\n3. Queue notification emails based on frequency.\n4. Create in-app notifications. |
| **Daily (Cron)**     | Send Digest Emails      | Celery Beat         | `trial_alerts`, `notifications` | For users with `daily` frequency: compile matching trials, send single digest email.                                   |
| **Weekly (Cron)**    | Send Weekly Roundup     | Celery Beat         | Multiple tables                | Compile: new trials, popular posts, upcoming events. Send personalized newsletter.                                      |
| **Daily (Cron)**     | Cleanup Expired Tokens  | Celery Beat         | `password_reset_tokens`        | Delete tokens where `expires_at < NOW() AND used = TRUE`.                                                              |
| **Daily (Cron)**     | Purge Inactive Accounts | Celery Beat         | `users`                        | Soft delete unverified accounts older than 7 days. Email warning before deletion.                                       |
| **On Event Reminders** | Send Event Notifications | Background Task   | `event_registrations`, `events` | Send reminder emails: 1 day before, 1 hour before event start time.                                                    |
| **On Survey Submit** | PII Scrubbing           | Pydantic Validator  | `survey_responses`             | Sanitize input to remove email/phone patterns before database persistence. Log scrubbing actions.                      |
| **On Content Report** | Auto-Moderation Check  | Event Handler       | `content_reports`, `forum_posts` | If `reports_count > 3`: auto-hide content, escalate to admin queue with high priority.                               |

---

## 14. DATA FLOW SUMMARY

### User Registration Flow
```
1. Frontend: User fills registration form
2. POST /auth/register → Backend validates
3. Backend: Hash password (Argon2)
4. Database: INSERT into users table
5. Database: INSERT into user_profiles table
6. Backend: Generate JWT token
7. Email Service: Queue welcome email (background)
8. Response: Return JWT + user object to frontend
9. Frontend: Store token, redirect to dashboard
```

### Trial Search Flow
```
1. Frontend: User enters search criteria
2. GET /trials?disease=HIV&country=Kenya
3. Backend: Build PostgreSQL query with filters
4. Database: Full-text search on clinical_trials (GIN index)
5. Database: JOIN with trial_sites for locations
6. Backend: Rank results by relevance
7. For logged-in users: Check trial_saves for saved status
8. Response: Return trials array + pagination metadata
9. Frontend: Display results with "Save" button state
```

### Forum Post Flow
```
1. Frontend: User writes post
2. POST /community/posts
3. Backend: Validate content (length, format)
4. Backend: Auto-moderation (profanity filter)
5. Database: INSERT into forum_posts
6. Database: Set moderation_status (approved/pending)
7. Database: INSERT into notifications for community subscribers
8. Background: Send notification emails (if enabled)
9. Response: Return created post object
10. Frontend: Display post immediately or "pending moderation"
```

### Password Reset Flow
```
1. Frontend: User enters email
2. POST /auth/request-reset
3. Backend: Check if user exists (silent fail if not)
4. Backend: Generate secure token (secrets.token_urlsafe)
5. Database: INSERT into password_reset_tokens (expires in 1 hour)
6. Database: UPDATE old tokens SET used=TRUE
7. Email Service: Send reset link (background)
8. Response: Generic success message
9. User clicks email link
10. GET /auth/verify-reset-token/{token}
11. Backend validates token
12. Frontend: Show password form if valid
13. POST /auth/reset-password
14. Database: UPDATE users.password_hash
15. Database: UPDATE token SET used=TRUE
16. Response: Success confirmation
```

---

## 15. MVP CONSTRAINTS & BOUNDARIES

### What We DO (MVP Scope)
✅ User authentication and profile management  
✅ Clinical trial search with filters and full-text search  
✅ Trial bookmarking and alerts  
✅ Community forums with moderation  
✅ Events calendar and registration  
✅ Educational resource library  
✅ Basic AI assistant (rule-based navigation)  
✅ Notification system (in-app + email)  
✅ Admin panel for content management  
✅ User feedback and surveys  
✅ HCP verification workflow  
✅ Organizations and working groups  
✅ GDPR compliance (data export, account deletion)  

### What We DON'T DO (Out of MVP Scope)
❌ **Direct Trial Enrollment:** We connect but don't manage enrollment process  
❌ **Electronic Health Records (EHR):** No medical record storage or integration  
❌ **Real-Time Chat:** Forum posts only, no direct messaging (MVP)  
❌ **Payment Processing:** No premium features or transactions (MVP)  
❌ **Live Trial Scraping:** Trials managed via admin CSV uploads  
❌ **Medical Advice:** Platform provides information only, never diagnoses  
❌ **Telemedicine:** We are a connector, not a clinic  
❌ **Advanced AI:** Rule-based assistant in MVP, LLM integration is future phase  
❌ **Multi-Language:** English only in MVP (i18n infrastructure prepared)  
❌ **Mobile Native Apps:** Responsive web app only (MVP)  

### Technical Constraints
1. **Stateless Chat:** No conversation history stored (privacy-first approach)
2. **Manual Trial Ingestion:** Admin CSV uploads, not automated scraping (data quality)
3. **Email Verification:** Optional in MVP (reduces friction), required for HCPs
4. **Soft Deletes:** Important content marked deleted but retained (audit trail)
5. **Anonymous Browsing:** Public access to trials/resources (accessibility)

---

## 16. SECURITY & PRIVACY ACTIONS

| Action Type           | Implementation                                                                                                     | Database Impact                          |
| :-------------------- | :----------------------------------------------------------------------------------------------------------------- | :--------------------------------------- |
| **Password Security** | Argon2 hashing, minimum 8 chars, complexity requirements                                                           | `users.password_hash`                    |
| **Token Security**    | JWT with 24-hour expiration, RS256 signing, refresh tokens (future)                                                | None (stateless)                         |
| **PII Protection**    | Encrypted at rest, access logging, minimal collection                                                              | `users`, `user_profiles`                 |
| **Consent Management**| Explicit consent for data sharing, granular privacy settings                                                       | `users.consent_given`, `user_profiles`   |
| **Content Moderation**| Auto-moderation triggers, human review queue, community reporting                                                  | `content_reports`, `forum_posts`         |
| **Audit Logging**     | All admin actions logged, user activity tracking (anonymous option)                                                | `user_activity_log`                      |
| **Rate Limiting**     | API throttling (100 req/min per IP), auth endpoint stricter (5 req/min)                                            | None (middleware)                        |
| **CORS Policy**       | Whitelist approved frontend domains only                                                                           | None (configuration)                     |
| **Input Validation**  | Pydantic schemas for all endpoints, SQL injection prevention via ORM                                               | All tables                               |
| **HTTPS Only**        | TLS 1.3, HSTS headers, no plaintext transmission                                                                   | None (infrastructure)                    |

---

## 17. ANALYTICS & METRICS

### User Engagement Metrics
- Daily/Monthly Active Users (DAU/MAU)
- Trial searches per user
- Forum posts per user
- Average session duration
- Feature adoption rates

### Platform Health Metrics
- API response times (p95, p99)
- Error rates by endpoint
- Database query performance
- Background job completion rates
- Email delivery rates

### Business Metrics
- New user registrations
- Trial interest expressions
- Resource downloads
- Event registrations
- HCP verification rate

**Logged in:** `user_activity_log` table  
**Aggregated in:** Admin analytics dashboard (`GET /admin/analytics`)

---

## 18. ERROR HANDLING

### Standard HTTP Status Codes
- `200 OK` - Successful GET/PATCH/PUT
- `201 Created` - Successful POST (resource created)
- `204 No Content` - Successful DELETE
- `400 Bad Request` - Invalid input (validation error)
- `401 Unauthorized` - Missing or invalid JWT token
- `403 Forbidden` - Valid token but insufficient permissions
- `404 Not Found` - Resource doesn't exist
- `409 Conflict` - Duplicate resource (e.g., email already exists)
- `422 Unprocessable Entity` - Semantic validation error
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Unhandled server error
- `503 Service Unavailable` - Maintenance mode

### Error Response Format
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Email already exists",
    "details": {
      "field": "email",
      "constraint": "unique"
    }
  }
}
```

---

## Summary: MVP Golden Rules

1️⃣ **Privacy First:** Users control their data. Anonymity is a feature, not a bug.  
2️⃣ **Neutral Platform:** No sponsor bias in trial ranking. Relevance and access only.  
3️⃣ **No Medical Advice:** Information, not diagnosis. Always include disclaimers.  
4️⃣ **Low-Bandwidth Optimized:** Compressed assets, lazy loading, 3G/4G support.  
5️⃣ **Accessibility:** WCAG 2.1 AA compliance, screen reader support, high contrast.  
6️⃣ **Security by Design:** Encryption, authentication, regular security audits.  
7️⃣ **Community Safety:** Active moderation, clear guidelines, reporting tools.  
8️⃣ **MVP Focus:** If it doesn't connect users to trials or educate on advocacy, it's Phase 2.  
