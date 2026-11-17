"""
Make an existing account a platform admin.

Public signup cannot create admins, so an admin first signs up normally
(for example as a patient), then someone with server access runs, from the backend folder:

    python -m app.scripts.make_admin someone@example.com
"""
import asyncio
import sys

from app.db.postgres import PostgresDB


async def make_admin(conn, email: str) -> bool:
    """Give the account with this email the admin role. Returns False if no such active account."""
    user_id = await conn.fetchval("""
        UPDATE users SET user_type = 'admin', updated_at = NOW()
        WHERE email = $1 AND status <> 'deleted'
        RETURNING id
    """, email)
    return user_id is not None


async def main(email: str) -> int:
    await PostgresDB.connect()
    try:
        async with PostgresDB.get_pool().acquire() as conn:
            if await make_admin(conn, email):
                print(f"{email} is now an admin. They need to log in again.")
                return 0
            print(f"No account found for {email}.")
            return 1
    finally:
        await PostgresDB.disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m app.scripts.make_admin <email>")
        sys.exit(2)
    sys.exit(asyncio.run(main(sys.argv[1].strip())))
