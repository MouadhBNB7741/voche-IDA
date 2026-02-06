from app.db.postgres import PostgresDB


# app/db/queries/users.py
async def get_user_by_email(email: str):
    query = """
        SELECT id, email, password_hash, role, is_active
        FROM users
        WHERE email = $1
    """
    # Simply await the connection passed to it
    return await PostgresDB.fetch_one(query, email)