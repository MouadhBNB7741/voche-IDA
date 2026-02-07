# VOCE Platform - Comprehensive API Endpoint Specification

This document details the **Contract** between the Frontend (React application) and the Backend.
All endpoints listed here must be implemented to support the full functionality of the current MVP.

> **Note:**
> *   Base URL: `/api/v1`
> *   Date Format: ISO 8601 (`YYYY-MM-DDTHH:mm:ssZ`)
> *   Pagination: All list endpoints generally support `page` and `limit` query parameters.

---

## 🔐 1. Authentication (`/auth`)
*Endpoints for user registration, login, and session management.*

### Register User
*   **Endpoint:** `POST /auth/register`
*   **Request Body:**
    ```json
    {
      "email": "jane@example.com",
      "password": "SecurePassword123!",
      "name": "Jane Doe",
      "role": "patient", // "patient" | "hcp" | "caregiver" 
      "location": "Nairobi, Kenya" // Optional
    }
    ```
*   **Response (201 Created):**
    ```json
    {
      "token": "eyJhbGciOiJIUz...",
      "user": {
        "id": "uuid-123",
        "email": "jane@example.com",
        "name": "Jane Doe",
        "role": "patient"
      }
    }
    ```

### Login
*   **Endpoint:** `POST /auth/login`
*   **Request Body:**
    ```json
    {
      "email": "jane@example.com",
      "password": "SecurePassword123!"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "token": "eyJhbGciOiJIUz...",
      "user": { /* User Object */ }
    }
    ```

### Forgot Password / Request Password Reset
*   **Endpoint:** `POST /auth/request-reset`
*   **Request Body:** `{"email": "jane@example.com"}`
*   **Response:** `{"message": "If that email exists, a reset link has been sent."}`
*   **Note:** Returns same message for valid/invalid emails (security best practice to prevent email enumeration)

### Verify Reset Token
*   **Endpoint:** `GET /auth/verify-reset-token/{token}`
*   **Purpose:** Check if password reset token is valid before showing password form
*   **Response (200 OK):**
    ```json
    {
      "valid": true
    }
    ```
*   **Response (400 Bad Request):**
    ```json
    {
      "detail": "Invalid reset token" // or "Reset token expired" or "Reset token already used"
    }
    ```

### Reset Password (with Token)
*   **Endpoint:** `POST /auth/reset-password`
*   **Request Body:**
    ```json
    {
      "token": "reset_token_from_email",
      "new_password": "NewSecurePassword123!"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "message": "Password reset successful"
    }
    ```

### Get Current User (Authenticated)
*   **Endpoint:** `GET /auth/me`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response (200 OK):**
    ```json
    {
      "id": "uuid-123",
      "email": "jane@example.com",
      "role": "subscriber", // or "developer"
      "api_key": null, // Only exists for developer role
      "subscription_tier_id": 1
    }
    ```

### Update Password (Authenticated)
*   **Endpoint:** `PUT /auth/update-password`
*   **Headers:** `Authorization: Bearer <token>`
*   **Request Body:**
    ```json
    {
      "current_password": "OldPassword123!",
      "new_password": "NewPassword123!"
    }
    ```
*   **Response (200 OK):**
    ```json
    {
      "message": "Success"
    }
    ```

---

## 👤 2. Users & Profile (`/users`)
*Endpoints for managing user profiles.*

### Get Current User Profile
*   **Endpoint:** `GET /users/me`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response (200 OK):**
    ```json
    {
      "id": "uuid-123",
      "name": "Jane Doe",
      "email": "jane@example.com",
      "role": "patient",
      "avatar": "https://cdn.voce.app/avatars/user123.jpg", // Optimized URL
      "location": "Nairobi, Kenya",
      "bio": "Patient advocate...",
      "interests": ["HIV", "Malaria"],
      "verified": false, // For HCPs
      "notifications_settings": {
        "email_alerts": true,
        "push_alerts": false
      }
    }
    ```

### Update User Profile
*   **Endpoint:** `PATCH /users/me`
*   **Request Body:**
    ```json
    {
      "name": "Jane Doe Updated",
      "location": "Mombasa, Kenya",
      "bio": "New bio...",
      "interests": ["TB", "Malaria"],
      "avatar": "data:image/jpeg;base64,..." // Or URL if upload handled separately
    }
    ```

