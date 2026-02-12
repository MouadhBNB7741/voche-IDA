# 🏗️ VOCE Platform | Backend System Conception

> **Document Purpose:** This document serves as the comprehensive backend blueprint for the VOCE Platform MVP. It defines the system's structure, communication contracts, and data organization in clear, non-technical language to align Product, Frontend, and Backend teams.

---

## Executive Summary

The VOCE backend serves as the **secure, scalable foundation** that powers the platform's three core missions:

1. **Discovery** - Connecting users with relevant clinical trials
2. **Education** - Providing verified health resources and information
3. **Community** - Facilitating safe peer support and professional networking

The backend is built using **Python with FastAPI**, backed by **PostgreSQL**, following industry-standard security practices (HIPAA/GDPR-compliant) and modern API design principles (RESTful architecture).

---

## 1. Backend Folder Structure

The backend follows a **modular architecture** that separates concerns and enables independent development and testing of each system component.

```
backend/
├─ app/
│  ├─ api/              → API Endpoints & Routes
│  ├─ core/             → Security, Configuration & Utilities
│  ├─ db/               → Database Connection & Migrations
│  ├─ schemas/          → Data Validation & Input/Output Models
│  ├─ services/         → Business Logic & External Integrations
│  ├─ tests/            → Automated Quality Assurance
│  ├─ main.py           → Application Entry Point
│  └─ __init__.py       → Package Initialization
├─ requirements.txt     → Dependency List
└─ .env                 → Environment Configuration (Secret)
```

### Folder Responsibilities

#### **`api/`** - The Gateway

- **What it does:** Defines all the "doors" (endpoints) through which the frontend communicates with the backend
- **Analogy:** Like a receptionist desk—receives requests, validates them, and routes to the appropriate department
- **Examples:** Registration endpoint, trial search endpoint, profile update endpoint
- **Contains:** Route definitions organized by feature (auth, trials, community, etc.)

#### **`schemas/`** - The Contract Enforcer

- **What it does:** Defines exactly what data format is expected for each request and response
- **Analogy:** Like a customs inspector—ensures every incoming package matches its declared contents
- **Examples:** "Registration must include email, password, name, and role", "Trial response includes id, title, phase, status"
- **Purpose:** Prevents invalid data from entering the system and ensures consistent responses

#### **`services/`** - The Brain

- **What it does:** Contains all the business logic—the "how" behind operations
- **Analogy:** Like department specialists—when reception receives a request, services figure out the actual work
- **Examples:**
  - Matching algorithm that finds trials relevant to a user's profile
  - Email service that sends password reset links
  - Content moderation logic that filters inappropriate forum posts
- **Purpose:** Keeps complex logic separate from API routes for maintainability

#### **`core/`** - The Foundation

- **What it does:** Handles system-wide concerns like security, authentication, and configuration
- **Examples:**
  - Password hashing and verification
  - JWT token generation and validation
  - Application settings and environment variables
  - Logging and error handling
- **Purpose:** Centralize critical security and configuration logic

#### **`db/`** - The Data Layer

- **What it does:** Manages all database interactions and schema migrations
- **Analogy:** Like a filing system manager—handles storing, retrieving, and organizing all persistent data
- **Contains:**
  - Database connection pooling
  - Migration scripts (for updating database structure)
  - Database utility functions
- **Purpose:** Creates a clean separation between business logic and data storage

#### **`tests/`** - The Quality Guardian

- **What it does:** Automated tests that verify every component works correctly
- **Types:**
  - Unit tests (individual function verification)
  - Integration tests (multi-component workflows)
  - API contract tests (ensures endpoints match documentation)
- **Purpose:** Catch bugs before they reach production, enable confident updates

#### **`main.py`** - The Orchestrator

- **What it does:** The application's starting point—assembles all components
- **Responsibilities:**
  - Initializes the FastAPI application
  - Registers all API routes
  - Configures middleware (CORS, rate limiting, logging)
  - Sets up database connections
  - Defines startup and shutdown procedures

---

## 2. API Contract (High-Level)

The API contract defines **how the frontend and backend communicate**. For each feature, we specify:

- **What can be requested** (endpoint + HTTP method)
- **What information must be provided** (input)
- **What information is returned** (output)

This section is organized by feature domain, following RESTful conventions.

---

### 🔐 **Authentication & Authorization** (`/api/v1/auth`)

**Purpose:** Establishes user identity, protects accounts, and manages sessions.

#### **User Registration**

- **What it does:** Creates a new user account in the system
- **Method:** `POST /auth/register`
- **Input Required:**
  - Email address
  - Password (minimum 8 characters, complexity requirements)
  - Full name
  - User role (patient, healthcare professional, caregiver, organization member)
  - Location (optional, for trial matching)
  - Condition/specialization (optional, for personalization)
- **What happens:**
  1. System checks if email already exists
  2. Password is securely hashed (never stored in plain text)
  3. User profile is created
  4. For healthcare professionals: verification flag set to "pending"
  5. For developers (future): API key is generated
  6. Confirmation email is sent (future)
- **Output:** Authentication token (JWT) + user profile object

#### **User Login**

