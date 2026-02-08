# Database Initialization - VOCE Platform

## 📋 Overview

This directory contains the database schema and indexes for the VOCE clinical trials platform.

**Design Document:** See `docs/conception/dbStrucutre.md` for full specification

## 📁 Files

```
db/
├── schema.sql          # All table definitions (CREATE TABLE statements)
├── indexes.sql         # All performance indexes
├── README.md           # This file
└── postgres.py         # Connection pool and query helpers
```

## 🗄️ Database Structure

### Table Count: 24 tables organized in 8 categories

1. **User Management** (3 tables)
   - `users` - Core authentication
   - `user_profiles` - Extended user data
   - `password_reset_tokens` - Password recovery

2. **Organizations** (1 table)
   - `organizations` - Institutional partners

3. **Clinical Trials** (4 tables)
   - `clinical_trials` - Trial registry
   - `trial_sites` - Geographic locations
   - `trial_saves` - User bookmarks
   - `trial_alerts` - Notification subscriptions

4. **Community & Forums** (4 tables)
   - `communities` - Forum categories
   - `forum_posts` - Discussion threads
   - `comments` - Replies with threading
   - `content_reports` - Moderation system

5. **Collaboration** (3 tables)
   - `working_groups` - Research/advocacy groups
   - `organization_members` - Org membership
   - `working_group_members` - Group membership

6. **Events & Resources** (4 tables)
   - `events` - Webinars, conferences
   - `event_registrations` - Attendance tracking
   - `resources` - Educational content
   - `resource_ratings` - User reviews

7. **Surveys & Research** (3 tables)
   - `surveys` - Research instruments
   - `survey_questions` - Question definitions
   - `survey_responses` - User answers

8. **System & Engagement** (2 tables)
   - `notifications` - User inbox
   - `user_activity_log` - Analytics & audit

## 🚀 Quick Start

### Prerequisites
- PostgreSQL 16+
- Database created: `voce`
- Database user with CREATE permissions

### Option 1: Manual Setup (Recommended for learning)

```bash
# 1. Create database
createdb voce

# 2. Apply schema
psql -h localhost -U postgres -d voce -f backend/app/db/schema.sql

# 3. Create indexes
psql -h localhost -U postgres -d voce -f backend/app/db/indexes.sql

# 4. Verify
psql -h localhost -U postgres -d voce -c "\dt"  # List tables
psql -h localhost -U postgres -d voce -c "\di"  # List indexes
```

### Option 2: Single Command

```bash
# Apply both schema and indexes
psql -h localhost -U postgres -d voce -f backend/app/db/schema.sql -f backend/app/db/indexes.sql
```

### Option 3: Using Environment Variable

```bash
# If you have DATABASE_URL set
psql $DATABASE_URL -f backend/app/db/schema.sql
psql $DATABASE_URL -f backend/app/db/indexes.sql
```

## 📊 Table Dependencies

Tables must be created in this order (already correct in schema.sql):

```
1. users                    (no dependencies)
2. organizations            (no dependencies)
3. password_reset_tokens    (depends on: users)
4. user_profiles            (depends on: users, organizations)
5. clinical_trials          (no dependencies)
6. trial_sites              (depends on: clinical_trials)
7. trial_saves              (depends on: users, clinical_trials)
8. trial_alerts             (depends on: users, clinical_trials)
9. communities              (no dependencies)
10. forum_posts             (depends on: users, communities)
11. comments                (depends on: users, forum_posts)
12. content_reports         (depends on: users)
13. working_groups          (depends on: organizations)
14. organization_members    (depends on: users, organizations)
15. working_group_members   (depends on: users, working_groups)
16. events                  (no dependencies)
17. event_registrations     (depends on: users, events)
18. resources               (depends on: organizations)
19. resource_ratings        (depends on: users, resources)
20. surveys                 (no dependencies)
21. survey_questions        (depends on: surveys)
22. survey_responses        (depends on: users, surveys, survey_questions)
23. notifications           (depends on: users)
24. user_activity_log       (depends on: users)
```

## 🔑 Key Design Decisions

### UUID Primary Keys
- All tables use UUID (v4) as primary keys
- Better for distributed systems
- Prevents ID enumeration attacks
- Example: `id UUID PRIMARY KEY DEFAULT uuid_generate_v4()`

### Timestamp Standards
- All timestamps use `TIMESTAMPTZ` (with timezone)
- All timestamps default to `NOW()` (UTC)
- Standard fields: `created_at`, `updated_at`

### JSONB Flexibility
- Used for flexible/evolving data
- Examples:
  - `clinical_trials.metadata` - Additional trial data
  - `user_profiles.interests` - Array of topics
  - `forum_posts.tags` - Post categorization
  - `user_activity_log.metadata` - Analytics context

### Soft Deletes
- Critical tables use `is_deleted` flag instead of hard deletes
- Tables with soft delete:
  - `forum_posts.is_deleted`
  - `comments.is_deleted`
- Preserves data for:
  - Audit trails
  - Legal compliance
  - Content moderation

### Foreign Key Strategies

**CASCADE:**
- User deletes their account → their trial saves deleted
- Trial deleted → trial sites deleted
- Example: `ON DELETE CASCADE`