### Upload Medical License (HCP Only)
*   **Endpoint:** `POST /users/me/verification`
*   **Request Body (Multipart):** `file=<license.pdf>`
*   **Response:** `{"status": "pending_verification"}`

---

## 🔎 3. Clinical Trials (`/trials`)
*Endpoints for searching and interacting with trials.*

### List / Search Trials
*   **Endpoint:** `GET /trials`
*   **Query Params:**
    *   `page`: `1` (default)
    *   `limit`: `10` (default)
    *   `q`: "malaria" (Search keyword)
    *   `disease`: "HIV"
    *   `phase`: "Phase 3"
    *   `location`: "Kenya"
    *   `status`: "recruiting"
*   **Response (200 OK):**
    ```json
    {
      "data": [
        {
          "id": "trial-1",
          "title": "Safety Study of...",
          "summary": "Brief summary...",
          "disease": "Malaria",
          "phase": "Phase 3",
          "status": "Recruiting",
          "location": "Kisumu, Kenya",
          "enrollment": 120,
          "maxEnrollment": 500
        }
      ],
      "meta": {
        "total": 45,
        "page": 1,
        "limit": 10,
        "totalPages": 5
      }
    }
    ```

### Get Trial Details
*   **Endpoint:** `GET /trials/:id`
*   **Response:**
    ```json
    {
      "id": "trial-1",
      "...": "All Standard Fields",
      "eligibility": ["Age > 18", "HIV Negative"],
      "contact": "Dr. Smith (research@lab.org)",
      "sites": ["Hospital A", "Clinic B"]
    }
    ```

### Save/Bookmark Trial
*   **Endpoint:** `POST /trials/:id/save`
*   **Response:** `{"saved": true}`
*   **Endpoint:** `DELETE /trials/:id/save`
*   **Response:** `{"saved": false}`

---

## 💬 4. Community (`/community`)
*Endpoints for forums and discussions.*

### List Forum Posts
*   **Endpoint:** `GET /community/posts`
*   **Query Params:** `page`, `limit`, `category` ("HIV", "General"), `sort` ("recent", "popular", "replies")
*   **Response:**
    ```json
    {
      "data": [
        {
          "id": "post-101",
          "title": "My experience with...",
          "author": "UserABC",
          "author_avatar": "url...",
          "category": "HIV",
          "timestamp": "2024-02-01T10:00:00Z",
          "likes": 15,
          "replies_count": 4,
          "is_liked_by_me": false // Computed for current user
        }
      ],
      "meta": { "total": 120, "page": 1 }
    }
    ```

### Create New Post
*   **Endpoint:** `POST /community/posts`
*   **Request Body:**
    ```json
    {
      "title": "Question about eligibility",
      "content": "Full content...",
      "category": "General",
      "tags": ["help", "question"]
    }
    ```

### Get Single Post & Replies
*   **Endpoint:** `GET /community/posts/:id`
*   **Response:**
    ```json
    {
      "post": { /* Post Object */ },
      "replies": [
        {
          "id": "reply-1",
          "content": "I agree...",
          "author": "Dr. X",
          "timestamp": "2024-02-01T12:00:00Z",
          "likes": 2
        }
      ]
    }
    ```

### Reply to Post
*   **Endpoint:** `POST /community/posts/:id/replies`
*   **Request Body:** `{"content": "This is my reply..."}`

### Like Post/Reply
*   **Endpoint:** `POST /community/posts/:id/like`
*   **Endpoint:** `POST /community/replies/:id/like`

### Delete Post (Author/Admin only)
*   **Endpoint:** `DELETE /community/posts/:id`

### Report Content
*   **Endpoint:** `POST /community/report`
*   **Request Body:**
    ```json
    {
      "target_type": "post", // or "reply"
      "target_id": "post-123",
      "reason": "misinformation"
    }
    ```

---

## �️ 5. Events (`/events`)

*   `GET /events`: List events (filter by `type`, `date`).
*   `GET /events/:id`: Get event details.
*   `POST /events/:id/register`: Register user for event.
*   `DELETE /events/:id/register`: Cancel registration.