- **What it does:** Authenticates existing user and creates session
- **Method:** `POST /auth/login`
- **Input Required:**
  - Email address
  - Password
- **What happens:**
  1. System verifies email exists
  2. Password is validated against stored hash
  3. Session token (JWT) is generated with 24-hour expiration
  4. Last login timestamp is updated
- **Output:** Authentication token + user profile object
- **Error cases:** Invalid credentials return generic error (security best practice)

#### **Password Reset Request**

- **What it does:** Initiates password recovery process
- **Method:** `POST /auth/request-reset`
- **Input Required:** Email address
- **What happens:**
  1. System generates secure, time-limited reset token (1-hour expiration)
  2. Token is stored in database
  3. Email sent with reset link (contains token)
  4. Previous unused tokens for this user are invalidated
- **Output:** Generic success message (prevents email enumeration attacks)

#### **Password Reset Confirmation**

- **What it does:** Completes password reset using emailed token
- **Method:** `POST /auth/reset-password`
- **Input Required:**
  - Reset token (from email link)
  - New password
- **What happens:**
  1. Token is validated (exists, not expired, not used)
  2. New password is hashed
  3. User password is updated
  4. All active sessions are invalidated
  5. Token is marked as used
- **Output:** Success confirmation

#### **Get Current User Profile**

- **What it does:** Retrieves authenticated user's complete profile
- **Method:** `GET /auth/me`
- **Input Required:** Valid JWT token in Authorization header
- **Output:** Complete user profile including preferences, saved items, verification status

#### **Update Password (Authenticated)**

- **What it does:** Allows logged-in user to change password
- **Method:** `PUT /auth/update-password`
- **Input Required:**
  - Current password (for verification)
  - New password
  - Valid JWT token
- **What happens:**
  1. Current password is verified
  2. New password is hashed and saved
  3. Optional: logout all other sessions
- **Output:** Success confirmation

#### **Token Verification**

- **What it does:** Validates reset token before allowing password change
- **Method:** `GET /auth/verify-reset-token/{token}`
- **Purpose:** Prevents user from filling out password form with invalid/expired token
- **Output:** Valid status + expiration time OR error

---

### 👤 **User Profile Management** (`/api/v1/users`)

**Purpose:** Manages user information, preferences, and personalization data.

#### **Get User Profile**

- **What it does:** Retrieves full profile for authenticated user
- **Method:** `GET /users/me`
- **Output Includes:**
  - Personal information (name, email, location)
  - Role and verification status
  - Bio and interests
  - Profile completion percentage
  - Notification preferences
  - Account settings (language, timezone)
  - Privacy consent records

#### **Update User Profile**

- **What it does:** Modifies user information
- **Method:** `PATCH /users/me`
- **Updatable Fields:**
  - Display name
  - Bio/description
  - Location
  - Language preference
  - Disease/condition interests (for patients)
  - Specialization (for HCPs)
  - Organization affiliation
  - Avatar/profile image
- **What happens:**
  1. Input is validated
  2. Changes are saved to database
  3. Profile completion percentage recalculated
  4. Updated profile returned

#### **Upload Verification Documents (HCP Only)**

- **What it does:** Allows healthcare professionals to submit medical license for verification
- **Method:** `POST /users/me/verification`
- **Input Required:**
  - Medical license document (PDF/JPG)
  - License number
  - Issuing country/state
  - Expiration date
- **What happens:**
  1. Document is securely stored
  2. Admin notification is created for review
  3. User status set to "pending_verification"
- **Output:** Upload confirmation + expected review timeframe

#### **Manage Notification Preferences**

- **What it does:** Controls what notifications user receives
- **Method:** `PATCH /users/me/notifications`
- **Configurable Settings:**
  - Email alerts (on/off)
  - Push notifications (on/off)
  - Notification types (trial matches, community replies, events, system)
  - Frequency (instant, daily digest, weekly)
- **Output:** Updated preferences

---

### 🔬 **Clinical Trials** (`/api/v1/trials`)

**Purpose:** Enables discovery, filtering, and interaction with clinical trial listings.

#### **Search & List Trials**

- **What it does:** Returns trials matching search criteria
- **Method:** `GET /trials`
- **Search Filters:**
  - **Text search:** Keyword in title/description
  - **Disease area:** HIV, Malaria, TB, Cancer, etc.
  - **Phase:** Phase 1, 2, 3, 4
  - **Status:** Recruiting, Active, Completed, Not Yet Recruiting
  - **Location:** Country or city
  - **Sponsor:** Pharmaceutical company or institution
- **Pagination:** `page` and `limit` parameters
- **Sorting:** Relevance (default), newest, enrollment status
- **What happens:**
  1. Query is constructed with filters
  2. Full-text search executed against PostgreSQL
  3. Results ranked by relevance and availability
  4. For authenticated users: check if each trial is saved
- **Output:**
  - Array of trial summaries (id, title, phase, status, location, enrollment)
  - Total count
  - Pagination metadata

#### **Get Trial Details**

