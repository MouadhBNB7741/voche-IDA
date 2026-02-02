# 📋 VOCE Platform – Final MVP Action Matrix

**Scope:** MVP (Minimum Viable Product)  
**Golden Rule:** *Every action must either connect a user to a trial or educate them on advocacy.*

> **Legend**
> * **FE:** Frontend (React) | **BE:** Backend (FastAPI Python) | **DB:** Database (PostgreSQL)
> * **Auth:** `🔒` Private / Requires Login | `🌍` Public / Anonymous

---

### 1. AUTHENTICATION & PROFILE MODULE
*The entry point. Handles identity, role selection, and security.*

| Actor           | Action                  | Handler (Route Hint)       | System Logic & Data flow                                                                                  |
| :-------------- | :---------------------- | :------------------------- | :-------------------------------------------------------------------------------------------------------- |
| **Visitor**     | Register (Sign Up)      | `POST /auth/register`      | 1. Hash password (`bcrypt`).<br>2. Create `User` record.<br>3. Send verification email (Background Task). |
| **Visitor**     | Login                   | `POST /auth/token`         | 1. Validate credentials.<br>2. Return **JWT Access Token**.                                               |
| **Public** `🌍`  | **Partnership Inquiry** | `POST /contact`            | Sends a structured email to Admin from Coalitions/CSOs wanting to join.                                   |
| **User** `🔒`    | Select Role             | `POST /auth/role`          | Selects `PATIENT`, `HCP`, or `ORG`. Locks user into specific profile flow.                                |
| **Patient** `🔒` | Set Interests           | `PUT /users/me/interests`  | Updates `profile.interests` (JSONB) in DB. Used for Trial Navigator filtering.                            |
| **HCP** `🔒`     | Request Verify          | `POST /users/verification` | Uploads document (PDF/Image) to **S3**. Sets `verification_pending` flag.                                 |

---

### 2. CLINICAL TRIAL NAVIGATOR MODULE
*The "Engine" of the platform. Search and Discovery.*

| Actor           | Action                 | Handler (Route Hint)        | System Logic & Data flow                                                                                                    |
| :-------------- | :--------------------- | :-------------------------- | :-------------------------------------------------------------------------------------------------------------------------- |
| **Any** `🌍`     | Search Trials          | `GET /trials`               | **Params:** `?disease=HIV&country=Kenya`<br>**Logic:** Postgres Full-Text Search on `trials` table.                         |
| **Any** `🌍`     | View Details           | `GET /trials/{id}`          | Fetches trial metadata. Hides direct contact info for anonymous users.                                                      |
| **Patient** `🔒` | Bookmark Trial         | `POST /trials/{id}/save`    | Creates entry in `saved_trials` table (User ID + Trial ID).                                                                 |
| **Patient** `🔒` | "Connect"              | `POST /trials/{id}/connect` | 1. Check `inclusion_criteria`.<br>2. Log to `trial_leads`.<br>3. **Privacy First:** No external email sent to hospital yet. |
| **HCP** `🔒`     | **Submit Observation** | `POST /observations`        | Submits scientific feedback (e.g., "Transport barriers"). Distinct from "Reporting Abuse."                                  |
| **HCP** `🔒`     | Download Protocol      | `GET /trials/{id}/protocol` | Generates/Serves technical PDF summary for medical professionals.                                                           |
| **HCP** `🔒`     | Share Trial            | `POST /trials/{id}/share`   | Generates unique, anonymous public link for WhatsApp/Email sharing.                                                         |

---

### 3. EDUCATION & COMMUNITY MODULE
*The "Sticky" features. Literacy and Safety.*

| Actor        | Action           | Handler (Route Hint)      | System Logic & Data flow                                                   |
| :----------- | :--------------- | :------------------------ | :------------------------------------------------------------------------- |
| **Any** `🌍`  | View Resources   | `GET /resources`          | Lists PDFs/Videos filtered by tags: `Advocacy`, `Ethics`, `Literacy`.      |
| **Any** `🌍`  | Chat Triage      | `POST /chat/triage`       | **Logic:** Decision tree bot. Maps keywords to resource links (Stateless). |
| **User** `🔒` | Post in Forum    | `POST /forums/{id}/posts` | Creates thread/reply. **Privacy:** Real names hidden; uses Display Name.   |
| **User** `🔒` | **Report Abuse** | `POST /reports`           | Flags content for moderation. Auto-hides if reports > 3.                   |
| **Org** `🔒`  | Upload Toolkit   | `POST /resources`         | Uploads material. Sets status to `pending_approval`.                       |

---

### 4. ADMIN & OPERATIONS MODULE (Internal)
*Governance and Data Management.*

| Actor         | Action           | Handler (Route Hint)         | System Logic & Data flow                                             |
| :------------ | :--------------- | :--------------------------- | :------------------------------------------------------------------- |
| **Admin** `🔒` | Ingest Trials    | `POST /admin/trials/upload`  | **Logic:** CSV Parser → Data Validation → Bulk Insert into `trials`. |
| **Admin** `🔒` | Verify HCP       | `PUT /users/{id}/verify`     | Updates status to `verified`. Unlocks HCP-specific features.         |
| **Admin** `🔒` | Approve Resource | `PUT /resources/{id}/status` | Promotes content from `pending` to `published`.                      |
| **Admin** `🔒` | View Analytics   | `GET /admin/stats`           | Aggregates DB metrics: Search trends and registration counts.        |

---

### 5. SYSTEM AUTOMATION (Background)

| Trigger       | Action        | Technology        | Logic                                                                     |
| :------------ | :------------ | :---------------- | :------------------------------------------------------------------------ |
| **New Trial** | Match & Alert | `BackgroundTasks` | Scans `disease_interest` and queues "New Trial" emails to matching users. |
| **Daily**     | Data Cleanup  | `Celery Beat`     | Purges unverified accounts older than 7 days.                             |
| **On Survey** | PII Scrubbing | `Pydantic`        | Sanitizes input to remove email/phone patterns before DB persistence.     |

---

### Summary of MVP Constraints

1.  **No Direct Integration:** "Connect" logs interest internally; no direct EMR/Hospital API push.
2.  **Stateless Chat:** No conversation history is stored to prioritize user privacy.
3.  **Manual Ingestion:** Trials are managed via Admin CSV uploads, not live scraping.