---

## 🤖 6. AI Assistant (`/ai`)
*Endpoints for the Assistant Page.*

### Send Chat Message
*   **Endpoint:** `POST /ai/chat`
*   **Request Body:**
    ```json
    {
      "message": "Find trials for Malaria in Kenya",
      "history": [ /* Optional context of last few messages */ ]
    }
    ```
*   **Response:**
    ```json
    {
      "response": "I found 3 trials...",
      "related_actions": [ // Suggestions for UI buttons
        { "label": "View Trials", "link": "/trials?q=malaria" }
      ]
    }
    ```

---

## 🔔 7. Notifications (`/notifications`)

*   `GET /notifications`: Get unread/read notifications.
*   `PATCH /notifications/:id/read`: Mark as read.
*   `DELETE /notifications/:id`: Remove notification.

---

## ⚙️ 8. System & Feedback

### Submit Feedback
*   **Endpoint:** `POST /system/feedback`
*   **Request Body:**
    ```json
    {
      "category": "platform", // "trial", "patient"
      "message": "The search is slow..."
    }
    ```

### Enum/Metadata (Optional but recommended)
*   **Endpoint:** `GET /system/metadata`
*   **Response:** Returns lists of available *Diseases*, *Countries*, *Post Categories* etc., for filling dropdowns dynamically.

---

## 🏢 9. Organizations & Working Groups (`/organizations`)

### List Organizations
*   **Endpoint:** `GET /organizations`
*   **Query Params:** `type` (hospital, research_institution, advocacy_group), `country`
*   **Response (200 OK):**
    ```json
    {
      "data": [
        {
          "id": "org-1",
          "name": "Africa Health Research Institute",
          "type": "research_institution",
          "country": "South Africa",
          "description": "Leading HIV and TB research...",
          "website": "https://ahri.org",
          "membership_status": "partner"
        }
      ]
    }
    ```

### Get Organization Details
*   **Endpoint:** `GET /organizations/:id`
*   **Response:** Full organization profile including contact info, associated trials, members

### Join Organization (Verified Users Only)
*   **Endpoint:** `POST /organizations/:id/join`
*   **Headers:** `Authorization: Bearer <token>`
*   **Response:** `{"status": "pending_approval", "message": "Your request has been sent to the organization admin."}`

### List Working Groups
*   **Endpoint:** `GET /working-groups`
*   **Query Params:** `organization_id`, `type`, `public_only`
*   **Response:** Array of working groups with member counts and descriptions

### Join Working Group
*   **Endpoint:** `POST /working-groups/:id/join`
*   **Response:** Join confirmation or pending approval status

---

## 📊 10. Surveys & Research (`/surveys`)

### List Available Surveys
*   **Endpoint:** `GET /surveys`
*   **Query Params:** `status` (active, completed), `eligibility` (filter by user profile)
*   **Response (200 OK):**
    ```json
    {
      "data": [
        {
          "id": "survey-1",
          "title": "Patient Experience with Clinical Trial Information",
          "description": "Help us improve how we present trial data",
          "estimated_time": "10 minutes",
          "incentive": null,
          "status": "active",
          "already_completed": false
        }
      ]
    }
    ```

### Get Survey Questions
*   **Endpoint:** `GET /surveys/:id`
*   **Response (200 OK):**
    ```json
    {
      "id": "survey-1",
      "title": "...",
      "consent_text": "Your responses will be anonymous...",
      "questions": [
        {
          "id": "q1",
          "text": "How often do you search for clinical trials?",
          "type": "multiple_choice",
          "required": true,
          "options": ["Daily", "Weekly", "Monthly", "Rarely"]
        },
        {
          "id": "q2",
          "text": "What barriers do you face?",
          "type": "open_text",
          "required": false
        }
      ]
    }
    ```

### Submit Survey Response
*   **Endpoint:** `POST /surveys/:id/responses`
*   **Request Body:**
    ```json
    {
      "consent_given": true,
      "anonymous": true,
      "responses": [
        { "question_id": "q1", "answer": "Weekly" },
        { "question_id": "q2", "answer": "Limited information about eligibility criteria" }
      ]
    }
    ```