- **What it does:** Returns complete information for specific trial
- **Method:** `GET /trials/{trial_id}`
- **Output Includes:**
  - Full description and objectives
  - Detailed eligibility criteria
  - Study phase and status
  - Enrollment numbers (current/target)
  - Trial sites and contact information
  - Start date and estimated completion
  - Sponsor information
  - Related resources (protocols, consent forms)
  - Safety information

#### **Save/Bookmark Trial**

- **What it does:** Adds trial to user's saved list for later reference
- **Method:** `POST /trials/{trial_id}/save`
- **Requires:** Authentication
- **What happens:**
  1. Relationship created in `trial_saves` table
  2. Notification may be triggered for trial updates
- **Output:** Confirmation + updated save status

#### **Remove Saved Trial**

- **What it does:** Removes trial from user's saved list
- **Method:** `DELETE /trials/{trial_id}/save`
- **Output:** Confirmation

#### **Get User's Saved Trials**

- **What it does:** Retrieves all trials bookmarked by user
- **Method:** `GET /users/me/saved-trials`
- **Output:** Array of full trial objects + save timestamp

#### **Express Interest / Contact Trial**

- **What it does:** Captures user intent to participate
- **Method:** `POST /trials/{trial_id}/interest`
- **Purpose:** Connects patient with trial coordinator
- **What happens:**
  1. User contact info + basic profile shared with trial sponsor
  2. Email sent to trial coordinator
  3. Confirmation email sent to user
  4. Lead logged for analytics
- **Privacy:** User explicitly consents before contact info is shared

#### **Create Trial Alert**

- **What it does:** Notifies user when trials matching criteria are added
- **Method:** `POST /alerts/trials`
- **Input Required:**
  - Disease area
  - Location preference
  - Alert frequency (instant, weekly)
- **Output:** Alert subscription confirmation

---

### 💬 **Community & Forums** (`/api/v1/community`)

**Purpose:** Facilitates peer support through discussion forums while maintaining safety and privacy.

#### **List Forum Posts**

- **What it does:** Retrieves community discussions
- **Method:** `GET /community/posts`
- **Filters:**
  - Community/category (HIV Support, Malaria Research, General)
  - Post type (question, story, discussion, announcement)
  - Moderation status (for admins)
  - Time period (last week, month, all time)
- **Sorting:** Recent, popular (likes), most replied, trending
- **What happens:**
  1. Posts filtered by category and status
  2. For each post, calculate engagement metrics
  3. For authenticated users: check if user has liked
- **Output:**
  - Array of post summaries (title, author, timestamp, likes, replies count, excerpt)
  - Pagination metadata

#### **Get Post Details & Replies**

- **What it does:** Retrieves full post content and all comments/replies
- **Method:** `GET /community/posts/{post_id}`
- **Output:**
  - Complete post content
  - Author info (username, role, avatar)
  - Timestamp and edit history
  - Engagement metrics
  - Array of replies/comments (threaded if applicable)
  - User's like status
- **Privacy:** Author's email never exposed, only display name

#### **Create New Post**

- **What it does:** Publishes new discussion thread
- **Method:** `POST /community/posts`
- **Input Required:**
  - Title
  - Content (text, supports markdown)
  - Community/category selection
  - Tags (optional, for organization)
- **What happens:**
  1. Content validated (length, format)
  2. Automatic content moderation (profanity filter, spam detection)
  3. Post created with "approved" or "pending" status
  4. Community members may be notified based on preferences
- **Output:** Created post object with ID

#### **Reply to Post**

- **What it does:** Adds comment to existing discussion
- **Method:** `POST /community/posts/{post_id}/replies`
- **Input Required:** Reply content
- **What happens:**
  1. Reply is created and linked to parent post
  2. Post author is notified (if enabled in preferences)
  3. Reply counter on parent post is incremented

#### **Like/Unlike Post or Reply**

- **What it does:** Expresses support or agreement
- **Method:** `POST /community/posts/{post_id}/like`
- **Method:** `DELETE /community/posts/{post_id}/like`
- **What happens:**
  1. Like relationship created/removed
  2. Like counter updated
  3. No notification (reduces noise)

#### **Edit Post**

- **What it does:** Allows author to modify their content
- **Method:** `PATCH /community/posts/{post_id}`
- **Authorization:** Only post author or admin
- **What happens:**
  1. Original content stored in edit history
  2. Updated content saved
  3. "Edited" flag and timestamp added

#### **Delete Post**

- **What it does:** Removes post from community
- **Method:** `DELETE /community/posts/{post_id}`
- **Authorization:** Post author, moderators, or admins
- **What happens:**
  1. Soft delete (marked as deleted, but retained for audit)
  2. Content no longer displayed
  3. All replies also hidden

#### **Report Content**

- **What it does:** Flags inappropriate or harmful content
- **Method:** `POST /community/reports`
- **Input Required:**
  - Target type (post or reply)
  - Target ID
  - Reason (misinformation, harassment, spam, medical advice)
  - Optional description
- **What happens:**
  1. Report created and queue for moderator review
  2. Content auto-hidden if multiple reports received
  3. No notification to reported user (prevents gaming)
- **Output:** Confirmation that report was received

---

### 📚 **Resources & Education** (`/api/v1/resources`)

