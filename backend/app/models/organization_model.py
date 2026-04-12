from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
import json
import asyncpg
from pydantic import ValidationError

from app.models.base_model import DBModel
from app.schemas.organization import (
    OrganizationResponse,
    OrganizationDetailResponse,
    JoinOrganizationResponse,
    WorkingGroupResponse,
    OrganizationMemberResponse,
)

class OrganizationModel(DBModel):
    async def list_organizations(
        self,
        page: Optional[int] = 1,
        limit: Optional[int] = 20,
        org_type: Optional[str] = None,
        country: Optional[str] = None
    ) -> Dict[str, Any]:
        where_clauses = []
        params = []
        
        # Dynamic Filtering
        if org_type:
            params.append(org_type)
            where_clauses.append(f"org_type = ${len(params)}")
            
        if country:
            params.append(country)
            where_clauses.append(f"country = ${len(params)}")
            
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        pagination_str = ""
        if limit is not None and limit > 0:
            offset = (page - 1) * limit
            params.extend([limit, offset])
            pagination_str = f"LIMIT ${len(params) - 1} OFFSET ${len(params)}"
            
        query = f"""
            SELECT 
                org_id, org_name, org_type, country, description, 
                website, membership_status, contact_email, logo, member_count, joined_date
            FROM organizations
            {where_str}
            ORDER BY org_name ASC
            {pagination_str}
        """
        
        count_params = params[:-2] if pagination_str else params
        count_query = f"SELECT count(*) FROM organizations {where_str}"
        
        rows = await self.conn.fetch(query, *params)
        total = await self.conn.fetchval(count_query, *count_params)
        
        return {
            "data": [dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": page if limit else 1,
                "limit": limit if limit else total
            }
        }

    async def get_organization_details(self, org_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT 
                org_id, org_name, org_type, country, description, 
                website, membership_status, contact_email, logo, member_count, joined_date
            FROM organizations
            WHERE org_id = $1
        """
        row = await self.conn.fetchrow(query, org_id)
        if not row:
            return None
        
        org_dict = dict(row)
        
        # Get members (approved only)
        members_query = """
            SELECT om.id, om.user_id, om.role, om.status, om.joined_at, u.display_name as user_name, u.email as user_email
            FROM organization_members om
            JOIN users u ON om.user_id = u.id
            WHERE om.org_id = $1 AND om.status = 'approved'
        """
        members_rows = await self.conn.fetch(members_query, org_id)
        org_dict["members"] = [dict(m) for m in members_rows]
        
        # Get working groups
        groups_query = """
            SELECT group_id, name, type, privacy_level, member_count, is_active, description, organization_id
            FROM working_groups
            WHERE organization_id = $1
        """
        groups_rows = await self.conn.fetch(groups_query, org_id)
        org_dict["working_groups"] = [dict(g) for g in groups_rows]
        
        return org_dict

    async def join_organization(self, org_id: str, user_id: str) -> Dict[str, str]:
        # Check user is verified
        user_query = "SELECT is_verified FROM users WHERE id = $1"
        verified = await self.conn.fetchval(user_query, user_id)
        
        if verified is None:
            raise ValueError("User not found")
            
        if not verified:
            raise PermissionError("User is not verified")

        org_check_query = "SELECT org_id FROM organizations WHERE org_id = $1"
        org_exists = await self.conn.fetchval(org_check_query, org_id)
        if not org_exists:
            raise ValueError("Organization not found")
        
        # Check for duplicates
        check_query = "SELECT status FROM organization_members WHERE org_id = $1 AND user_id = $2"
        existing = await self.conn.fetchrow(check_query, org_id, user_id)
        if existing:
            raise ValueError(f"Membership request already exists with status: {existing['status']}")
            
        insert_query = """
            INSERT INTO organization_members (id, org_id, user_id, role, status)
            VALUES (gen_random_uuid(), $1, $2, 'member', 'pending')
        """
        await self.conn.execute(insert_query, org_id, user_id)
        
        return {
            "status": "pending_approval",
            "message": "Your request has been sent to the organization admin."
        }

    async def decide_organization_join(self, org_id: str, user_id: str, action: str) -> Dict[str, str]:
        # action is accept or refuse
        new_status = 'approved' if action in ('accept', 'approved') else 'rejected'
        
        update_query = """
            UPDATE organization_members
            SET status = $1, updated_at = NOW()
            WHERE org_id = $2 AND user_id = $3 AND status = 'pending'
            RETURNING id
        """
        result = await self.conn.fetchval(update_query, new_status, org_id, user_id)
        
        if not result:
            raise ValueError("No pending join request found for this user in this organization")
            
        if new_status == 'approved':
            # update member count
            count_update = """
                UPDATE organizations
                SET member_count = member_count + 1, updated_at = NOW()
                WHERE org_id = $1
            """
            await self.conn.execute(count_update, org_id)
            
        return {
            "status": new_status,
            "message": f"Organization request {new_status}"
        }

    async def get_organization_requests(
        self, 
        org_id: str, 
        status_filter: Optional[str] = None, 
        limit: Optional[int] = None, 
        page: Optional[int] = 1
    ) -> Dict[str, Any]:
        where_clauses = ["om.org_id = $1"]
        params = [org_id]
        
        if status_filter:
            params.append(status_filter)
            where_clauses.append(f"om.status = ${len(params)}")
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        
        pagination_str = ""
        if limit is not None and limit > 0:
            offset = (page - 1) * limit
            params.extend([limit, offset])
            pagination_str = f"LIMIT ${len(params)-1} OFFSET ${len(params)}"
            
        count_params = params[:len(params)-2] if pagination_str else params
        count_query = f"SELECT count(*) FROM organization_members om {where_str}"
        total = await self.conn.fetchval(count_query, *count_params)
            
        query = f"""
            SELECT om.id, om.user_id, om.role, om.status, om.joined_at, u.display_name as user_name, u.email as user_email
            FROM organization_members om
            JOIN users u ON om.user_id = u.id
            {where_str}
            ORDER BY om.joined_at DESC
            {pagination_str}
        """
        rows = await self.conn.fetch(query, *params)
        
        return {
            "data": [dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": page if limit else 1,
                "limit": limit if limit else total
            }
        }


    async def get_working_group_details(self, group_id: str) -> Optional[Dict[str, Any]]:
        query = """
            SELECT 
                group_id, name, type, privacy_level, member_count, is_active, description, organization_id
            FROM working_groups
            WHERE group_id = $1
        """
        row = await self.conn.fetchrow(query, group_id)
        if not row:
            return None
        
        group_dict = dict(row)
        
        # Get members (approved only)
        members_query = """
            SELECT wgm.id, wgm.user_id, wgm.role, wgm.status, wgm.joined_at, u.display_name as user_name, u.email as user_email
            FROM working_group_members wgm
            JOIN users u ON wgm.user_id = u.id
            WHERE wgm.group_id = $1 AND wgm.status = 'approved'
        """
        members_rows = await self.conn.fetch(members_query, group_id)
        group_dict["members"] = [dict(m) for m in members_rows]
        
        return group_dict

    async def list_working_groups(
        self,
        page: Optional[int] = 1,
        limit: Optional[int] = 20,
        org_id: Optional[str] = None,
        group_type: Optional[str] = None,
        public_only: bool = False
    ) -> Dict[str, Any]:
        where_clauses = []
        params = []
        
        if org_id:
            params.append(org_id)
            where_clauses.append(f"organization_id = ${len(params)}")
        if group_type:
            params.append(group_type)
            where_clauses.append(f"type = ${len(params)}")
        if public_only:
            where_clauses.append("privacy_level = 'public'")
            
        where_str = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        pagination_str = ""
        if limit is not None and limit > 0:
            offset = (page - 1) * limit
            params.extend([limit, offset])
            pagination_str = f"LIMIT ${len(params)-1} OFFSET ${len(params)}"

        query = f"""
            SELECT 
                group_id, name, type, privacy_level, member_count, is_active, description, organization_id
            FROM working_groups
            {where_str}
            ORDER BY name ASC
            {pagination_str}
        """
        
        count_params = params[:len(params)-2] if pagination_str else params
        count_query = f"SELECT count(*) FROM working_groups {where_str}"
        
        rows = await self.conn.fetch(query, *params)
        total = await self.conn.fetchval(count_query, *count_params)
        
        return {
            "data": [dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": page if limit else 1,
                "limit": limit if limit else total
            }
        }
    
    async def join_working_group(self, group_id: str, user_id: str) -> Dict[str, str]:
        # Check user exists
        user_query = "SELECT id FROM users WHERE id = $1"
        exists = await self.conn.fetchval(user_query, user_id)
        if not exists:
            raise ValueError("User not found")

        # Get privacy level
        group_query = "SELECT privacy_level FROM working_groups WHERE group_id = $1"
        privacy_level = await self.conn.fetchval(group_query, group_id)
        if not privacy_level:
            raise ValueError("Working group not found")
            
        status = 'approved' if privacy_level == 'public' else 'pending'

        # Check for duplicates
        check_query = "SELECT status FROM working_group_members WHERE group_id = $1 AND user_id = $2"
        existing = await self.conn.fetchrow(check_query, group_id, user_id)
        if existing:
            raise ValueError(f"Membership request already exists with status: {existing['status']}")
            
        insert_query = """
            INSERT INTO working_group_members (id, group_id, user_id, role, status)
            VALUES (gen_random_uuid(), $1, $2, 'member', $3)
        """
        await self.conn.execute(insert_query, group_id, user_id, status)
        
        if status == 'approved':
            # update member count
            count_update = """
                UPDATE working_groups
                SET member_count = member_count + 1, updated_at = NOW()
                WHERE group_id = $1
            """
            await self.conn.execute(count_update, group_id)
            
        msg = "Auto-approved since group is public" if status == 'approved' else "Request sent to admin"
        
        return {
            "status": status,
            "message": msg
        }

    async def decide_working_group_join(self, group_id: str, user_id: str, action: str) -> Dict[str, str]:
        new_status = 'approved' if action in ('accept', 'approved') else 'rejected'
        
        update_query = """
            UPDATE working_group_members
            SET status = $1
            WHERE group_id = $2 AND user_id = $3 AND status = 'pending'
            RETURNING id
        """
        result = await self.conn.fetchval(update_query, new_status, group_id, user_id)
        
        if not result:
            raise ValueError("No pending join request found for this user in this working group")
            
        if new_status == 'approved':
            # update member count
            count_update = """
                UPDATE working_groups
                SET member_count = member_count + 1, updated_at = NOW()
                WHERE group_id = $1
            """
            await self.conn.execute(count_update, group_id)
            
        return {
            "status": new_status,
            "message": f"Working group request {new_status}"
        }

    async def get_working_group_requests(
        self, 
        group_id: str, 
        status_filter: Optional[str] = None, 
        limit: Optional[int] = None, 
        page: Optional[int] = 1
    ) -> Dict[str, Any]:
        where_clauses = ["wgm.group_id = $1"]
        params = [group_id]
        
        if status_filter:
            params.append(status_filter)
            where_clauses.append(f"wgm.status = ${len(params)}")
            
        where_str = f"WHERE {' AND '.join(where_clauses)}"
        
        pagination_str = ""
        if limit is not None and limit > 0:
            offset = (page - 1) * limit
            params.extend([limit, offset])
            pagination_str = f"LIMIT ${len(params)-1} OFFSET ${len(params)}"
            
        count_params = params[:len(params)-2] if pagination_str else params
        count_query = f"SELECT count(*) FROM working_group_members wgm {where_str}"
        total = await self.conn.fetchval(count_query, *count_params)
            
        query = f"""
            SELECT wgm.id, wgm.user_id, wgm.role, wgm.status, wgm.joined_at, u.display_name as user_name, u.email as user_email
            FROM working_group_members wgm
            JOIN users u ON wgm.user_id = u.id
            {where_str}
            ORDER BY wgm.joined_at DESC
            {pagination_str}
        """
        rows = await self.conn.fetch(query, *params)
        
        return {
            "data": [dict(r) for r in rows],
            "meta": {
                "total": total,
                "page": page if limit else 1,
                "limit": limit if limit else total
            }
        }