*   **Response:** `{"message": "Thank you for your feedback!", "completion_id": "resp-123"}`

---

## 🔧 11. User Preferences & Settings (`/users/me`)

### Get Notification Preferences
*   **Endpoint:** `GET /users/me/preferences/notifications`
*   **Response (200 OK):**
    ```json
    {
      "email_alerts": true,
      "push_notifications": false,
      "notification_types": {
        "trial_matches": true,
        "community_replies": true,
        "event_reminders": true,
        "system_updates": false
      },
      "frequency": "immediate" // or "daily_digest", "weekly"
    }
    ```

### Update Notification Preferences
*   **Endpoint:** `PATCH /users/me/preferences/notifications`
*   **Request Body:** (same structure as above)
*   **Response:** Updated preferences object

### Get Privacy Settings
*   **Endpoint:** `GET /users/me/preferences/privacy`
*   **Response:**
    ```json
    {
      "profile_visibility": "public", // "public", "community_only", "private"
      "show_saved_trials": false,
      "show_activity": true,
      "allow_messages": true
    }
    ```

### Update Privacy Settings
*   **Endpoint:** `PATCH /users/me/preferences/privacy`
*   **Request Body:** Updated privacy settings
*   **Response:** Confirmation

### Request Data Export (GDPR)
*   **Endpoint:** `POST /users/me/data-export`
*   **Response:** `{"message": "Your data export will be emailed within 24 hours", "request_id": "export-123"}`

### Delete Account
*   **Endpoint:** `DELETE /users/me`
*   **Request Body:** `{"password": "confirm_password", "reason": "Optional feedback"}`
*   **Response:** `{"message": "Account deletion scheduled. You have 30 days to cancel."}`

---

## 🔐 12. Trial Alerts & Subscriptions (`/alerts`)

### Create Trial Alert
*   **Endpoint:** `POST /alerts/trials`
*   **Request Body:**
    ```json
    {
      "disease_area": "HIV",
      "location": "Kenya",
      "phase": "Phase 3",
      "frequency": "weekly"
    }
    ```
*   **Response:** `{"alert_id": "alert-123", "message": "You'll be notified of matching trials weekly"}`

### List My Alerts
*   **Endpoint:** `GET /alerts/trials`
*   **Response:** Array of active trial alerts with criteria and frequency

### Update Alert
*   **Endpoint:** `PATCH /alerts/trials/:id`
*   **Request Body:** Updated criteria or frequency
*   **Response:** Updated alert object

### Delete Alert
*   **Endpoint:** `DELETE /alerts/trials/:id`
*   **Response:** Confirmation

### Pause/Resume Alert
*   **Endpoint:** `PATCH /alerts/trials/:id/toggle`
*   **Response:** `{"is_active": false}` or `{"is_active": true}`

---

## 👨‍⚕️ 13. HCP-Specific Endpoints (`/hcp`)

### Submit Verification Documents
*   **Endpoint:** `POST /hcp/verification`
*   **Request Body (Multipart):**
    ```
    file: <medical_license.pdf>
    license_number: "MD-12345"
    issuing_country: "Kenya"
    specialization: "Oncology"
    expiration_date: "2028-12-31"
    ```
*   **Response:** `{"status": "pending_verification", "expected_review_time": "3-5 business days"}`

### Check Verification Status
*   **Endpoint:** `GET /hcp/verification/status`
*   **Response:**
    ```json
    {
      "status": "pending", // "pending", "approved", "rejected", "expired"
      "submitted_date": "2024-02-01",
      "reviewed_by": null,
      "notes": null
    }
    ```

### Access HCP Resources
*   **Endpoint:** `GET /hcp/resources`
*   **Authorization:** Requires verified HCP status
*   **Response:** Array of HCP-only educational materials (trial recruitment guides, patient consent templates)

---

## 🛡️ 14. Admin & Moderation (`/admin`)

**Note:** All endpoints in this section require `admin` or `moderator` role