**Purpose:** Provides access to vetted educational materials and advocacy toolkits.

#### **List Resources**

- **What it does:** Returns educational materials catalog
- **Method:** `GET /resources`
- **Filters:**
  - Type (video, document, toolkit, course)
  - Category/topic (clinical trials 101, patient rights, disease-specific)
  - Language
  - Featured/recommended
- **Sorting:** Most popular, newest, highest rated
- **Output:**
  - Array of resource summaries (title, type, description, duration/pages, rating)
  - Download/view counts

#### **Get Resource Details**

- **What it does:** Retrieves full information about educational material
- **Method:** `GET /resources/{resource_id}`
- **Output:**
  - Complete description
  - Access URL or download link
  - Author/organization
  - Publication date
  - Prerequisites (if course)
  - Related resources
  - User ratings and reviews

#### **Download/Access Resource**

- **What it does:** Provides access to resource file
- **Method:** `GET /resources/{resource_id}/download`
- **What happens:**
  1. Access permissions verified (some resources require login)
  2. Download counter incremented
  3. Analytics event logged
  4. Secure, temporary download URL generated
- **Output:** File download or streaming URL

#### **Rate Resource**

- **What it does:** Allows users to provide feedback on quality
- **Method:** `POST /resources/{resource_id}/rating`
- **Input:** Star rating (1-5) + optional text review
- **Output:** Updated average rating

#### **Track Resource Progress** (for courses/multi-part content)

- **What it does:** Saves user progress through educational materials
- **Method:** `PATCH /resources/{resource_id}/progress`
- **Input:** Completion percentage or module ID
- **Output:** Updated progress status

---

### 📅 **Events & Webinars** (`/api/v1/events`)

**Purpose:** Manages educational events, webinars, and community gatherings.

#### **List Events**

- **What it does:** Returns upcoming and past events
- **Method:** `GET /events`
- **Filters:**
  - Type (webinar, conference, training, roundtable)
  - Date range
  - Location (virtual vs. physical)
  - Organizing body
- **Sorting:** Upcoming first, by relevance
- **Output:**
  - Event summaries (title, date/time, type, organizer, participant count)
  - Registration status for authenticated users

#### **Get Event Details**

- **What it does:** Retrieves complete event information
- **Method:** `GET /events/{event_id}`
- **Output:**
  - Full description and agenda
  - Date, time, timezone
  - Virtual access link (if applicable)
  - Physical location details
  - Speaker/facilitator information
  - Prerequisites or preparation materials
  - Registration deadline
  - Current registration count

#### **Register for Event**

- **What it does:** Signs user up for participation
- **Method:** `POST /events/{event_id}/register`
- **What happens:**
  1. Availability checked (capacity limits)
  2. Registration recorded
  3. Confirmation email sent with details
  4. Calendar invite generated (ICS file)
  5. Reminder notifications scheduled
- **Output:** Registration confirmation + access details

#### **Cancel Event Registration**

- **What it does:** Removes user from event attendee list
- **Method:** `DELETE /events/{event_id}/register`
- **Output:** Cancellation confirmation

#### **Get User's Registered Events**

- **What it does:** Retrieves all events user is attending
- **Method:** `GET /users/me/events`
- **Output:** Array of events with access links

---

### 🤖 **AI Assistant** (`/api/v1/ai`)

**Purpose:** Provides intelligent navigation assistance and answers common questions.

#### **Send Chat Message**

- **What it does:** Processes user query and returns helpful guidance
- **Method:** `POST /ai/chat`
- **Input Required:**
  - User message/question
  - Conversation history (optional, for context)
- **What happens:**
  1. Message analyzed to determine intent (trial search, general info, navigation)
  2. For MVP: rule-based decision tree routes to appropriate resources
  3. For future: LLM processes natural language
  4. Response generated with actionable suggestions
- **Output:**
  - Assistant text response
  - Suggested actions (buttons/links to trials, resources, community)
  - Related FAQs
- **Important:** Always includes disclaimer that assistant doesn't provide medical advice

#### **Get Suggested Questions**

- **What it does:** Provides conversation starters
- **Method:** `GET /ai/suggestions`
- **Output:** Array of common questions contextual to user's profile

---

### 🔔 **Notifications** (`/api/v1/notifications`)

**Purpose:** Manages user alerts and system messages.

#### **Get Notifications**

- **What it does:** Retrieves user's notification inbox
- **Method:** `GET /notifications`
- **Filters:** Read/unread, type, date range
- **Output:**
  - Array of notifications (title, message, type, timestamp, read status, action link)
  - Unread count

#### **Mark as Read**

- **What it does:** Updates notification status
- **Method:** `PATCH /notifications/{notification_id}/read`
- **Also supports:** `PATCH /notifications/mark-all-read`

#### **Delete Notification**

- **What it does:** Removes notification from user's inbox
- **Method:** `DELETE /notifications/{notification_id}`

#### **Get Notification Preferences**

- **What it does:** Retrieves current notification settings
- **Method:** `GET /notifications/preferences`
- **Output:** Configuration for each notification type and channel

---

### 🏢 **Organizations & Working Groups** (`/api/v1/organizations`)

