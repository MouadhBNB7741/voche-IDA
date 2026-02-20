from typing import Optional, Dict, Any, List
from app.models.base_model import DBModel
import json

class DoctorModel(DBModel):
    async def create_verification(self, user_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        async with self.conn.transaction():
            query = """
                INSERT INTO doctor_verifications (
                    user_id, license_number, institution, country, specialization,
                    status, created_at
                )
                VALUES ($1, $2, $3, $4, $5, 'pending', NOW())
                RETURNING *
            """
            row = await self.conn.fetchrow(
                query,
                user_id,
                data['license_number'],
                data['institution'],
                data['country'],
                data['specialization'],
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
