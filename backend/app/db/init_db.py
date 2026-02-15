import os
import logging
import json
from datetime import datetime
from app.db.postgres import PostgresDB
from app.core.security import hash_password

logger = logging.getLogger(__name__)

async def init_db():
    """
    Checks if the database is initialized. 
    If not, applies schema and indexes.
    """
    pool = PostgresDB.get_pool()
    async with pool.acquire() as conn:
        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        )
        if not table_exists:
            logger.info("📦 Database tables not found. Initializing...")
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            schema_path = os.path.join(base_dir, "app", "db", "schema.sql")
            indexes_path = os.path.join(base_dir, "app", "db", "indexes.sql")
            
            if os.path.exists(schema_path) and os.path.exists(indexes_path):
                with open(schema_path, "r", encoding="utf-8") as f:
                    schema_sql = f.read()
                with open(indexes_path, "r", encoding="utf-8") as f:
                    indexes_sql = f.read()
                
                async with conn.transaction():
                    await conn.execute(schema_sql)
                    await conn.execute(indexes_sql)
                logger.info("✅ Database schema and indexes applied.")
                
                # Auto-seed after fresh init
                await seed_db(conn)
            else:
                logger.error(f"❌ SQL files not found at {schema_path} or {indexes_path}")
        else:
            logger.info("✅ Database tables already exist.")

async def seed_db(conn):
    """
    Seeds the database with initial data (5 trials, 1 user).
    Uses hashed passwords and detailed trial data.
    """
    logger.info("🌱 Seeding database...")
    
    # 1. Seed User
    pwd_raw = "Password123!"
    pwd_hash = hash_password(pwd_raw)
    
    user_id = await conn.fetchval("""
        INSERT INTO users (
            email, password_hash, user_type, display_name, first_name, last_name, 
            status, is_active, is_verified, profile_completed,
            notification_preferences, verification
        ) 
        VALUES (
            'seed_user@example.com', $1, 'patient', 'SeedUser', 'Seed', 'User',
            'active', TRUE, TRUE, TRUE, 
            '{"emailAlerts": true, "pushNotifications": true, "frequency": "instant"}'::jsonb,
            '{"status": "verified"}'::jsonb
        )
        ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
        RETURNING id
    """, pwd_hash)
    
    # Create profile
    await conn.execute("""
        INSERT INTO user_profiles (user_id, bio, location)
        VALUES ($1, 'I am a seed user.', 'Global')
        ON CONFLICT (user_id) DO NOTHING
    """, user_id)

    # 2. Seed 5 Clinical Trials
    # Data matches docs/conception/dbStrucutre.md fields
    trials = [
        {
            "nct_id": "NCT00000001", 
            "title": "Breast Cancer Advanced Study", 
            "summary": "This is a phase 3 study evaluating the efficacy of a new therapeutic agent for advanced breast cancer patients.", 
            "disease_area": "Breast Cancer", 
            "phase": "Phase 3", 
            "status": "Recruiting", 
            "sponsor": "Global Health Phama",
            "eligibility_criteria": "Inclusion: Female, Age 18-70, Histologically confirmed BC.\nExclusion: Prior chemotherapy within 30 days.",
            "start_date": "2024-01-01",
            "estimated_completion": "2026-12-31",
            "enrollment": 150,
            "max_enrollment": 500,
            "contact": "contact@globalhealth.com",
            "metadata": {"tags": ["oncology", "women's health"]}
        },
        {
            "nct_id": "NCT00000002", 
            "title": "Type 2 Diabetes Insulin Trial", 
            "summary": "Research on new insulin delivery methods to improve glycemic control in Type 2 Diabetes.", 
            "disease_area": "Diabetes", 
            "phase": "Phase 2", 
            "status": "Active", 
            "sponsor": "BioMed Research",
            "eligibility_criteria": "Inclusion: Type 2 Diabetes diagnosis > 1 year.\nExclusion: Type 1 Diabetes.",
            "start_date": "2023-06-15",
            "estimated_completion": "2025-06-15",
            "enrollment": 80,
            "max_enrollment": 200,
            "contact": "trials@biomed.org",
            "metadata": {"tags": ["metabolic", "insulin"]}
        },
        {
            "nct_id": "NCT00000003", 
            "title": "Lung Cancer Early Detection", 
            "summary": "Analyzing the effectiveness of new screening protocols for early stage lung cancer detection.", 
            "disease_area": "Lung Cancer", 
            "phase": "Phase 1", 
            "status": "Recruiting", 
            "sponsor": "Oncology Institute",
            "eligibility_criteria": "Inclusion: Smokers/Ex-smokers, Age 40+.\nExclusion: Prior history of lung cancer.",
            "start_date": "2024-03-01",
            "estimated_completion": "2025-03-01",
            "enrollment": 20,
            "max_enrollment": 100,
            "contact": "recruit@oncologyinst.org",
            "metadata": {"tags": ["oncology", "screening"]}
        },
        {
            "nct_id": "NCT00000004", 
            "title": "Alzheimer's Prevention Study", 
            "summary": "Longitudinal observational study on cognitive health and lifestyle factors preventing Alzheimer's.", 
            "disease_area": "Alzheimer's Disease", 
            "phase": "Phase 4", 
            "status": "Completed", 
            "sponsor": "Neuro Sciences",
            "eligibility_criteria": "Inclusion: Age 60+.\nExclusion: Diagnosed dementia.",
            "start_date": "2020-01-01",
            "estimated_completion": "2024-01-01",
            "enrollment": 1000,
            "max_enrollment": 1000,
            "contact": "info@neurosciences.com",
            "metadata": {"tags": ["neurology", "aging"]}
        },
        {
            "nct_id": "NCT00000005", 
            "title": "Cardiovascular Risk Reduction", 
            "summary": "Assessing statin efficacy in low-risk populations for long-term cardiovascular health.", 
            "disease_area": "Cardiology", 
            "phase": "Phase 3", 
            "status": "Suspended", 
            "sponsor": "Heart Group",
            "eligibility_criteria": "Inclusion: Age 45-65, Low LDL.\nExclusion: Previous cardiac event.",
            "start_date": "2022-09-01",
            "estimated_completion": "2026-09-01",
            "enrollment": 300,
            "max_enrollment": 2000,
            "contact": "study@heartgroup.org",
            "metadata": {"tags": ["cardiology", "prevention"]}
        }
    ]
    
    for t in trials:
        await conn.execute("""
            INSERT INTO clinical_trials (
                nct_id, title, summary, disease_area, phase, status, 
                sponsor, countries, eligibility_criteria, start_date, 
                estimated_completion, enrollment, max_enrollment, contact, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, '["USA", "France", "UK"]'::jsonb, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (nct_id) DO NOTHING
        """, 
        t["nct_id"], t["title"], t["summary"], t["disease_area"], t["phase"], t["status"], 
        t["sponsor"], t["eligibility_criteria"], datetime.strptime(t["start_date"], "%Y-%m-%d").date(),
        datetime.strptime(t["estimated_completion"], "%Y-%m-%d").date(), t["enrollment"], t["max_enrollment"], 
        t["contact"], json.dumps(t["metadata"])
        )

    logger.info("✅ Seeding completed.")