**Purpose:** Manages institutional partnerships and collaborative groups.

#### **List Organizations**

- **What it does:** Returns directory of partner organizations
- **Method:** `GET /organizations`
- **Filters:** Type (research institution, advocacy group, hospital network), country
- **Output:** Organization profiles (name, type, description, country, website)

#### **Get Organization Details**

- **What it does:** Retrieves complete organization profile
- **Method:** `GET /organizations/{org_id}`
- **Output:**
  - Full description
  - Contact information
  - Associated trials
  - Member list (if public)
  - Resources contributed

#### **Join Organization** (for verified HCPs/members)

- **What it does:** Requests membership in organization's VOCE group
- **Method:** `POST /organizations/{org_id}/join`
- **What happens:**
  1. Membership request created
  2. Organization admin notified
  3. Pending status set
- **Output:** Request confirmation

---

### 📊 **Surveys & Feedback** (`/api/v1/surveys`)

**Purpose:** Collects user feedback and research data with consent.

#### **List Available Surveys**

- **What it does:** Returns surveys user is eligible to complete
- **Method:** `GET /surveys`
- **Filters:** Status (active, completed), relevance to user profile
- **Output:** Survey metadata (title, description, estimated time, incentive if applicable)

#### **Get Survey Questions**

- **What it does:** Retrieves full survey instrument
- **Method:** `GET /surveys/{survey_id}`
- **Output:** Ordered array of questions with response types

#### **Submit Survey Response**

- **What it does:** Records user's survey answers
- **Method:** `POST /surveys/{survey_id}/responses`
- **Input:** Array of question-answer pairs
- **What happens:**
  1. Consent verification
  2. Responses validated
  3. Data stored with anonymization options applied
  4. Completion recorded
- **Output:** Thank you confirmation + incentive if applicable

---

### ⚙️ **System & Administration** (`/api/v1/admin`, `/api/v1/system`)

**Purpose:** Platform management, content moderation, and system monitoring.

#### **Submit Feedback**

- **What it does:** Allows users to report bugs or suggest features
- **Method:** `POST /system/feedback`
- **Input:**
  - Category (bug, feature request, content issue)
  - Description
  - Optional screenshot/attachments
- **Output:** Ticket number for tracking

#### **Get System Metadata**

- **What it does:** Provides structured data for dropdowns and filters
- **Method:** `GET /system/metadata`
- **Output:**
  - List of supported countries
  - Disease areas
  - Languages
  - Trial phases
  - Community categories
  - User roles
- **Purpose:** Ensures frontend and backend always aligned on valid values

#### **Health Check**

- **What it does:** Verifies API is operational
- **Method:** `GET /health`
- **Output:** Service status, version, database connectivity

#### **Admin: Content Moderation Queue** (Restricted)

- **What it does:** Shows flagged content requiring review
- **Method:** `GET /admin/moderation/queue`
- **Authorization:** Admin or moderator role only
- **Output:** Pending reports with context

#### **Admin: Approve/Reject Content**

- **Method:** `POST /admin/moderation/{report_id}/resolve`
- **Input:** Decision (approve, remove, warn user)
- **What happens:** Content status updated, user may be notified

#### **Admin: Verify HCP**

- **What it does:** Approves healthcare professional verification
- **Method:** `POST /admin/users/{user_id}/verify`
- **Input:** Verification decision + notes
- **What happens:**
  1. User status updated to "verified"
  2. Verification badge enabled
  3. User notified of approval
  4. Access granted to HCP-only features

---

## 3. Database Design (High-Level)

The database is the **system's memory**—it stores all persistent information in an organized, secure, and queryable format. Our design prioritizes:

- **Data integrity** (relationships enforced)
- **Privacy** (sensitive data isolated)
- **Performance** (optimized for common queries)
- **Scalability** (supports platform growth)

### Design Principles

**Relational Structure:** We use PostgreSQL, a relational database, because VOCE's data has clear relationships:

- Users participate in trials
- Users create forum posts
- Posts belong to communities
- Trials are saved by multiple users

**UUID Primary Keys:** Every record is identified by a unique, globally-unique identifier (UUID) rather than sequential numbers, enhancing security and enabling distributed systems.

**Audit Trails:** Critical tables include timestamps for creation and updates, enabling compliance reporting and debugging.

**Soft Deletes:** Important data (like user posts) is marked as deleted rather than permanently removed, maintaining data integrity and audit capabilities.

---

### Core Tables & Relationships

#### **`users`** - Identity & Authentication

**Purpose:** Stores core user identity and authentication credentials

**Key Information:**

- Unique identifier (UUID)
- Email (login credential, unique)
- Password (hashed with Argon2—never plain text)
- User type (patient, HCP, organization member, admin)
- Display name (public-facing username)
- Verification status (for HCPs requiring credential validation)
- Account status (active, suspended, deleted)
- First name, last name
- Country and language preference
- Profile completion percentage
- Consent records (GDPR/HIPAA compliance)
- Account creation date
- Last login timestamp

**Relationships:**

- One user → Many saved trials
- One user → Many forum posts
- One user → Many notifications
- One user → One user profile (extended info)
- One user → Many event registrations

