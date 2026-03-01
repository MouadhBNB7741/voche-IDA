import logging
import json
from datetime import datetime, date
from app.core.security import hash_password
from app.db.postgres import PostgresDB

logger = logging.getLogger(__name__)

async def seed_db(conn):
    """
    Seeds the database with initial data for:
    1. Users (Admin, HCP, Regular, Organization)
    2. Clinical Trials (5 examples)
    3. Communities (3 types)
    4. Clinical Observations (Samples)
    """
    logger.info("🌱 Seeding database with comprehensive test data...")
    
    # Common password hash
    pwd_raw = "Password123!"
    pwd_hash = hash_password(pwd_raw)

    # ------------------------------------------------------------------
    # 1. SEED USERS
    # ------------------------------------------------------------------
    # Profiles: 
    # - Admin (Platform Owner)
    # - HCP (Verified Doctor)
    # - Patient (Regular User)
    # - Organization Admin
    
    users_data = [
        {
            "email": "admin@voche.com",
            "role": "admin",
            "display_name": "AdminUser",
            "first_name": "System",
            "last_name": "Admin",
            "is_verified": True,
            "verification": {"status": "verified", "role": "admin"},
            "bio": "Platform Administrator"
        },
        {
            "email": "doctor@hospital.com",
            "role": "hcp",
            "display_name": "Dr. Smith",
            "first_name": "John",
            "last_name": "Smith",
            "is_verified": True,
            "verification": {
                "status": "verified", 
                "licenseNumber": "MD554433", 
                "institution": "General Hospital",
                "specialization": "Oncology"
            },
            "bio": "Oncologist with 10 years experience."
        },
        {
            "email": "patient@example.com",
            "role": "patient",
            "display_name": "JaneDoe",
            "first_name": "Jane",
            "last_name": "Doe",
            "is_verified": False,
            "verification": {"status": "unverified"},
            "bio": "Patient advocate."
        },
        {
            "email": "org_admin@pharma.com",
            "role": "org_member",
            "display_name": "PharmaRep",
            "first_name": "Robert",
            "last_name": "Pharma",
            "is_verified": True,
            "verification": {"status": "verified", "organization": "Global Pharma"},
            "bio": "Clinical trial coordinator."
        }
    ]

    user_ids = {} # Map email -> uuid

    for u in users_data:
        avatar_url = f"https://ui-avatars.com/api/?name={u['first_name']}+{u['last_name']}"
        
        uid = await conn.fetchval("""
            INSERT INTO users (
                email, password_hash, user_type, display_name, first_name, last_name, 
                status, is_active, is_verified, profile_completed,
                notification_preferences, verification, avatar
            ) 
            VALUES (
                $1, $2, $3, $4, $5, $6,
                'active', TRUE, $7, TRUE, 
                '{"emailAlerts": true, "pushNotifications": true, "frequency": "instant"}'::jsonb,
                $8, $9
            )
            ON CONFLICT (email) DO UPDATE SET 
                user_type = EXCLUDED.user_type,
                is_verified = EXCLUDED.is_verified,
                verification = EXCLUDED.verification,
                avatar = EXCLUDED.avatar
            RETURNING id
        """, u["email"], pwd_hash, u["role"], u["display_name"], u["first_name"], u["last_name"], 
           u["is_verified"], json.dumps(u["verification"]), avatar_url)
        
        user_ids[u["role"]] = uid
        
        # User Profile
        await conn.execute("""
            INSERT INTO user_profiles (user_id, bio, location)
            VALUES ($1, $2, 'New York, USA')
            ON CONFLICT (user_id) DO UPDATE SET bio = EXCLUDED.bio
        """, uid, u["bio"])

    logger.info("✅ Users seeded.")

    # ------------------------------------------------------------------
    # 2. SEED CLINICAL TRIALS
    # ------------------------------------------------------------------
    trials_data = [
        {
            "nct_id": "NCT00000001", 
            "title": "Breast Cancer Advanced Study", 
            "summary": "This is a phase 3 study evaluating the efficacy of a new therapeutic agent for advanced breast cancer patients.", 
            "disease_area": "Breast Cancer", 
            "phase": "Phase 3", 
            "status": "Recruiting", 
            "sponsor": "Global Health Pharma",
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

    trial_ids = []
    
    for t in trials_data:
        tid = await conn.fetchval("""
            INSERT INTO clinical_trials (
                nct_id, title, summary, disease_area, phase, status, 
                sponsor, countries, eligibility_criteria, start_date, 
                estimated_completion, enrollment, max_enrollment, contact, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, '["USA", "France", "UK"]'::jsonb, $8, $9, $10, $11, $12, $13, $14)
            ON CONFLICT (nct_id) DO UPDATE SET status = EXCLUDED.status
            RETURNING trial_id
        """, 
        t["nct_id"], t["title"], t["summary"], t["disease_area"], t["phase"], t["status"], 
        t["sponsor"], t["eligibility_criteria"], datetime.strptime(t["start_date"], "%Y-%m-%d").date(),
        datetime.strptime(t["estimated_completion"], "%Y-%m-%d").date(), t["enrollment"], t["max_enrollment"], 
        t["contact"], json.dumps(t["metadata"])
        )
        if tid:
            trial_ids.append(tid)

    logger.info("✅ Clinical Trials seeded.")

    # ------------------------------------------------------------------
    # 3. SEED COMMUNITIES
    # ------------------------------------------------------------------
    communities_data = [
        {
            "name": "Breast Cancer Awareness",
            "description": "Support and discussion for breast cancer patients and survivors.",
            "type": "disease_specific",
            "moderation_level": "pre_moderated"
        },
        {
            "name": "General Wellness",
            "description": "Tips and tricks for staying healthy.",
            "type": "general",
            "moderation_level": "open"
        },
        {
            "name": "Oncology Professionals",
            "description": "Private group for oncologists and researchers.",
            "type": "hcp_only",
            "moderation_level": "restricted"
        }
    ]

    for c in communities_data:
        icon_url = f"https://ui-avatars.com/api/?name={c['name']}"
        await conn.execute("""
            INSERT INTO communities (name, description, type, moderation_level, icon)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (name) DO NOTHING
        """, c["name"], c["description"], c["type"], c["moderation_level"], icon_url)

    logger.info("✅ Communities seeded.")

    # ------------------------------------------------------------------
    # 4. SEED CLINICAL OBSERVATIONS
    # ------------------------------------------------------------------
    # Using the HCP user and first trial
    if user_ids.get("hcp") and len(trial_ids) > 0:
        hcp_id = user_ids["hcp"]
        trial_id = trial_ids[0]

        observations = [
            {
                "severity": "medium",
                "summary": "Patient reported mild nausea after first dose.",
                "data": {"symptoms": ["nausea"], "duration": "2 days"}
            },
            {
                "severity": "low",
                "summary": "No significant side effects observed.",
                "data": {"status": "stable"}
            },
            {
                "severity": "critical",
                "summary": "Severe allergic reaction requiring intervention.",
                "data": {"symptoms": ["anaphylaxis"], "action_taken": "epinephrine"}
            }
        ]

        for obs in observations:
            await conn.execute("""
                INSERT INTO clinical_observations (
                    trial_id, doctor_id, severity_level, summary, feedback_data, flagged
                )
                VALUES ($1, $2, $3, $4, $5, $6)
            """, 
            trial_id, hcp_id, obs["severity"], obs["summary"], 
            json.dumps(obs["data"]), obs["severity"] == "critical"
            )
            
    logger.info("✅ Clinical Observations seeded.")
    # ------------------------------------------------------------------
    # 5. SEED RESOURCES, RATINGS & PROGRESS
    # ------------------------------------------------------------------
    resources_data = [
        {
            "title": "Understanding Clinical Trials",
            "type": "video",
            "category": "education",
            "description": "An introductory video on how clinical trials work.",
            "url": "https://example.com/video1.mp4",
            "language": "en",
            "duration": "12:30",
            "author": "VOCE Medical Team",
            "tags": ["clinical", "trials", "beginner"],
            "published_date": "2024-01-01",
            "downloads": 12,
            "rating": 4.50,
            "featured": False,
            "requires_auth": False
        },
        {
            "title": "Patient Rights in Research",
            "type": "document",
            "category": "patient_rights",
            "description": "A comprehensive guide on patient rights during clinical studies.",
            "url": "https://example.com/doc1.pdf",
            "language": "en",
            "duration": "15 pages",
            "author": "Jane Doe",
            "tags": ["rights", "ethics"],
            "published_date": "2024-02-15",
            "downloads": 45,
            "rating": 4.80,
            "featured": True,
            "requires_auth": False
        },
        {
            "title": "Oncology Toolkit 2024",
            "type": "toolkit",
            "category": "tools",
            "description": "Tools and resources for oncology practitioners.",
            "url": "https://example.com/toolkit1.zip",
            "language": "en",
            "duration": "N/A",
            "author": "Dr. Smith",
            "tags": ["oncology", "tools", "hcp"],
            "published_date": "2024-03-10",
            "downloads": 89,
            "rating": 4.20,
            "featured": True,
            "requires_auth": True
        },
        {
            "title": "Managing Diabetes Daily",
            "type": "course",
            "category": "disease_management",
            "description": "Interactive course on daily habits for managing type 2 diabetes.",
            "url": "https://example.com/course1",
            "language": "es",
            "duration": "2 hours",
            "author": "BioMed Education",
            "tags": ["diabetes", "lifestyle", "spanish"],
            "published_date": "2024-04-05",
            "downloads": 150,
            "rating": 4.60,
            "featured": False,
            "requires_auth": True
        },
        {
            "title": "Alzheimer's Early Symptoms Guide",
            "type": "document",
            "category": "education",
            "description": "Checklist and guide on recognizing early signs of Alzheimer's.",
            "url": "https://example.com/doc2.pdf",
            "language": "en",
            "duration": "10 pages",
            "author": "Neuro Sciences",
            "tags": ["neurology", "aging"],
            "published_date": "2024-05-20",
            "downloads": 200,
            "rating": 4.90,
            "featured": True,
            "requires_auth": False
        }
    ]

    resource_ids = []
    for r in resources_data:
        rid = await conn.fetchval("""
            INSERT INTO resources (
                title, type, category, description, url, language, duration, author,
                tags, published_date, downloads, rating, featured, requires_auth
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING resource_id
        """,
        r["title"], r["type"], r["category"], r["description"], r["url"], r["language"],
        r["duration"], r["author"], json.dumps(r["tags"]), datetime.strptime(r["published_date"], "%Y-%m-%d").date(),
        r["downloads"], r["rating"], r["featured"], r["requires_auth"])
        resource_ids.append(rid)

    logger.info("✅ Resources seeded.")

    # Seed Ratings & Progress (using generated users and resources)
    if user_ids and resource_ids:
        patient_id = user_ids.get("patient")
        hcp_id = user_ids.get("hcp")

        # Ratings
        ratings_data = [
            (resource_ids[0], patient_id, 4, "Good intro video."),
            (resource_ids[1], patient_id, 5, "Very detailed and helpful."),
            (resource_ids[2], hcp_id, 4, "Useful tools for the clinic."),
            (resource_ids[3], patient_id, 5, "Great manageable course!"),
            (resource_ids[4], hcp_id, 5, "Excellent guide for patients.")
        ]
        
        for resource_id, user_id, rating, review in ratings_data:
            if user_id:
                await conn.execute("""
                    INSERT INTO resource_ratings (resource_id, user_id, rating, review)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (resource_id, user_id) DO NOTHING
                """, resource_id, user_id, rating, review)

        logger.info("✅ Resource Ratings seeded.")

        # Progress
        progress_data = [
            (resource_ids[0], patient_id, 100, "12:30"),
            (resource_ids[1], patient_id, 50, "Page 7"),
            (resource_ids[2], hcp_id, 100, "Completed"),
            (resource_ids[3], patient_id, 25, "Module 1"),
            (resource_ids[4], hcp_id, 80, "Page 8")
        ]

        for resource_id, user_id, progress, last_pos in progress_data:
            if user_id:
                await conn.execute("""
                    INSERT INTO resource_progress (resource_id, user_id, progress, last_position)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (resource_id, user_id) DO UPDATE SET 
                        progress = EXCLUDED.progress, 
                        last_position = EXCLUDED.last_position,
                        updated_at = NOW()
                """, resource_id, user_id, progress, last_pos)

        logger.info("✅ Resource Progress seeded.")
        
    logger.info("🌱 Database seeding complete.")