### Get Moderation Queue
*   **Endpoint:** `GET /admin/moderation/queue`
*   **Query Params:** `type` (post, comment, user), `status` (pending, reviewed)
*   **Response (200 OK):**
    ```json
    {
      "data": [
        {
          "report_id": "rep-1",
          "target_type": "post",
          "target_id": "post-123",
          "target_content": "...",
          "reporter_id": "user-456",
          "reason": "misinformation",
          "description": "This post claims trials are scams",
          "created_at": "2024-02-05T10:00:00Z",
          "status": "pending",
          "reports_count": 3
        }
      ]
    }
    ```

### Resolve Report
*   **Endpoint:** `POST /admin/moderation/:report_id/resolve`
*   **Request Body:**
    ```json
    {
      "action": "remove_content", // "approve", "remove_content", "warn_user", "ban_user"
      "notes": "Violated community guidelines on medical misinformation",
      "notify_user": true
    }
    ```
*   **Response:** `{"message": "Report resolved", "action_taken": "remove_content"}`

### Get User Details (Admin)
*   **Endpoint:** `GET /admin/users/:id`
*   **Response:** Complete user profile including activity history, reports, verification documents

### Verify HCP Account
*   **Endpoint:** `POST /admin/users/:id/verify-hcp`
*   **Request Body:**
    ```json
    {
      "approved": true,
      "notes": "License verified with issuing authority"
    }
    ```
*   **Response:** `{"message": "User verified as HCP", "user_notified": true}`

### Suspend/Ban User
*   **Endpoint:** `POST /admin/users/:id/suspend`
*   **Request Body:**
    ```json
    {
      "duration_days": 7, // or null for permanent ban
      "reason": "Repeated violations of community guidelines"
    }
    ```
*   **Response:** Confirmation

### Create/Update Trial (Manual Entry)
*   **Endpoint:** `POST /admin/trials`
*   **Endpoint:** `PATCH /admin/trials/:id`
*   **Request Body:** Full trial object
*   **Purpose:** Allows admins to manually add trials not in automated feeds

### Bulk Import Trials
*   **Endpoint:** `POST /admin/trials/import`
*   **Request Body (Multipart):** CSV or JSON file with trial data
*   **Response:** `{"imported": 45, "failed": 2, "errors": [...]}`

### Feature Content
*   **Endpoint:** `POST /admin/content/feature`
*   **Request Body:**
    ```json
    {
      "content_type": "resource", // "resource", "post", "event"
      "content_id": "res-123",
      "featured": true,
      "featured_until": "2024-03-01"
    }
    ```
*   **Response:** Confirmation

### Platform Analytics
*   **Endpoint:** `GET /admin/analytics`
*   **Query Params:** `metric` (users, trials, engagement), `period` (day, week, month)
*   **Response:**
    ```json
    {
      "total_users": 1250,
      "active_users_30d": 450,
      "trials_searched": 8920,
      "top_diseases": ["HIV", "Malaria", "TB"],
      "top_countries": ["Kenya", "South Africa", "Nigeria"]
    }
    ```

---

## 🔍 15. Search & Discovery (`/search`)

### Global Search
*   **Endpoint:** `GET /search`
*   **Query Params:** `q` (query), `type` (all, trials, resources, posts, events)
*   **Response (200 OK):**
    ```json
    {
      "trials": [...],
      "resources": [...],
      "posts": [...],
      "events": [...],
      "total_results": 47
    }
    ```

### Autocomplete/Suggestions
*   **Endpoint:** `GET /search/suggestions`
*   **Query Params:** `q` (partial query)
*   **Response:** Array of suggested search terms

---

## 💾 16. Health & System (`/system`)

### Health Check
*   **Endpoint:** `GET /health`
*   **Response:**
    ```json
    {
      "status": "healthy",
      "version": "1.0.0",
      "database": "connected",
      "timestamp": "2024-02-07T16:42:00Z"
    }
    ```

### System Status
*   **Endpoint:** `GET /system/status`
*   **Response:**
    ```json
    {
      "api_version": "v1",
      "maintenance_mode": false,
      "features": {
        "ai_assistant": true,
        "forums": true,
        "events": true
      }
    }
    ```

---

## 📝 Summary of All Endpoints