---

#### **`user_profiles`** - Extended User Information

**Purpose:** Stores detailed, optional user information separate from core identity

**Why separate?** Reduces load on authentication queries; allows flexible profile updates without touching sensitive credentials table.

**Key Information:**

- Profile identifier (UUID)
- Link to user (foreign key to `users.id`)
- Medical condition (for patients—used in trial matching)
- Specialization (for HCPs—cardiology, oncology, etc.)
- Medical license number (for HCPs)
- Organization affiliation
- Bio/about me section
- Interests/disease areas of interest (array)
- Notification preferences
- Avatar/profile image URL
- Privacy settings

**Relationships:**

- One-to-one with `users` table

---

#### **`clinical_trials`** - Trial Registry

**Purpose:** Central repository of all clinical trial information

**Key Information:**

- Trial identifier (UUID - internal)
- NCT ID (official ClinicalTrials.gov identifier)
- Title
- Full description
- Disease area (HIV, Malaria, TB, etc.)
- Phase (1, 2, 3, 4, Post-Market)
- Status (recruiting, active, completed, suspended)
- Sponsor (pharmaceutical company or institution)
- Countries where trial is conducted (array)
- Eligibility criteria (structured text or array)
- Start date
- Estimated completion date
- Maximum enrollment target
- Current enrollment count
- Contact information
- Metadata (JSONB field for flexible, unstructured trial-specific data)
- Last updated timestamp (for sync tracking)

**Relationships:**

- One trial → Many trial saves (by users)
- One trial → Many trial alerts (user subscriptions)
- One trial → Many sites (trial_sites table)

**Indexing Strategy:** Full-text search index on title, description, and disease for fast querying.

---

#### **`trial_saves`** - User Bookmarks

**Purpose:** Tracks which users have saved which trials

**Key Information:**

- Relationship identifier
- User ID (foreign key)
- Trial ID (foreign key)
- Saved timestamp
- Notes (optional user notes about why they saved it)

**Relationships:**

- Many-to-many bridge between `users` and `clinical_trials`

---

#### **`trial_alerts`** - Trial Notifications

**Purpose:** User subscriptions to be notified about new matching trials

**Key Information:**

- Alert identifier
- User ID (foreign key)
- Trial ID (foreign key, nullable—can be for general criteria)
- Alert frequency (instant, daily, weekly)
- Filter criteria (disease, location, phase—stored as JSON)
- Last notified timestamp
- Active status (enable/disable without deleting)

**Relationships:**

- Many alerts per user
- Can be associated with specific trial or general search criteria

---

#### **`communities`** - Forum Categories

**Purpose:** Organizes forum discussions into topical communities

**Key Information:**

- Community identifier
- Name (e.g., "HIV Support", "Clinical Trial Experiences")
- Description
- Type (disease-specific, general, HCP-only)
- Moderation level (open, pre-moderated, restricted)
- Member count
- Post count
- Created date
- Icon/image

**Relationships:**

- One community → Many forum posts

---

#### **`forum_posts`** - Discussion Threads

**Purpose:** User-generated discussion content

**Key Information:**

- Post identifier
- User ID (foreign key—author)
- Community ID (foreign key)
- Title
- Content (supports markdown)
- Post type (question, story, discussion, announcement)
- Moderation status (approved, pending, flagged, removed)
- Created timestamp
- Updated timestamp
- Views count
- Replies count
- Upvotes/likes count
- Downvotes count (future consideration)
- Is pinned (for important announcements)
- Is locked (prevents new replies)

**Relationships:**

- One post → Many comments/replies
- Author is a user
- Belongs to one community

---

#### **`comments`** - Post Replies

**Purpose:** Responses to forum posts

**Key Information:**

- Comment identifier
- Post ID (foreign key)
- User ID (foreign key—author)
- Content
- Timestamp
- Likes count
- Parent comment ID (for nested replies—optional for MVP)
- Moderation status

**Relationships:**

- Many comments belong to one post
- Author is a user

---

#### **`organizations`** - Institutional Partners

**Purpose:** Directory of partner organizations and institutions

**Key Information:**

- Organization identifier
- Organization name
- Organization type (hospital, research institution, advocacy group, pharma)
- Description
- Country
- Website URL
- Membership status (partner, affiliated, verified)
- Joined date
- Contact email
- Logo image

**Relationships:**

- One organization → Many members (users)
- One organization → Many sponsored trials

---

#### **`working_groups`** - Collaborative Groups

**Purpose:** Specialized groups for research collaboration or advocacy

**Key Information:**

- Group identifier
- Name
- Organization ID (foreign key, nullable)
- Description
- Type (research, advocacy, patient support)
- Privacy level (public, private, invitation-only)
- Member count
- Created date

**Relationships:**

- One group → Many members
- May be associated with an organization

---

#### **`resources`** - Educational Materials

**Purpose:** Library of vetted educational content

**Key Information:**

- Resource identifier
- Title
- Type (video, document, toolkit, course)
- Category (clinical trials 101, patient rights, disease education)
- Description
- File URL or external link
- Duration or page count
- Language
- Downloads count
- Average rating
- Author or source organization
- Publication date
- Featured status
- Requires authentication (boolean)
- Tags (array)

