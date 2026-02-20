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
                try:
                    await seed_db(conn)
                except Exception as e:
                    logger.error(f"❌ Seeding failed: {e}")
                
            else:
                logger.error(f"❌ SQL files not found at {schema_path} or {indexes_path}")
        else:
            logger.info("✅ Database tables already exist.")

