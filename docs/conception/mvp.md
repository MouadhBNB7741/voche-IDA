# 🏛️ Annex III: Final Technical Roadmap & MVP Architecture

---

## 1. Executive Summary of Technology
> **Mission:** To support VOCE’s dual mission of **engagement** (community building) and **evidence generation** (data science).

The technical architecture utilizes a **Data-First Stack (React + Python + SQL)**. This shift ensures the platform is AI-ready and capable of complex relational data management from Day 1. It explicitly separates *Clinical Observations* (HCPs) from *Content Moderation*, ensuring scientific integrity and clear data pipelines.

---

## 2. The Tech Stack (PERN - Python Edition)

| Component    | Technology         | Rationale for VOCE                                                           |
| :----------- | :----------------- | :--------------------------------------------------------------------------- |
| **Frontend** | `React.js (Vite)`  | Responsive, mobile-first interface optimized for low-bandwidth (LMICs).      |
| **Backend**  | `Python (FastAPI)` | High-performance API. Native support for AI/Data Science (Pandas, NumPy).    |
| **Database** | `PostgreSQL`       | Robust relational management for **Patients ↔ Trials ↔ Hospitals**.          |
| **ORM**      | `SQLAlchemy`       | Secure database interactions and SQL injection prevention.                   |
| **Search**   | `Postgres FTS`     | Built-in full-text search for clinical trials without external dependencies. |
| **Infra**    | `Docker / AWS`     | Containerized deployment for consistency across dev and production.          |

---

## 3. MVP Roadmap
*This roadmap is strictly scoped to the Minimum Viable Product, prioritized by the "Golden Rule": Does this connect a user to a trial or educate them on advocacy?*

### 🏗️ PHASE 1: Core Infrastructure & Compliance
* **Repo & Env Setup:** Initialize Monorepo with React and FastAPI.
* **Security Layer:** 
    * **HIPAA/GDPR-compliant** encryption (at rest and in transit).
    * **Consent Manager Middleware**: Enforces granular consent before DB writes.
* **API Gateway:** RESTful structure (`/api/v1/`) with rate limiting.
* **Interoperability:** **FHIR** standard compliant data models.

### 🔑 PHASE 2: Identity & Access Management (RBAC)
* **Auth Architecture:** OAuth2 with **JWT** for stateless session management.
* **User Roles:**
    * **Patient:** Anonymous browsing + "Saved Trials" registration.
    * **HCP:** Registration with "Medical License ID" verification flag.
    * **Admin:** Dashboard for content moderation.
* **Onboarding:** Dynamic tagging for "Disease Interests" (e.g., HIV, Malaria).

### 🧬 PHASE 3: Clinical Trial Navigator & Data Engine
* **Database Schema:** Relational tables for `Trials`, `Locations`, and `Inclusion_Criteria`.
* **Data Separation:** Distinct `ClinicalObservations` (HCPs) vs. `Reports` (Abuse).
* **Data Ingestion:** Bulk Upload Tool (CSV/JSON) for Admin curation.
* **Search Engine:** FastAPI endpoint: `GET /trials?disease=TB&country=South_Africa`.
* **HCP Feedback:** Dedicated form for anonymized clinical observations.

### 📚 PHASE 4: Engagement & Education Hubs
* **Resource Library:** Admin CMS for PDF toolkits and video links.
* **Forums (MVP Lite):** Threaded discussions with identity masking.
* **Moderation:** "Report Content" flags to prevent medical misinformation.
* **Partnership Gateway:** `POST /contact` for coalition API requests.

### 🤖 PHASE 5: AI Assistant & Intelligence
* **VOCE Assistant:** Rule-based Python logic (Decision Tree) for navigation.
* **Analytics:** Backend logs for "Most Searched Diseases" to inform IDA policy.

### 🚀 PHASE 6: Pilot & Launch Readiness
* **Localization (i18n):** Support for **English + 1 Priority Language**.
* **Beta Group:** UAT with 50 Patients and 10 HCPs.
* **Feedback Loop:** Integrated "Suggest a Feature" and "Report a Bug" UI.

---

## 4. Final MVP Action Matrix (Functional Spec)

### A. Authentication & Users
| Actor          | Action   | Route                 | System Logic                     |
| :------------- | :------- | :-------------------- | :------------------------------- |
| **Visitor**    | Register | `POST /auth/register` | Create User + Verify Email.      |
| **Visitor**    | Login    | `POST /auth/token`    | Validate + Return JWT.           |
| **HCP** `🔒`    | Verify   | `POST /users/verify`  | Upload License → `pending` flag. |
| **Public** `🌍` | Inquiry  | `POST /contact`       | Structured email to Admin.       |

### B. Clinical Trial Navigator
| Actor           | Action   | Route                       | System Logic               |
| :-------------- | :------- | :-------------------------- | :------------------------- |
| **Any** `🌍`     | Search   | `GET /trials`               | Postgres Full-Text Search. |
| **Patient** `🔒` | Connect  | `POST /trials/{id}/connect` | Log lead internally.       |
| **HCP** `🔒`     | Observe  | `POST /observations`        | Submit clinical feedback.  |
| **HCP** `🔒`     | Protocol | `GET /trials/{id}/protocol` | Serve technical PDF.       |

### C. Education & Community
| Actor        | Action    | Route                | System Logic                 |
| :----------- | :-------- | :------------------- | :--------------------------- |
| **Any** `🌍`  | Resources | `GET /resources`     | List PDFs by Tag.            |
| **Any** `🌍`  | Chat      | `POST /chat/triage`  | Static Decision Tree Bot.    |
| **User** `🔒` | Post      | `POST /forums/posts` | Create thread (Hidden ID).   |
| **User** `🔒` | Report    | `POST /reports`      | Flag content for moderation. |

---

## 5. MVP Golden Rule & Constraints

> [!IMPORTANT]
> **The Filter:** If a feature does not **connect a user to a trial** or **educate them on advocacy**, it is **NOT MVP**.

1.  **Strict Neutrality:** Ranking by relevance (location/disease), never by sponsorship.
2.  **No Medical Advice:** Hard-coded disclaimers; Chatbot is navigation-only.
3.  **Low-Bandwidth:** Compressed assets and "Lazy Loading" for 3G networks.