**Relationships:**

- One resource → Many ratings
- May be associated with organization

---

#### **`events`** - Webinars & Gatherings

**Purpose:** Calendar of educational and networking events

**Key Information:**

- Event identifier
- Title
- Description
- Event date and time
- Timezone
- Event type (webinar, conference, training, roundtable)
- Organizer (user or organization)
- Virtual meeting link
- Physical location (if applicable)
- Participant count (current)
- Maximum participants
- Registration deadline
- Tags
- Status (upcoming, ongoing, completed, cancelled)

**Relationships:**

- One event → Many registered users (via registration table)

---

#### **`event_registrations`** - Attendance Tracking

**Purpose:** Tracks which users are registered for which events

**Key Information:**

- Registration identifier
- Event ID (foreign key)
- User ID (foreign key)
- Registration timestamp
- Attendance status (registered, attended, no-show)
- Confirmation sent boolean

**Relationships:**

- Many-to-many bridge between `users` and `events`

---

#### **`notifications`** - User Alerts

**Purpose:** In-app notification system

**Key Information:**

- Notification identifier
- User ID (foreign key—recipient)
- Type (trial, community, event, system)
- Title
- Message content
- Related link (URL to relevant page)
- Read status
- Created timestamp
- Expiration date (optional)

**Relationships:**

- Many notifications per user

---

#### **`surveys`** - Research Instruments

**Purpose:** Stores survey definitions and metadata

**Key Information:**

- Survey identifier
- Title
- Description
- Purpose
- Target audience (patient types, roles)
- Estimated completion time
- Active status
- Consent text
- Created/published date
- Closing date

**Relationships:**

- One survey → Many questions
- One survey → Many responses

---

#### **`survey_questions`** - Survey Items

**Purpose:** Individual questions within surveys

**Key Information:**

- Question identifier
- Survey ID (foreign key)
- Question text
- Question type (multiple choice, scale, open text, etc.)
- Order/position in survey
- Required status
- Options (for multiple choice—stored as JSON array)

**Relationships:**

- Many questions belong to one survey

---

#### **`survey_responses`** - User Answers

**Purpose:** Collected survey data from users

**Key Information:**

- Response identifier
- Survey ID (foreign key)
- User ID (foreign key, nullable if anonymous)
- Question ID (foreign key)
- Answer (JSON field to accommodate different response types)
- Submitted timestamp

**Relationships:**

- Many responses per survey
- User may be anonymous based on survey design

---

#### **`content_reports`** - Moderation Queue

**Purpose:** User-flagged content requiring review

**Key Information:**

- Report identifier
- Reporter user ID (foreign key)
- Target type (post, comment, user)
- Target ID
- Reason category (misinformation, harassment, spam, medical advice)
- Description
- Status (pending, reviewed, resolved)
- Moderating admin ID (foreign key, nullable)
- Resolution notes
- Created timestamp
- Resolved timestamp

**Relationships:**

- Many reports can target same content
- Assigned to admin for resolution

---

#### **`password_reset_tokens`** - Secure Password Recovery

**Purpose:** Manages password reset workflow

**Key Information:**

- Token identifier
- User ID (foreign key)
- Secure token string (cryptographically random)
- Created timestamp
- Expires timestamp (typically 1 hour from creation)
- Used status (boolean)

**Relationships:**

- Many tokens per user (historical)

**Security Notes:**

- Tokens are single-use only
- Automatically expire after time limit
- Previous tokens invalidated when new one generated

---

### Conceptual Relationships Summary

```
USERS
  ├─→ has one USER_PROFILE
  ├─→ saves many CLINICAL_TRIALS (via trial_saves)
  ├─→ subscribes to TRIAL_ALERTS
  ├─→ authors many FORUM_POSTS
  ├─→ writes many COMMENTS
  ├─→ registers for many EVENTS
  ├─→ receives many NOTIFICATIONS
  ├─→ completes many SURVEY_RESPONSES
  └─→ belongs to ORGANIZATIONS/WORKING_GROUPS

CLINICAL_TRIALS
  ├─→ saved by many USERS
  ├─→ has many TRIAL_ALERTS
  └─→ conducted at many sites

COMMUNITIES
  └─→ contains many FORUM_POSTS

FORUM_POSTS
  ├─→ belongs to one COMMUNITY
  ├─→ has one author (USER)
  └─→ has many COMMENTS

ORGANIZATIONS
  ├─→ has many members (USERS)
  └─→ sponsors many WORKING_GROUPS

RESOURCES
  ├─→ created by ORGANIZATIONS or USERS
  └─→ rated by USERS

SURVEYS
  ├─→ contains many QUESTIONS
  └─→ receives many RESPONSES from USERS
```

---

## 4. Security & Compliance Considerations

While this document avoids technical implementation, these non-negotiable principles guide all backend development:

### **Data Privacy**

- **Principle:** Users own their data and control its usage
- **Implementation:** Explicit consent flows, granular privacy settings, right to data export and deletion
- **Standard:** GDPR Article 7 (Consent), HIPAA Privacy Rule

