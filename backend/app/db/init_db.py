import os
import logging
from app.db.postgres import PostgresDB
from app.db.seed import seed_db

logger = logging.getLogger(__name__)

async def init_db():
    """
    Checks if the database is initialized. 
    If not, applies schema and indexes.
    """
    pool = PostgresDB.get_pool()
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    
    async with pool.acquire() as conn:
        # Run all idempotent migrations from app/db/migrations/
        migrations_dir = os.path.join(base_dir, "app", "db", "migrations")
        if os.path.exists(migrations_dir):
            migration_files = sorted([f for f in os.listdir(migrations_dir) if f.endswith(".sql")])
            for mig_file in migration_files:
                with open(os.path.join(migrations_dir, mig_file), "r", encoding="utf-8") as f:
                    mig_sql = f.read()
                try:
                    await conn.execute(mig_sql)
                    logger.info(f"✅ Migration applied: {mig_file}")
                except Exception as e:
                    logger.error(f"❌ Migration {mig_file} failed: {e}")

        table_exists = await conn.fetchval(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')"
        )
        if not table_exists:
            logger.info("📦 Database tables not found. Initializing...")
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
                try:
                    await seed_db(conn)
                except Exception as e:
                    logger.error(f"❌ Seeding failed: {e}")  
            else:
                logger.error(f"❌ SQL files not found at {schema_path} or {indexes_path}")
        else:
            logger.info("✅ Database tables already exist.")