### Authentication (`/auth`)
- `POST /auth/register` - Create account
- `POST /auth/login` - Login
- `POST /auth/request-reset` - Password reset request
- `GET /auth/verify-reset-token/{token}` - Validate reset token
- `POST /auth/reset-password` - Complete password reset
- `GET /auth/me` - Get current user
- `PUT /auth/update-password` - Change password

### Users & Profile (`/users`)
- `GET /users/me` - Get profile
- `PATCH /users/me` - Update profile
- `POST /users/me/verification` - HCP verification upload
- `GET /users/me/saved-trials` - Saved trials
- `GET /users/me/events` - Registered events
- `GET /users/me/preferences/*` - Settings
- `PATCH /users/me/preferences/*` - Update settings
- `POST /users/me/data-export` - GDPR export
- `DELETE /users/me` - Delete account

### Trials (`/trials`)
- `GET /trials` - Search trials
- `GET /trials/:id` - Trial details
- `POST /trials/:id/save` - Save trial
- `DELETE /trials/:id/save` - Unsave trial
- `POST /trials/:id/interest` - Express interest

### Community (`/community`)
- `GET /community/posts` - List posts
- `GET /community/posts/:id` - Post details
- `POST /community/posts` - Create post
- `POST /community/posts/:id/replies` - Reply
- `POST /community/posts/:id/like` - Like
- `PATCH /community/posts/:id` - Edit post
- `DELETE /community/posts/:id` - Delete post
- `POST /community/report` - Report content

### Events (`/events`)
- `GET /events` - List events
- `GET /events/:id` - Event details
- `POST /events/:id/register` - Register
- `DELETE /events/:id/register` - Cancel registration

### Resources (`/resources`)
- `GET /resources` - List resources
- `GET /resources/:id` - Resource details
- `GET /resources/:id/download` - Download
- `POST /resources/:id/rating` - Rate resource
- `PATCH /resources/:id/progress` - Track progress

### AI Assistant (`/ai`)
- `POST /ai/chat` - Chat message
- `GET /ai/suggestions` - Get prompts

### Notifications (`/notifications`)
- `GET /notifications` - List notifications
- `PATCH /notifications/:id/read` - Mark read
- `PATCH /notifications/mark-all-read` - Mark all read
- `DELETE /notifications/:id` - Delete

### Organizations (`/organizations`)
- `GET /organizations` - List organizations
- `GET /organizations/:id` - Organization details
- `POST /organizations/:id/join` - Join organization

### Working Groups (`/working-groups`)
- `GET /working-groups` - List groups
- `POST /working-groups/:id/join` - Join group

### Surveys (`/surveys`)
- `GET /surveys` - Available surveys
- `GET /surveys/:id` - Survey questions
- `POST /surveys/:id/responses` - Submit response

### Alerts (`/alerts`)
- `POST /alerts/trials` - Create alert
- `GET /alerts/trials` - List alerts
- `PATCH /alerts/trials/:id` - Update alert
- `DELETE /alerts/trials/:id` - Delete alert
- `PATCH /alerts/trials/:id/toggle` - Pause/resume

### HCP (`/hcp`)
- `POST /hcp/verification` - Submit credentials
- `GET /hcp/verification/status` - Check status
- `GET /hcp/resources` - HCP resources

### Admin (`/admin`)
- `GET /admin/moderation/queue` - Moderation queue
- `POST /admin/moderation/:id/resolve` - Resolve report
- `GET /admin/users/:id` - User details
- `POST /admin/users/:id/verify-hcp` - Verify HCP
- `POST /admin/users/:id/suspend` - Suspend user
- `POST /admin/trials` - Create trial
- `POST /admin/trials/import` - Bulk import
- `POST /admin/content/feature` - Feature content
- `GET /admin/analytics` - Platform analytics

### Search (`/search`)
- `GET /search` - Global search
- `GET /search/suggestions` - Autocomplete

### System (`/system`)
- `GET /system/metadata` - Enums/dropdowns
- `POST /system/feedback` - Submit feedback
- `GET /health` - Health check
- `GET /system/status` - System status

---

**Total Endpoints:** 70+  
**Authentication Required:** ~80% of endpoints  
**Admin Only:** ~15% of endpoints  
**Public Access:** ~20% of endpoints