### **Authentication Security**

- **Principle:** Passwords never stored in recoverable format
- **Implementation:** Argon2 hashing, JWT tokens with expiration, secure session management
- **Protection against:** Brute force attacks (rate limiting), credential stuffing, session hijacking

### **Data Encryption**

- **At Rest:** Database encryption for sensitive fields (license numbers, health data)
- **In Transit:** HTTPS/TLS for all API communication
- **Purpose:** Protects data even if physical storage compromised

### **Access Control**

- **Principle:** Users can only access data they're authorized to see
- **Implementation:** Role-based permissions (patient, HCP, admin), resource ownership verification
- **Example:** Users can only edit their own posts, admins can moderate any content

### **Content Moderation**

- **Principle:** Platform must not become vector for misinformation or harm
- **Implementation:** Automated filtering + human review queue, medical advice disclaimers
- **Balance:** Enable free expression while protecting vulnerable users

### **Audit Logging**

- **Principle:** Critical actions must be traceable
- **Implementation:** Log authentication attempts, data changes, admin actions
- **Purpose:** Security investigations, compliance reporting, debugging

---

## 5. Technical Constraints & Non-Functional Requirements

### **Performance Targets**

- API response time: < 200ms for 95% of requests
- Database query optimization for trials search (most frequent operation)
- Pagination for all list endpoints to prevent data overload

### **Scalability Preparation**

- Database connection pooling
- Stateless API design (enables horizontal scaling)
- Background job queue for heavy operations (email sending, data imports)

### **Error Handling**

- Graceful degradation (API returns meaningful error messages)
- Never expose internal system details in errors
- Consistent error format for frontend parsing

### **Monitoring & Observability**

- Health check endpoints
- Error rate tracking
- Performance metrics (request duration, database query time)
- User analytics (feature usage, engagement patterns)

---

## 6. MVP Scope & Future Roadmap

### **What's IN the MVP**

✅ User authentication and profiles  
✅ Clinical trial search and bookmarking  
✅ Community forums with basic moderation  
✅ Educational resource library  
✅ Event calendar and registration  
✅ Basic notification system  
✅ Password reset flow  
✅ HCP verification workflow

### **What's DEFERRED to Post-MVP**

🔄 Real-time chat/messaging  
🔄 Advanced AI-powered trial matching  
🔄 Multi-language support (beyond English)  
🔄 Mobile native apps (web-first for MVP)  
🔄 Payment processing (for premium tiers)  
🔄 Direct trial enrollment (requires regulatory compliance)  
🔄 Electronic consent management  
🔄 Integration with EHR systems

---

## 7. Alignment with Frontend

This backend design directly supports all current frontend pages:

| Frontend Page      | Backend APIs Used                                          |
| ------------------ | ---------------------------------------------------------- |
| **Login/Register** | `/auth/login`, `/auth/register`                            |
| **Dashboard**      | `/users/me`, `/trials` (recommendations), `/notifications` |
| **Trial Search**   | `/trials` (with filters)                                   |
| **Trial Details**  | `/trials/{id}`, `/trials/{id}/save`                        |
| **Community**      | `/community/posts`, `/community/posts/{id}/like`           |
| **Post Details**   | `/community/posts/{id}`, `/community/posts/{id}/replies`   |
| **Events**         | `/events`, `/events/{id}/register`                         |
| **Resources**      | `/resources`, `/resources/{id}`                            |
| **Profile**        | `/users/me`, `/users/me/saved-trials`                      |
| **Notifications**  | `/notifications`, `/notifications/{id}/read`               |
| **Assistant**      | `/ai/chat`                                                 |
| **Admin Panel**    | `/admin/*` endpoints                                       |

---

## 8. Success Metrics (How We'll Measure Backend Quality)

### **Reliability**

- Uptime target: 99.9% (less than 43 minutes downtime per month)
- Zero data loss incidents
- Successful database backup verification

### **Performance**

- 95th percentile API response time < 200ms
- Search results returned in < 500ms
- Database query optimization achieving target response times

### **Security**

- Zero successful authentication bypasses
- All security headers properly configured
- Regular dependency vulnerability scans passing

### **Developer Experience**

- API documentation 100% accurate and up-to-date
- All endpoints covered by automated tests
- Clear error messages enable frontend debugging

---

## 9. Conclusion & Next Steps

This backend conception provides the foundation for VOCE's technical implementation. It balances:

- **Simplicity** (MVP-focused, avoiding over-engineering)
- **Security** (HIPAA/GDPR-compliant from day one)
- **Scalability** (architecture supports future growth)
- **User-centricity** (every endpoint serves clear user need)

### **Immediate Next Steps**

1. **PM Review & Approval** → Validate that this conception aligns with product vision
2. **Frontend Alignment** → Ensure frontend team agrees on API contracts
3. **Database Schema Finalization** → Translate conceptual design to SQL schema
4. **API Contract Documentation** → Generate OpenAPI/Swagger specification
5. **Development Sprint Planning** → Break implementation into phases
6. **Test Strategy** → Define test coverage requirements
