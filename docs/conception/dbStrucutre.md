# 🏛 VochePlatform | Database Schema (MVP)

> **Architecture:** PERN Stack (PostgreSQL, Express/FastAPI, React, Node/Python)  
> **Standards:** Relational Integrity + AI-Ready JSONB + UUID Primary Keys

---

## 🛠 Technical Specification

| Feature         | Standard                            |
| :-------------- | :---------------------------------- |
| **Database**    | PostgreSQL 16+                      |
| **ORM**         | SQLAlchemy (Python) / Prisma (Node) |
| **Identity**    | UUID v4                             |
| **Timezone**    | UTC                                 |
| **Flexibility** | JSONB for unstructured AI data      |

---

## 📋 Table of Contents

1. [User Management](#user-management)
   - users
   - user_profiles
   - password_reset_tokens
2. [Clinical Trials](#clinical-trials)
   - clinical_trials
   - trial_sites
   - trial_saves
   - trial_alerts
3. [Community & Forums](#community--forums)
   - communities
   - forum_posts
   - comments
   - content_reports
4. [Organizations & Collaboration](#organizations--collaboration)
   - organizations
   - working_groups
   - organization_members
   - working_group_members
5. [Events & Resources](#events--resources)
   - events
   - event_registrations
   - resources
   - resource_ratings
6. [Surveys & Research](#surveys--research)
   - surveys
   - survey_questions
   - survey_responses
   - survey_completions
7. [System & Engagement](#system--engagement)
   - notifications
   - user_activity_log

---

## 1. User Management

### `users`
*Core identity and access control.*

| Field                  | Type              | Constraints       | Notes                                     |
| :--------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `id`                | `UUID`            | `PRIMARY KEY`     | Primary Identifier (v4)                   |
| 📧 `email`             | `VARCHAR(255)`    | `UNIQUE, NOT NULL`| Indexed Login Credential                  |
| 🔐 `password_hash`     | `VARCHAR(255)`    | `NOT NULL`        | Argon2 / Bcrypt Hash                      |
| 🎭 `user_type`         | `VARCHAR(50)`     | `NOT NULL`        | `patient`, `hcp`, `org_member`, `admin`   |
| 👤 `display_name`      | `VARCHAR(100)`    | `NOT NULL`        | Public-facing username                    |
| 📛 `first_name`        | `VARCHAR(100)`    | `NULL`            | User's first name                         |
| 📛 `last_name`         | `VARCHAR(100)`    | `NULL`            | User's last name                          |
| 🌍 `country`           | `VARCHAR(100)`    | `NULL`            | User's country (ISO code or name)         |
| 🗣️ `language_preference`| `VARCHAR(10)`    | `DEFAULT 'en'`    | Preferred language (ISO 639-1 code)       |
| 📊 `status`            | `VARCHAR(50)`     | `DEFAULT 'active'`| `active`, `suspended`, `pending`, `deleted`|
| ✅ `is_verified`       | `BOOLEAN`         | `DEFAULT FALSE`   | Email/Account verification status         |
| 🟢 `is_active`         | `BOOLEAN`         | `DEFAULT TRUE`    | Account active status                     |
| 📝 `profile_completed` | `BOOLEAN`         | `DEFAULT FALSE`   | Has user completed onboarding             |
| 📜 `consent_given`     | `BOOLEAN`         | `DEFAULT FALSE`   | GDPR/HIPAA consent acknowledgment         |
| 🖼️ `avatar`            | `TEXT`            | `NULL`            | Profile image URL                         |
| 📅 `created_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Account creation timestamp (UTC)          |
| 🕒 `last_login`        | `TIMESTAMP`       | `NULL`            | Security audit trail                      |
| 🔄 `updated_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Last profile update                       |

**Indexes:**
- `idx_users_email` on `email` (unique, for fast login lookup)
- `idx_users_user_type` on `user_type` (for role-based queries)
- `idx_users_status` on `status` (for active user queries)

**Constraints:**
- `CHECK (user_type IN ('patient', 'hcp', 'org_member', 'admin'))`
- `CHECK (status IN ('active', 'suspended', 'pending', 'deleted'))`

---

### `user_profiles`
*Extended user information and preferences.*

| Field                   | Type              | Constraints       | Notes                                     |
| :---------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `profile_id`         | `UUID`            | `PRIMARY KEY`     | Primary identifier                        |
| 👤 `user_id`            | `UUID`            | `FOREIGN KEY, UNIQUE`| References `users(id)` ON DELETE CASCADE|
| 🩺 `condition`          | `VARCHAR(255)`    | `NULL`            | Medical condition (for patients)          |
| 👨‍⚕️ `specialization`    | `VARCHAR(255)`    | `NULL`            | Medical specialization (for HCPs)         |
| 🆔 `license_number`     | `VARCHAR(100)`    | `NULL`            | Medical license number (for HCPs)         |
| 🏢 `organization_id`    | `UUID`            | `FOREIGN KEY, NULL`| References `organizations(org_id)`       |
| 📝 `bio`                | `TEXT`            | `NULL`            | User biography/about section              |
| 🏷️ `interests`          | `JSONB`           | `DEFAULT '[]'`    | Array of disease areas/topics of interest |
| 🔔 `notification_enabled`| `BOOLEAN`        | `DEFAULT TRUE`    | Master notification toggle                |
| 🌐 `location`           | `VARCHAR(255)`    | `NULL`            | City/region (for trial matching)          |
| 📊 `profile_visibility` | `VARCHAR(50)`     | `DEFAULT 'public'`| `public`, `community_only`, `private`     |
| 📧 `email_alerts`       | `BOOLEAN`         | `DEFAULT TRUE`    | Email notification preference             |
| 📱 `push_notifications` | `BOOLEAN`         | `DEFAULT FALSE`   | Push notification preference              |
| 🔒 `show_saved_trials`  | `BOOLEAN`         | `DEFAULT FALSE`   | Privacy: show saved trials publicly       |
| 📅 `created_at`         | `TIMESTAMP`       | `DEFAULT NOW()`   | Profile creation timestamp                |
| 🔄 `updated_at`         | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_user_profiles_user_id` on `user_id` (unique)
- `idx_user_profiles_organization_id` on `organization_id`

**Constraints:**
- `CHECK (profile_visibility IN ('public', 'community_only', 'private'))`

---

### `password_reset_tokens`
*Secure password recovery management.*

| Field           | Type              | Constraints       | Notes                                     |
| :-------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `id`         | `UUID`            | `PRIMARY KEY`     | Token identifier                          |
| 👤 `user_id`    | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 🎫 `token`      | `VARCHAR(255)`    | `UNIQUE, NOT NULL`| Cryptographically secure token            |
| ⏰ `created_at` | `TIMESTAMP`       | `DEFAULT NOW()`   | Token generation time                     |
| ⏳ `expires_at` | `TIMESTAMP`       | `NOT NULL`        | Token expiration (typically +1 hour)      |
| ✅ `used`       | `BOOLEAN`         | `DEFAULT FALSE`   | Has token been used                       |
| 🕒 `used_at`    | `TIMESTAMP`       | `NULL`            | When token was consumed                   |

**Indexes:**
- `idx_password_reset_tokens_token` on `token` (unique, for fast lookup)
- `idx_password_reset_tokens_user_id` on `user_id`
- `idx_password_reset_tokens_expires_at` on `expires_at` (for cleanup queries)

**Note:** Old tokens should be periodically cleaned up via scheduled job.

---

## 2. Clinical Trials

### `clinical_trials`
*Central registry of all clinical trial information.*

| Field                    | Type              | Constraints       | Notes                                     |
| :----------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `trial_id`            | `UUID`            | `PRIMARY KEY`     | Internal trial identifier                 |
| 🆔 `nct_id`              | `VARCHAR(50)`     | `UNIQUE, NULL`    | ClinicalTrials.gov NCT identifier         |
| 📌 `title`               | `VARCHAR(500)`    | `NOT NULL`        | Official trial title                      |
| 📄 `summary`             | `TEXT`            | `NULL`            | Plain-language trial description          |
| 🩺 `disease_area`        | `VARCHAR(255)`    | `NOT NULL`        | Primary disease/condition                 |
| 🔬 `phase`               | `VARCHAR(50)`     | `NOT NULL`        | `Phase 1`, `Phase 2`, `Phase 3`, `Phase 4`|
| 📊 `status`              | `VARCHAR(50)`     | `NOT NULL`        | `Recruiting`, `Active`, `Completed`, etc. |
| 🏢 `sponsor`             | `VARCHAR(255)`    | `NOT NULL`        | Sponsoring organization                   |
| 🌍 `countries`           | `JSONB`           | `DEFAULT '[]'`    | Array of countries where trial runs       |
| 📋 `eligibility_criteria`| `TEXT`            | `NULL`            | Inclusion/exclusion criteria              |
| 📅 `start_date`          | `DATE`            | `NULL`            | Trial start date                          |
| 🏁 `estimated_completion`| `DATE`            | `NULL`            | Expected completion date                  |
| 👥 `enrollment`          | `INTEGER`         | `DEFAULT 0`       | Current enrollment count                  |
| 🎯 `max_enrollment`      | `INTEGER`         | `NULL`            | Target enrollment                         |
| 📧 `contact`             | `VARCHAR(255)`    | `NULL`            | Primary contact information               |
| 📦 `metadata`            | `JSONB`           | `DEFAULT '{}'`    | Additional trial-specific data            |
| 🔄 `last_updated`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Last data sync/update timestamp           |
| 📅 `created_at`          | `TIMESTAMP`       | `DEFAULT NOW()`   | Record creation timestamp                 |

**Indexes:**
- `idx_clinical_trials_nct_id` on `nct_id` (unique)
- `idx_clinical_trials_disease_area` on `disease_area`
- `idx_clinical_trials_status` on `status`
- `idx_clinical_trials_phase` on `phase`
- Full-text search index on `title`, `summary` (PostgreSQL GIN/GIST)

**Constraints:**
- `CHECK (phase IN ('Phase 1', 'Phase 2', 'Phase 3', 'Phase 4', 'Post-Market'))`
- `CHECK (status IN ('Recruiting', 'Active', 'Completed', 'Suspended', 'Not yet recruiting'))`

---

### `trial_sites`
*Physical locations where trials are conducted.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `site_id`         | `UUID`            | `PRIMARY KEY`     | Site identifier                           |
| 🔬 `trial_id`        | `UUID`            | `FOREIGN KEY, NOT NULL`| References `clinical_trials(trial_id)`  |
| 🏥 `site_name`       | `VARCHAR(255)`    | `NOT NULL`        | Hospital/clinic name                      |
| 🌍 `country`         | `VARCHAR(100)`    | `NOT NULL`        | Country                                   |
| 🏙️ `city`            | `VARCHAR(100)`    | `NOT NULL`        | City                                      |
| 📍 `address`         | `TEXT`            | `NULL`            | Full address                              |
| 📧 `contact_email`   | `VARCHAR(255)`    | `NULL`            | Site contact email                        |
| ☎️ `contact_phone`   | `VARCHAR(50)`     | `NULL`            | Site contact phone                        |
| ✅ `is_recruiting`   | `BOOLEAN`         | `DEFAULT TRUE`    | Site actively recruiting                  |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Record creation                           |

**Indexes:**
- `idx_trial_sites_trial_id` on `trial_id`
- `idx_trial_sites_country` on `country`

---

### `trial_saves`
*User bookmarks for trials.*

| Field           | Type              | Constraints       | Notes                                     |
| :-------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `id`         | `UUID`            | `PRIMARY KEY`     | Save record identifier                    |
| 👤 `user_id`    | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 🔬 `trial_id`   | `UUID`            | `FOREIGN KEY, NOT NULL`| References `clinical_trials(trial_id)` ON DELETE CASCADE|
| 📝 `notes`      | `TEXT`            | `NULL`            | User's personal notes about trial         |
| 📅 `saved_at`   | `TIMESTAMP`       | `DEFAULT NOW()`   | When trial was saved                      |

**Indexes:**
- `idx_trial_saves_user_id` on `user_id`
- `idx_trial_saves_trial_id` on `trial_id`
- `unique_user_trial_save` UNIQUE(`user_id`, `trial_id`) - prevent duplicate saves

---

### `trial_alerts`
*User subscriptions for trial notifications.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `alert_id`        | `UUID`            | `PRIMARY KEY`     | Alert identifier                          |
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 🔬 `trial_id`        | `UUID`            | `FOREIGN KEY, NULL`| Specific trial (or NULL for criteria-based)|
| 🩺 `disease_area`    | `VARCHAR(255)`    | `NULL`            | Disease area filter                       |
| 🌍 `location`        | `VARCHAR(255)`    | `NULL`            | Location preference                       |
| 🔬 `phase`           | `VARCHAR(50)`     | `NULL`            | Trial phase preference                    |
| 📦 `filter_criteria` | `JSONB`           | `DEFAULT '{}'`    | Additional filter criteria                |
| 🔔 `alert_frequency` | `VARCHAR(50)`     | `DEFAULT 'weekly'`| `instant`, `daily`, `weekly`              |
| 🕒 `last_notified`   | `TIMESTAMP`       | `NULL`            | Last notification sent                    |
| ✅ `is_active`       | `BOOLEAN`         | `DEFAULT TRUE`    | Alert enabled/disabled                    |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Alert creation timestamp                  |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_trial_alerts_user_id` on `user_id`
- `idx_trial_alerts_is_active` on `is_active`

**Constraints:**
- `CHECK (alert_frequency IN ('instant', 'daily', 'weekly'))`

---

## 3. Community & Forums

### `communities`
*Forum categories and discussion groups.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `community_id`    | `UUID`            | `PRIMARY KEY`     | Community identifier                      |
| 📛 `name`            | `VARCHAR(255)`    | `UNIQUE, NOT NULL`| Community name/title                      |
| 📝 `description`     | `TEXT`            | `NULL`            | Community description                     |
| 🏷️ `type`            | `VARCHAR(50)`     | `NOT NULL`        | `disease_specific`, `general`, `hcp_only` |
| 🎨 `icon`            | `VARCHAR(255)`    | `NULL`            | Icon URL or emoji                         |
| 🛡️ `moderation_level`| `VARCHAR(50)`     | `DEFAULT 'open'`  | `open`, `pre_moderated`, `restricted`     |
| 👥 `member_count`    | `INTEGER`         | `DEFAULT 0`       | Total members                             |
| 📊 `post_count`      | `INTEGER`         | `DEFAULT 0`       | Total posts                               |
| ✅ `is_active`       | `BOOLEAN`         | `DEFAULT TRUE`    | Community active status                   |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Community creation timestamp              |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last activity timestamp                   |

**Indexes:**
- `idx_communities_type` on `type`
- `idx_communities_is_active` on `is_active`

**Constraints:**
- `CHECK (type IN ('disease_specific', 'general', 'hcp_only'))`
- `CHECK (moderation_level IN ('open', 'pre_moderated', 'restricted'))`

---

### `forum_posts`
*User-generated discussion threads.*

| Field                  | Type              | Constraints       | Notes                                     |
| :--------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `post_id`           | `UUID`            | `PRIMARY KEY`     | Post identifier                           |
| 👤 `user_id`           | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE SET NULL (preserve content)|
| 🏘️ `community_id`      | `UUID`            | `FOREIGN KEY, NOT NULL`| References `communities(community_id)`  |
| 📌 `title`             | `VARCHAR(500)`    | `NOT NULL`        | Post title                                |
| 📝 `content`           | `TEXT`            | `NOT NULL`        | Post content (supports markdown)          |
| 🏷️ `post_type`         | `VARCHAR(50)`     | `DEFAULT 'discussion'`| `question`, `story`, `discussion`, `announcement`|
| 🛡️ `moderation_status` | `VARCHAR(50)`     | `DEFAULT 'approved'`| `pending`, `approved`, `flagged`, `removed`|
| 📅 `created_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Post creation timestamp                   |
| 🔄 `updated_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Last edit timestamp                       |
| 👁️ `views_count`       | `INTEGER`         | `DEFAULT 0`       | Total views                               |
| 💬 `replies_count`     | `INTEGER`         | `DEFAULT 0`       | Total replies/comments                    |
| 👍 `upvotes_count`     | `INTEGER`         | `DEFAULT 0`       | Total likes/upvotes                       |
| 👎 `downvotes_count`   | `INTEGER`         | `DEFAULT 0`       | Total downvotes (optional)                |
| 📌 `is_pinned`         | `BOOLEAN`         | `DEFAULT FALSE`   | Pinned to top of community                |
| 🔒 `is_locked`         | `BOOLEAN`         | `DEFAULT FALSE`   | Prevents new replies                      |
| 🗑️ `is_deleted`        | `BOOLEAN`         | `DEFAULT FALSE`   | Soft delete flag                          |
| 🏷️ `tags`              | `JSONB`           | `DEFAULT '[]'`    | Array of tags                             |

**Indexes:**
- `idx_forum_posts_user_id` on `user_id`
- `idx_forum_posts_community_id` on `community_id`
- `idx_forum_posts_moderation_status` on `moderation_status`
- `idx_forum_posts_created_at` on `created_at` DESC (for recent posts)
- Full-text search index on `title`, `content`

**Constraints:**
- `CHECK (post_type IN ('question', 'story', 'discussion', 'announcement'))`
- `CHECK (moderation_status IN ('pending', 'approved', 'flagged', 'removed'))`

---

### `comments`
*Replies to forum posts.*

| Field                  | Type              | Constraints       | Notes                                     |
| :--------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `comment_id`        | `UUID`            | `PRIMARY KEY`     | Comment identifier                        |
| 📰 `post_id`           | `UUID`            | `FOREIGN KEY, NOT NULL`| References `forum_posts(post_id)` ON DELETE CASCADE|
| 👤 `user_id`           | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE SET NULL|
| 💬 `parent_comment_id` | `UUID`            | `FOREIGN KEY, NULL`| References `comments(comment_id)` for nested replies|
| 📝 `content`           | `TEXT`            | `NOT NULL`        | Comment content                           |
| 📅 `created_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Comment creation timestamp                |
| 🔄 `updated_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Last edit timestamp                       |
| 👍 `likes_count`       | `INTEGER`         | `DEFAULT 0`       | Total likes                               |
| 🛡️ `moderation_status` | `VARCHAR(50)`     | `DEFAULT 'approved'`| `pending`, `approved`, `flagged`, `removed`|
| 🗑️ `is_deleted`        | `BOOLEAN`         | `DEFAULT FALSE`   | Soft delete flag                          |

**Indexes:**
- `idx_comments_post_id` on `post_id`
- `idx_comments_user_id` on `user_id`
- `idx_comments_parent_comment_id` on `parent_comment_id`
- `idx_comments_created_at` on `created_at`

---

### `content_reports`
*User-flagged content for moderation.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `report_id`       | `UUID`            | `PRIMARY KEY`     | Report identifier                         |
| 👤 `reporter_id`     | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE SET NULL|
| 🏷️ `target_type`     | `VARCHAR(50)`     | `NOT NULL`        | `post`, `comment`, `user`                 |
| 🎯 `target_id`       | `UUID`            | `NOT NULL`        | ID of reported content                    |
| 📝 `target_content`  | `TEXT`            | `NULL`            | Snapshot of content at report time        |
| 🚩 `reason`          | `VARCHAR(100)`    | `NOT NULL`        | `misinformation`, `harassment`, `spam`, `medical_advice`|
| 📄 `description`     | `TEXT`            | `NULL`            | Additional reporter notes                 |
| 📊 `status`          | `VARCHAR(50)`     | `DEFAULT 'pending'`| `pending`, `reviewed`, `resolved`        |
| 👨‍💼 `moderator_id`    | `UUID`            | `FOREIGN KEY, NULL`| References `users(id)` - assigned moderator|
| 📝 `resolution_notes`| `TEXT`            | `NULL`            | Moderator's resolution notes              |
| ⚖️ `action_taken`    | `VARCHAR(100)`    | `NULL`            | `approved`, `removed`, `warned`, `banned` |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Report creation timestamp                 |
| 🔄 `resolved_at`     | `TIMESTAMP`       | `NULL`            | Resolution timestamp                      |

**Indexes:**
- `idx_content_reports_target` on `target_type`, `target_id`
- `idx_content_reports_status` on `status`
- `idx_content_reports_reporter_id` on `reporter_id`

**Constraints:**
- `CHECK (target_type IN ('post', 'comment', 'user'))`
- `CHECK (reason IN ('misinformation', 'harassment', 'spam', 'medical_advice', 'other'))`
- `CHECK (status IN ('pending', 'reviewed', 'resolved'))`

---

## 4. Organizations & Collaboration

### `organizations`
*Institutional partners and verified organizations.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `org_id`          | `UUID`            | `PRIMARY KEY`     | Organization identifier                   |
| 🏢 `org_name`        | `VARCHAR(255)`    | `UNIQUE, NOT NULL`| Official organization name                |
| 🏷️ `org_type`        | `VARCHAR(100)`    | `NOT NULL`        | `hospital`, `research_institution`, `advocacy_group`, `pharma`|
| 📝 `description`     | `TEXT`            | `NULL`            | Organization description                  |
| 🌍 `country`         | `VARCHAR(100)`    | `NOT NULL`        | Primary country of operation              |
| 🌐 `website`         | `VARCHAR(255)`    | `NULL`            | Organization website URL                  |
| 📊 `membership_status`| `VARCHAR(50)`    | `DEFAULT 'pending'`| `pending`, `partner`, `affiliated`, `verified`|
| 📅 `joined_date`     | `DATE`            | `DEFAULT NOW()`   | Platform join date                        |
| 📧 `contact_email`   | `VARCHAR(255)`    | `NOT NULL`        | Primary contact email                     |
| 🖼️ `logo`            | `VARCHAR(255)`    | `NULL`            | Logo image URL                            |
| 👥 `member_count`    | `INTEGER`         | `DEFAULT 0`       | Total members                             |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Record creation timestamp                 |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_organizations_org_type` on `org_type`
- `idx_organizations_country` on `country`

**Constraints:**
- `CHECK (org_type IN ('hospital', 'research_institution', 'advocacy_group', 'pharma', 'other'))`
- `CHECK (membership_status IN ('pending', 'partner', 'affiliated', 'verified'))`

---

### `working_groups`
*Collaborative research and advocacy groups.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `group_id`        | `UUID`            | `PRIMARY KEY`     | Working group identifier                  |
| 📛 `name`            | `VARCHAR(255)`    | `NOT NULL`        | Working group name                        |
| 🏢 `organization_id` | `UUID`            | `FOREIGN KEY, NULL`| References `organizations(org_id)`       |
| 📝 `description`     | `TEXT`            | `NULL`            | Group description and goals               |
| 🏷️ `type`            | `VARCHAR(50)`     | `NOT NULL`        | `research`, `advocacy`, `patient_support` |
| 🔒 `privacy_level`   | `VARCHAR(50)`     | `DEFAULT 'public'`| `public`, `private`, `invitation_only`    |
| 👥 `member_count`    | `INTEGER`         | `DEFAULT 0`       | Total members                             |
| ✅ `is_active`       | `BOOLEAN`         | `DEFAULT TRUE`    | Group active status                       |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Group creation timestamp                  |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last activity timestamp                   |

**Indexes:**
- `idx_working_groups_organization_id` on `organization_id`
- `idx_working_groups_type` on `type`

**Constraints:**
- `CHECK (type IN ('research', 'advocacy', 'patient_support'))`
- `CHECK (privacy_level IN ('public', 'private', 'invitation_only'))`

---

### `organization_members`
*User membership in organizations.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `id`              | `UUID`            | `PRIMARY KEY`     | Membership record identifier              |
| 🏢 `org_id`          | `UUID`            | `FOREIGN KEY, NOT NULL`| References `organizations(org_id)` ON DELETE CASCADE|
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 🎭 `role`            | `VARCHAR(50)`     | `DEFAULT 'member'`| `admin`, `moderator`, `member`            |
| 📊 `status`          | `VARCHAR(50)`     | `DEFAULT 'pending'`| `pending`, `approved`, `rejected`        |
| 📅 `joined_at`       | `TIMESTAMP`       | `DEFAULT NOW()`   | Membership start timestamp                |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_organization_members_org_id` on `org_id`
- `idx_organization_members_user_id` on `user_id`
- `unique_org_user_membership` UNIQUE(`org_id`, `user_id`)

---

### `working_group_members`
*User membership in working groups.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `id`              | `UUID`            | `PRIMARY KEY`     | Membership record identifier              |
| 🔬 `group_id`        | `UUID`            | `FOREIGN KEY, NOT NULL`| References `working_groups(group_id)` ON DELETE CASCADE|
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 🎭 `role`            | `VARCHAR(50)`     | `DEFAULT 'member'`| `admin`, `moderator`, `member`            |
| 📊 `status`          | `VARCHAR(50)`     | `DEFAULT 'approved'`| `pending`, `approved`, `rejected`       |
| 📅 `joined_at`       | `TIMESTAMP`       | `DEFAULT NOW()`   | Membership start timestamp                |

**Indexes:**
- `idx_working_group_members_group_id` on `group_id`
- `idx_working_group_members_user_id` on `user_id`
- `unique_group_user_membership` UNIQUE(`group_id`, `user_id`)

---

## 5. Events & Resources

### `events`
*Educational events, webinars, and conferences.*

| Field                  | Type              | Constraints       | Notes                                     |
| :--------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `event_id`          | `UUID`            | `PRIMARY KEY`     | Event identifier                          |
| 📌 `title`             | `VARCHAR(500)`    | `NOT NULL`        | Event title                               |
| 📝 `description`       | `TEXT`            | `NOT NULL`        | Event description and agenda              |
| 📅 `event_date`        | `DATE`            | `NOT NULL`        | Event date                                |
| 🕒 `event_time`        | `TIME`            | `NOT NULL`        | Event start time                          |
| 🌍 `timezone`          | `VARCHAR(50)`     | `DEFAULT 'UTC'`   | Event timezone                            |
| 🏷️ `type`              | `VARCHAR(50)`     | `NOT NULL`        | `webinar`, `conference`, `training`, `roundtable`|
| 🏢 `organizer`         | `VARCHAR(255)`    | `NOT NULL`        | Organizing entity                         |
| 🌐 `location`          | `VARCHAR(255)`    | `NULL`            | Physical location or "Virtual"            |
| 🔗 `virtual_link`      | `VARCHAR(500)`    | `NULL`            | Virtual meeting link                      |
| 👥 `participants`      | `INTEGER`         | `DEFAULT 0`       | Current registrations                     |
| 🎯 `max_participants`  | `INTEGER`         | `NULL`            | Maximum capacity                          |
| ⏰ `registration_deadline`| `TIMESTAMP`    | `NULL`            | Last date to register                     |
| 📊 `status`            | `VARCHAR(50)`     | `DEFAULT 'upcoming'`| `upcoming`, `ongoing`, `completed`, `cancelled`|
| 🏷️ `tags`              | `JSONB`           | `DEFAULT '[]'`    | Event tags/topics                         |
| 🖼️ `banner_image`      | `VARCHAR(255)`    | `NULL`            | Event banner URL                          |
| 📅 `created_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Event creation timestamp                  |
| 🔄 `updated_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_events_event_date` on `event_date`
- `idx_events_type` on `type`
- `idx_events_status` on `status`

**Constraints:**
- `CHECK (type IN ('webinar', 'conference', 'training', 'roundtable'))`
- `CHECK (status IN ('upcoming', 'ongoing', 'completed', 'cancelled'))`

---

### `event_registrations`
*User registrations for events.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `registration_id` | `UUID`            | `PRIMARY KEY`     | Registration identifier                   |
| 📅 `event_id`        | `UUID`            | `FOREIGN KEY, NOT NULL`| References `events(event_id)` ON DELETE CASCADE|
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 📊 `status`          | `VARCHAR(50)`     | `DEFAULT 'registered'`| `registered`, `attended`, `no_show`, `cancelled`|
| ✅ `confirmation_sent`| `BOOLEAN`        | `DEFAULT FALSE`   | Confirmation email sent                   |
| 📅 `registered_at`   | `TIMESTAMP`       | `DEFAULT NOW()`   | Registration timestamp                    |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_event_registrations_event_id` on `event_id`
- `idx_event_registrations_user_id` on `user_id`
- `unique_event_user_registration` UNIQUE(`event_id`, `user_id`)

**Constraints:**
- `CHECK (status IN ('registered', 'attended', 'no_show', 'cancelled'))`

---

### `resources`
*Educational materials and toolkits.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `resource_id`     | `UUID`            | `PRIMARY KEY`     | Resource identifier                       |
| 📌 `title`           | `VARCHAR(500)`    | `NOT NULL`        | Resource title                            |
| 🏷️ `type`            | `VARCHAR(50)`     | `NOT NULL`        | `video`, `document`, `toolkit`, `course`  |
| 📚 `category`        | `VARCHAR(100)`    | `NOT NULL`        | Resource category/topic                   |
| 📝 `description`     | `TEXT`            | `NOT NULL`        | Resource description                      |
| 🔗 `url`             | `VARCHAR(500)`    | `NULL`            | External URL or file path                 |
| ⏱️ `duration`        | `VARCHAR(50)`     | `NULL`            | Duration (for videos) or page count       |
| 🗣️ `language`        | `VARCHAR(10)`     | `DEFAULT 'en'`    | Resource language (ISO 639-1)             |
| 📥 `downloads`       | `INTEGER`         | `DEFAULT 0`       | Total downloads                           |
| ⭐ `rating`          | `DECIMAL(3,2)`    | `DEFAULT 0.00`    | Average rating (0.00-5.00)                |
| 🏆 `featured`        | `BOOLEAN`         | `DEFAULT FALSE`   | Featured resource flag                    |
| 🔒 `requires_auth`   | `BOOLEAN`         | `DEFAULT FALSE`   | Authentication required                   |
| 👤 `author`          | `VARCHAR(255)`    | `NULL`            | Author or source organization             |
| 🏢 `organization_id` | `UUID`            | `FOREIGN KEY, NULL`| References `organizations(org_id)`       |
| 🏷️ `tags`            | `JSONB`           | `DEFAULT '[]'`    | Resource tags                             |
| 📅 `published_date`  | `DATE`            | `NULL`            | Publication date                          |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Record creation timestamp                 |
| 🔄 `updated_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_resources_type` on `type`
- `idx_resources_category` on `category`
- `idx_resources_language` on `language`
- `idx_resources_featured` on `featured`

**Constraints:**
- `CHECK (type IN ('video', 'document', 'toolkit', 'course'))`
- `CHECK (rating >= 0 AND rating <= 5)`

---

### `resource_ratings`
*User ratings and reviews for resources.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `rating_id`       | `UUID`            | `PRIMARY KEY`     | Rating identifier                         |
| 📚 `resource_id`     | `UUID`            | `FOREIGN KEY, NOT NULL`| References `resources(resource_id)` ON DELETE CASCADE|
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| ⭐ `rating`          | `INTEGER`         | `NOT NULL`        | Rating (1-5 stars)                        |
| 📝 `review`          | `TEXT`            | `NULL`            | Optional text review                      |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Rating creation timestamp                 |

**Indexes:**
- `idx_resource_ratings_resource_id` on `resource_id`
- `idx_resource_ratings_user_id` on `user_id`
- `unique_resource_user_rating` UNIQUE(`resource_id`, `user_id`) - one rating per user per resource

**Constraints:**
- `CHECK (rating >= 1 AND rating <= 5)`

---

## 6. Surveys & Research

### `surveys`
*Research surveys and feedback instruments.*

| Field                  | Type              | Constraints       | Notes                                     |
| :--------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `survey_id`         | `UUID`            | `PRIMARY KEY`     | Survey identifier                         |
| 📌 `title`             | `VARCHAR(500)`    | `NOT NULL`        | Survey title                              |
| 📝 `description`       | `TEXT`            | `NOT NULL`        | Survey description and purpose            |
| 📜 `consent_text`      | `TEXT`            | `NULL`            | Required consent statement                |
| 🎯 `target_audience`   | `JSONB`           | `DEFAULT '[]'`    | Target user types/roles                   |
| ⏱️ `estimated_time`    | `VARCHAR(50)`     | `NULL`            | Estimated completion time                 |
| 📊 `status`            | `VARCHAR(50)`     | `DEFAULT 'draft'` | `draft`, `active`, `closed`               |
| 🎁 `incentive`         | `TEXT`            | `NULL`            | Incentive description (if any)            |
| 📅 `published_date`    | `DATE`            | `NULL`            | Survey publication date                   |
| 📅 `closing_date`      | `DATE`            | `NULL`            | Survey closing date                       |
| 📅 `created_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Survey creation timestamp                 |
| 🔄 `updated_at`        | `TIMESTAMP`       | `DEFAULT NOW()`   | Last update timestamp                     |

**Indexes:**
- `idx_surveys_status` on `status`

**Constraints:**
- `CHECK (status IN ('draft', 'active', 'closed'))`

---

### `survey_questions`
*Individual questions within surveys.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `question_id`     | `UUID`            | `PRIMARY KEY`     | Question identifier                       |
| 📊 `survey_id`       | `UUID`            | `FOREIGN KEY, NOT NULL`| References `surveys(survey_id)` ON DELETE CASCADE|
| 📝 `question_text`   | `TEXT`            | `NOT NULL`        | Question text                             |
| 🏷️ `question_type`   | `VARCHAR(50)`     | `NOT NULL`        | `multiple_choice`, `scale`, `open_text`, `yes_no`|
| 🔢 `order_position`  | `INTEGER`         | `NOT NULL`        | Question order in survey                  |
| ✅ `required`        | `BOOLEAN`         | `DEFAULT FALSE`   | Is question required                      |
| 📋 `options`         | `JSONB`           | `NULL`            | Options for multiple choice (array)       |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Question creation timestamp               |

**Indexes:**
- `idx_survey_questions_survey_id` on `survey_id`
- `idx_survey_questions_order` on `survey_id`, `order_position`

**Constraints:**
- `CHECK (question_type IN ('multiple_choice', 'scale', 'open_text', 'yes_no'))`

---

### `survey_responses`
*User responses to surveys.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `response_id`     | `UUID`            | `PRIMARY KEY`     | Response identifier                       |
| 📊 `survey_id`       | `UUID`            | `FOREIGN KEY, NOT NULL`| References `surveys(survey_id)` ON DELETE CASCADE|
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NULL`| References `users(id)` (NULL if anonymous)|
| ❓ `question_id`     | `UUID`            | `FOREIGN KEY, NOT NULL`| References `survey_questions(question_id)`|
| 💬 `answer`          | `JSONB`           | `NOT NULL`        | Answer data (flexible format)             |
| 🔒 `is_anonymous`    | `BOOLEAN`         | `DEFAULT FALSE`   | Response anonymity flag                   |
| 📅 `submitted_at`    | `TIMESTAMP`       | `DEFAULT NOW()`   | Response submission timestamp             |

**Indexes:**
- `idx_survey_responses_survey_id` on `survey_id`
- `idx_survey_responses_user_id` on `user_id`
- `idx_survey_responses_question_id` on `question_id`

---

### `survey_completions`
*Tracks overall survey completion per user.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `completion_id`   | `UUID`            | `PRIMARY KEY`     | Completion identifier                     |
| 📊 `survey_id`       | `UUID`            | `FOREIGN KEY, NOT NULL`| References `surveys(survey_id)` ON DELETE CASCADE|
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NULL`| References `users(id)` (NULL if anonymous)|
| 🔒 `is_anonymous`    | `BOOLEAN`         | `DEFAULT FALSE`   | Completion anonymity flag                 |
| 📅 `submitted_at`    | `TIMESTAMP`       | `DEFAULT NOW()`   | Completion timestamp                      |

**Indexes:**
- `idx_survey_completions_survey_id` on `survey_id`
- `idx_survey_completions_user_id` on `user_id`

**Constraints:**
- `UNIQUE(survey_id, user_id)` - Prevent duplicate completions for non-anonymous users

---

## 7. System & Engagement

### `notifications`
*User notification inbox.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `notification_id` | `UUID`            | `PRIMARY KEY`     | Notification identifier                   |
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NOT NULL`| References `users(id)` ON DELETE CASCADE|
| 🏷️ `type`            | `VARCHAR(50)`     | `NOT NULL`        | `trial`, `community`, `event`, `system`   |
| 📌 `title`           | `VARCHAR(255)`    | `NOT NULL`        | Notification title                        |
| 📝 `message`         | `TEXT`            | `NOT NULL`        | Notification message content              |
| 🔗 `link`            | `VARCHAR(500)`    | `NULL`            | Related page URL                          |
| ✅ `read`            | `BOOLEAN`         | `DEFAULT FALSE`   | Read status                               |
| ⏰ `expires_at`      | `TIMESTAMP`       | `NULL`            | Optional expiration timestamp             |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Notification creation timestamp           |

**Indexes:**
- `idx_notifications_user_id` on `user_id`
- `idx_notifications_read` on `user_id`, `read`
- `idx_notifications_created_at` on `created_at` DESC

**Constraints:**
- `CHECK (type IN ('trial', 'community', 'event', 'system'))`

---

### `user_activity_log`
*Audit trail and analytics tracking.*

| Field                | Type              | Constraints       | Notes                                     |
| :------------------- | :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `activity_id`     | `UUID`            | `PRIMARY KEY`     | Activity identifier                       |
| 👤 `user_id`         | `UUID`            | `FOREIGN KEY, NULL`| References `users(id)` (NULL for anonymous)|
| 🎬 `action`          | `VARCHAR(100)`    | `NOT NULL`        | Action performed (e.g., `search_trial`, `view_resource`)|
| 🏷️ `entity_type`     | `VARCHAR(50)`     | `NULL`            | Type of entity acted upon                 |
| 🎯 `entity_id`       | `UUID`            | `NULL`            | ID of entity acted upon                   |
| 📦 `metadata`        | `JSONB`           | `DEFAULT '{}'`    | Additional context (e.g., search query)   |
| 🌐 `ip_address`      | `VARCHAR(50)`     | `NULL`            | User IP address (privacy considerations)  |
| 🖥️ `user_agent`      | `TEXT`            | `NULL`            | Browser/device information                |
| 📅 `created_at`      | `TIMESTAMP`       | `DEFAULT NOW()`   | Activity timestamp                        |

**Indexes:**
- `idx_user_activity_log_user_id` on `user_id`
- `idx_user_activity_log_action` on `action`
- `idx_user_activity_log_created_at` on `created_at` (for time-series queries)

**Note:** Consider data retention policies and GDPR compliance for activity logs.

---

## 📊 Database Relationships Summary

```
users (1) ←→ (1) user_profiles
users (1) ←→ (N) trial_saves
users (1) ←→ (N) trial_alerts
users (1) ←→ (N) forum_posts
users (1) ←→ (N) comments
users (1) ←→ (N) notifications
users (1) ←→ (N) event_registrations
users (1) ←→ (N) resource_ratings
users (1) ←→ (N) survey_responses
users (1) ←→ (N) organization_members
users (1) ←→ (N) working_group_members

clinical_trials (1) ←→ (N) trial_sites
clinical_trials (1) ←→ (N) trial_saves
clinical_trials (1) ←→ (N) trial_alerts

communities (1) ←→ (N) forum_posts
forum_posts (1) ←→ (N) comments

organizations (1) ←→ (N) user_profiles
organizations (1) ←→ (N) working_groups
organizations (1) ←→ (N) resources
organizations (1) ←→ (N) organization_members

working_groups (1) ←→ (N) working_group_members

events (1) ←→ (N) event_registrations

resources (1) ←→ (N) resource_ratings

surveys (1) ←→ (N) survey_questions
surveys (1) ←→ (N) survey_responses
```

---

## 🔒 Security & Compliance Notes

### Data Protection
- **Personally Identifiable Information (PII):** `users.email`, `users.first_name`, `users.last_name`, `user_profiles.license_number`
  - Must be encrypted at rest
  - Access logged via `user_activity_log`
  - GDPR right to deletion must cascade appropriately

### Soft Deletes
- Critical tables use soft deletes (`is_deleted` flag) rather than hard deletes:
  - `forum_posts`
  - `comments`
  - Preserves data integrity and audit trails

### HIPAA Considerations
- No Protected Health Information (PHI) stored directly
- `user_profiles.condition` is self-reported, not diagnostic
- Email communication must use encrypted channels

### Audit Trails
- All tables include `created_at` timestamps
- Sensitive operations logged in `user_activity_log`
- Moderation actions captured in `content_reports`

---

## 🚀 Performance Optimization

### Indexing Strategy
- **Primary Keys:** All tables use UUID PKs with btree indexes
- **Foreign Keys:** Indexed for join performance
- **Full-Text Search:** GIN indexes on `clinical_trials`, `forum_posts` for search
- **Time-Series:** Descending indexes on timestamp fields for "recent items" queries

### Denormalization
- **Counter Caches:** `replies_count`, `upvotes_count`, `member_count` reduce join overhead
  - Updated via triggers or application logic
- **JSONB Fields:** `metadata`, `filter_criteria`, `interests` allow flexible data without schema changes

### Partitioning Considerations (Future)
- `user_activity_log` - partition by date (monthly) for large-scale analytics
- `notifications` - consider archiving read notifications older than 90 days

---

## 🛠️ Migration & Deployment

### Initial Setup
```sql
-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable full-text search
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Set timezone
SET timezone = 'UTC';
```

### Migration Strategy
1. **Phase 1:** Core tables (users, user_profiles, clinical_trials)
2. **Phase 2:** Community features (communities, forum_posts, comments)
3. **Phase 3:** Events, resources, organizations
4. **Phase 4:** Surveys, working groups, advanced features

### Seed Data Requirements
- Default communities (HIV Support, General Discussion, etc.)
- Admin user account
- Sample clinical trials for testing
- System notifications configuration