**SET NULL:**
- User deletes account → their posts remain (author=NULL)
- Preserves community content
- Example: `ON DELETE SET NULL`

## 🔍 Full-Text Search

### Prepared for PostgreSQL FTS

**Tables with search indexes:**
- `clinical_trials` - title, summary
- `forum_posts` - title, content

**Index type:** GIN with pg_trgm (fuzzy matching)

**Example query (future):**
```sql
SELECT * FROM clinical_trials
WHERE title ILIKE '%cancer%'
   OR summary ILIKE '%cancer%';
```

**Optimized with:**
```sql
CREATE INDEX idx_clinical_trials_title_search 
  ON clinical_trials USING GIN (title gin_trgm_ops);
```

## 📈 Performance Indexes

### Index Strategy
- **Foreign Keys:** All indexed for join performance
- **User Lookups:** `users.email`, `users.user_type`
- **Trial Search:** `disease_area`, `status`, `phase`
- **Community:** `forum_posts.community_id`, created date
- **Partial Indexes:** Used for active-only queries
  - `WHERE is_active = TRUE`
  - `WHERE status = 'active'`
  - `WHERE featured = TRUE`

### Index Count
Total indexes created: ~100+

**Example partial index:**
```sql
CREATE INDEX idx_users_is_active 
  ON users(is_active) 
  WHERE is_active = TRUE;
```

## 🔒 Security & Compliance

### GDPR Considerations
- Soft deletes preserve audit trail
- `users.consent_given` tracks consent
- `user_activity_log` includes IP/user agent
- Consider retention policies for logs

### PII Fields (Encrypted at rest recommended)
- `users.email`
- `users.first_name`, `last_name`
- `user_profiles.license_number`

### No PHI Stored
- `user_profiles.condition` is self-reported, not diagnostic
- No medical records or health information
- HIPAA compliance maintained through design

## 🧪  Verification

After applying schema and indexes:

```bash
# Count tables 
psql -h localhost -U postgres -d voce -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';"

# List all tables
psql -h localhost -U postgres -d voce -c "\dt"

# Check foreign keys
psql -h localhost -U postgres -d voce -c "\
SELECT
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name
FROM information_schema.table_constraints AS tc
JOIN information_schema.key_column_usage AS kcu
  ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage AS ccu
  ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY';
"

# Check indexes count
psql -h localhost -U postgres -d voce -c "SELECT COUNT(*) FROM pg_indexes WHERE schemaname = 'public';"

# Table sizes
psql -h localhost -U postgres -d voce -c "
SELECT
    relname AS table_name,
    pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;
"
```

## 🗑️ Reset Database (Destructive!)

**WARNING: This deletes ALL data!**

```bash
# Option 1: Drop and recreate database
dropdb voce
createdb voce
psql -d voce -f backend/app/db/schema.sql
psql -d voce -f backend/app/db/indexes.sql

# Option 2: Drop all tables
psql -d voce -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
psql -d voce -f backend/app/db/schema.sql
psql -d voce -f backend/app/db/indexes.sql
```

## 📝 Next Steps

After database initialization:

### 1. Seed Data (Future)
Create seed data for:
- Default admin user
- Sample communities
- Test clinical trials
- System notifications

### 2. Migrations Strategy (Future)
Consider adding migration framework:
- **Option A:** Custom SQL migration scripts
- **Option B:** Python migration tools (e.g., Alembic for tracking only)
- **Option C:** Manual versioned SQL files

### 3. Connection from Application

The database is ready to use with async Python:

```python
from app.db.postgres import PostgresDB

# Initialize connection pool (in main.py startup)
await PostgresDB.connect()

# Query example
users = await PostgresDB.fetch_all("""
    SELECT id, email, user_type, created_at
    FROM users
    WHERE is_active = TRUE
    ORDER BY created_at DESC
    LIMIT 10
""")

# Insert example
await PostgresDB.execute("""
    INSERT INTO users (email, password_hash, user_type, display_name)
    VALUES ($1, $2, $3, $4)
""", email, password_hash, 'patient', display_name)
```

## 🐛 Troubleshooting

### Extension not found
```
ERROR:  extension "uuid-ossp" does not exist
```
**Solution:**
```bash
psql -d voce -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"
psql -d voce -c "CREATE EXTENSION IF NOT EXISTS \"pg_trgm\";"
```

### Permission denied
```
ERROR:  permission denied for schema public
```
**Solution:** Ensure your database user has CREATE permissions
```bash
psql -d voce -c "GRANT ALL ON SCHEMA public TO your_username;"
```

### Table already exists
```
ERROR:  relation "users" already exists
```
**Solution:** Either drop the table or use DROP TABLE IF EXISTS
```bash
psql -d voce -c "DROP TABLE IF EXISTS users CASCADE;"
```

## 📚 Resources

- **Design Document:** `docs/conception/dbStrucutre.md`

## 🤝 Contributing

When adding new tables:

1. Add to `schema.sql` in correct dependency order
2. Add appropriate indexes to `indexes.sql`
3. Update this README with table count and categories
4. Document in `docs/conception/dbStrucutre.md`
5. Consider foreign key ON DELETE behavior
6. Add comments explaining purpose
