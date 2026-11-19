from typing import Optional, Dict, Any, List
from app.models.base_model import DBModel
import json

class DoctorModel(DBModel):
    async def create_verification(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.conn.transaction():
            query = """
                INSERT INTO doctor_verifications (
                    user_id, license_number, institution, country, specialization,
                    document_url, issuing_region, expiration_date,
                    status, created_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, 'pending', NOW())
                RETURNING *
            """
            row = await self.conn.fetchrow(
                query,
                user_id,
                data['license_number'],
                data['institution'],
                data['country'],
                data['specialization'],
                data.get('document_url'),
                data.get('issuing_region'),
                data.get('expiration_date'),
            )
            
            # Update user jsonb status
            await self.conn.execute(
                """
                UPDATE users 
                SET verification = jsonb_set(COALESCE(verification, '{}'::jsonb), '{status}', '"pending"')
                WHERE id = $1
                """,
                user_id
            )
            return dict(row)

    async def get_verification(self, verification_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM doctor_verifications WHERE verification_id = $1"
        row = await self.conn.fetchrow(query, verification_id)
        return dict(row) if row else None

    async def get_verification_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        query = "SELECT * FROM doctor_verifications WHERE user_id = $1 ORDER BY created_at DESC LIMIT 1"
        row = await self.conn.fetchrow(query, user_id)
        return dict(row) if row else None

    async def update_pending_verification(self, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Change the details of the user's pending request. Returns None if there is none."""
        allowed = ("license_number", "institution", "country", "specialization",
                   "document_url", "issuing_region", "expiration_date")
        fields = {k: v for k, v in updates.items() if k in allowed}
        if not fields:
            return None
        set_clause = ", ".join(f"{name} = ${i + 2}" for i, name in enumerate(fields))
        row = await self.conn.fetchrow(
            f"""
            UPDATE doctor_verifications SET {set_clause}
            WHERE verification_id = (
                SELECT verification_id FROM doctor_verifications
                WHERE user_id = $1 AND status = 'pending'
                ORDER BY created_at DESC LIMIT 1
            )
            RETURNING *
            """,
            user_id, *fields.values(),
        )
        return dict(row) if row else None

    async def withdraw_pending_verification(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Delete the user's pending request. Returns the deleted row, or None if there is none."""
        async with self.conn.transaction():
            row = await self.conn.fetchrow(
                """
                DELETE FROM doctor_verifications
                WHERE user_id = $1 AND status = 'pending'
                RETURNING *
                """,
                user_id,
            )
            if not row:
                return None
            await self.conn.execute(
                """
                UPDATE users
                SET verification = jsonb_set(COALESCE(verification, '{}'::jsonb), '{status}', '"not_submitted"')
                WHERE id = $1
                """,
                user_id,
            )
            return dict(row)

    async def get_pending_verifications(self) -> List[Dict[str, Any]]:
        query = """
            SELECT v.*, u.email, u.display_name 
            FROM doctor_verifications v
            JOIN users u ON v.user_id = u.id
            WHERE v.status = 'pending'
            ORDER BY v.created_at ASC
        """
        rows = await self.conn.fetch(query)
        return [dict(r) for r in rows]

    async def review_verification(self, verification_id: str, admin_id: str, status: str, reason: Optional[str] = None) -> Optional[Dict[str, Any]]:
        async with self.conn.transaction():
            query = """
                UPDATE doctor_verifications
                SET status = $1, reviewed_by = $2, reviewed_at = NOW(), rejection_reason = $3
                WHERE verification_id = $4
                RETURNING *
            """
            row = await self.conn.fetchrow(query, status, admin_id, reason, verification_id)
            if not row:
                return None
            
            user_id = row['user_id']
            if status == 'approved':
                await self.conn.execute(
                    """
                    UPDATE users
                    SET is_verified = TRUE,
                        user_type = 'hcp',
                        verification = jsonb_set(COALESCE(verification, '{}'::jsonb), '{status}', '"approved"'::jsonb)
                    WHERE id = $1
                    """,
                    user_id
                )
                # Update profile
                await self.conn.execute(
                    """
                    INSERT INTO user_profiles (user_id, specialization, license_number)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET specialization = EXCLUDED.specialization, license_number = EXCLUDED.license_number
                    """,
                    user_id, row['specialization'], row['license_number']
                )
            elif status == 'rejected':
                 await self.conn.execute(
                    """
                    UPDATE users 
                    SET verification = jsonb_set(COALESCE(verification, '{}'::jsonb), '{status}', '"rejected"'::jsonb)
                    WHERE id = $1
                    """,
                    user_id
                )
            return dict(row)
