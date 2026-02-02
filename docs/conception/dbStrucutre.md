# 🏛 VOCE Platform | Database Schema (MVP)

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

## 👤 1. Authentication & Users (RBAC)

### `users`
*Core identity and access control.*

| Field             | Type              | Notes                                     |
| :---------------- | :---------------- | :---------------------------------------- |
| 🔑 `id`            | `UUID (PK)`       | Primary Identifier                        |
| 📧 `email`         | `VARCHAR(UNIQUE)` | Indexed Login Credential                  |
| 🔐 `password_hash` | `VARCHAR`         | Argon2 / Bcrypt Hash                      |
| 🎭 `role`          | `VARCHAR`         | `PATIENT`, `HCP`, `ORG_MEMBER`, `ADMIN`   |
| 👤 `display_name`  | `VARCHAR`         | Public-facing username                    |
| ✅ `is_verified`   | `BOOLEAN`         | Default `FALSE` (Audit required for HCPs) |
| 🟢 `is_active`     | `BOOLEAN`         | Default `TRUE`                            |
| 📅 `created_at`    | `TIMESTAMP`       | `DEFAULT NOW()`                           |
| 🕒 `last_login`    | `TIMESTAMP`       | Security Audit Trail                      |

### `profiles_patient`
*One-to-One with `users`.*

| Field                 | Type            | Notes                         |
| :-------------------- | :-------------- | :---------------------------- |
| 🔑 `user_id`           | `UUID (PK, FK)` | Link to `users.id`            |
| 🧬 `disease_interests` | `JSONB`         | e.g., `["HIV", "Malaria"]`    |
| 🌍 `location_country`  | `VARCHAR(2)`    | ISO Country Code (e.g., "KE") |
| 🗣 `language_pref`     | `VARCHAR(2)`    | e.g., "en", "sw"              |
| 📜 `consent_version`   | `VARCHAR`       | Terms version accepted        |

### `profiles_hcp`
*One-to-One with `users`.*

| Field                    | Type            | Notes                   |
| :----------------------- | :-------------- | :---------------------- |
| 🔑 `user_id`              | `UUID (PK, FK)` | Link to `users.id`      |
| 🆔 `medical_license_id`   | `VARCHAR`       | Verification data       |
| 🩺 `specialty`            | `VARCHAR`       | e.g., "Oncology"        |
| 🏥 `hospital_affiliation` | `VARCHAR`       | Optional workplace      |
| 📄 `verification_url`     | `VARCHAR`       | S3 Link to ID (Private) |

---

## 🧬 2. Clinical Trial Navigator

### `trials`
*The primary clinical dataset.*

| Field                  | Type        | Notes                               |
| :--------------------- | :---------- | :---------------------------------- |
| 🔑 `id`                 | `UUID (PK)` |                                     |
| 🆔 `external_id`        | `VARCHAR`   | e.g., NCT Number                    |
| 📝 `title`              | `TEXT`      | Scientific Title                    |
| 📖 `summary`            | `TEXT`      | Layman-friendly description         |
| 🧪 `phase`              | `VARCHAR`   | Phase 1-4                           |
| 🚦 `status`             | `VARCHAR`   | `RECRUITING`, `ACTIVE`, `COMPLETED` |
| 🔍 `inclusion_criteria` | `JSONB`     | Structured for AI Matching          |
| 🦠 `conditions`         | `TEXT[]`    | Array of tags                       |
| 🏢 `sponsors`           | `JSONB`     | Pharma/University data              |

### `trial_locations`
*Geographic availability.*

| Field             | Type         | Notes               |
| :---------------- | :----------- | :------------------ |
| 🔑 `id`            | `UUID (PK)`  |                     |
| 🔗 `trial_id`      | `UUID (FK)`  | Link to `trials.id` |
| 🏢 `facility_name` | `VARCHAR`    |                     |
| 📍 `city`          | `VARCHAR`    |                     |
| 🌍 `country`       | `VARCHAR(2)` | ISO Code (Indexed)  |
| 🗺 `geo_lat/long`  | `FLOAT`      | Map visualization   |

---

## 📈 3. Lead Gen & Observations

### `trial_leads`
*Patient-to-Trial connections.*

| Field               | Type        | Notes                          |
| :------------------ | :---------- | :----------------------------- |
| 🔑 `id`              | `UUID (PK)` |                                |
| 👤 `user_id`         | `UUID (FK)` | The Patient                    |
| 🧪 `trial_id`        | `UUID (FK)` | The Trial                      |
| 🚦 `status`          | `VARCHAR`   | `NEW`, `REVIEWED`, `CONTACTED` |
| ✅ `consent_granted` | `BOOLEAN`   | Legal requirement              |

### `clinical_observations`
*HCP-provided insights.*

| Field                | Type        | Notes                    |
| :------------------- | :---------- | :----------------------- |
| 🔑 `id`               | `UUID (PK)` |                          |
| 🩺 `hcp_user_id`      | `UUID (FK)` | Submitting Doctor        |
| 🏷 `observation_type` | `VARCHAR`   | `BARRIER`, `SIDE_EFFECT` |
| 💬 `content`          | `TEXT`      | Feedback text            |
| 🕵️ `is_anonymized`    | `BOOLEAN`   | Default `TRUE`           |

---

## 📚 4. Education & Community

### `resources` (CMS)
| Field    | Type        | Notes                  |
| :------- | :---------- | :--------------------- |
| 🔑 `id`   | `UUID (PK)` |                        |
| 📄 `type` | `VARCHAR`   | `PDF`, `VIDEO`, `LINK` |
| 🔗 `url`  | `TEXT`      | S3 / External Link     |
| 🏷 `tags` | `TEXT[]`    | Searchable categories  |

### `forum_posts` (Community)
| Field         | Type        | Notes           |
| :------------ | :---------- | :-------------- |
| 🔑 `id`        | `UUID (PK)` |                 |
| 📁 `topic_id`  | `UUID (FK)` | Forum Category  |
| 👤 `user_id`   | `UUID (FK)` | Author          |
| 💬 `content`   | `TEXT`      | Post body       |
| 🛡 `is_hidden` | `BOOLEAN`   | Moderation flag |

---

## 🛠 5. System & Search

### `audit_logs`
| Field          | Type        | Notes                   |
| :------------- | :---------- | :---------------------- |
| 🔑 `id`         | `UUID (PK)` |                         |
| 👤 `user_id`    | `UUID (FK)` | Actor                   |
| ⚡ `action`     | `VARCHAR`   | `LOGIN`, `DELETE`, etc. |
| 🌐 `ip_address` | `VARCHAR`   | Masked for privacy      |

---

### 🔍 Search Indexing (PostgreSQL)

```sql
-- Enable Full-Text Search on Trials
ALTER TABLE trials ADD COLUMN search_vector tsvector;

UPDATE trials 
SET search_vector = to_tsvector('english', 
    coalesce(title, '') || ' ' || 
    coalesce(summary, '') || ' ' || 
    array_to_string(conditions, ' ')
);

CREATE INDEX trials_search_idx ON trials USING GIN(search_vector);
```