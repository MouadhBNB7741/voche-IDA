import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.base_model import DBModel


class ClinicalModel(DBModel):
    """
    Model for Clinical Trials domain.
    Handles trials, saves, alerts, and interest expressions.
    Strict adhesion to DB schema: clinical_trials, trial_sites, trial_saves, trial_alerts.
    """

    # ------------------------------------------------------------------
    # 1. SEARCH & LIST TRIALS
    # ------------------------------------------------------------------
    async def search_trials(
        self,
        *,
        keyword: Optional[str] = None,
        disease_areas: Optional[List[str]] = None,
        phases: Optional[List[str]] = None,
        statuses: Optional[List[str]] = None,
        location: Optional[str] = None,
        sponsor: Optional[str] = None,
        page: int = 1,
        limit: int = 20,
        sort_by: str = "relevance",
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        params = []
        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        keyword_val = keyword.strip() if keyword and keyword.strip() else None
        where_conditions = []

        if keyword_val:
            kw_ph = add_param(keyword_val)
            where_conditions.append(
                f"to_tsvector('english', t.title || ' ' || COALESCE(t.summary, '')) @@ plainto_tsquery('english', {kw_ph})"
            )

        if disease_areas:
            da_ph = add_param(disease_areas)
            where_conditions.append(f"t.disease_area = ANY({da_ph})")

        if phases:
            ph_ph = add_param(phases)
            where_conditions.append(f"t.phase = ANY({ph_ph})")

        if statuses:
            st_ph = add_param(statuses)
            where_conditions.append(f"t.status = ANY({st_ph})")

        if location:
            loc_val = f"%{location}%"
            loc_ph = add_param(loc_val)
            where_conditions.append(
                f"""EXISTS (
                    SELECT 1 FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                    AND (ts.country ILIKE {loc_ph} OR ts.city ILIKE {loc_ph})
                )"""
            )

        if sponsor:
            sp_ph = add_param(f"%{sponsor}%")
            where_conditions.append(f"t.sponsor ILIKE {sp_ph}")

        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""

        if user_id:
            user_ph = add_param(user_id)
            is_saved_expr = f"""
                EXISTS (
                    SELECT 1 FROM trial_saves ts 
                    WHERE ts.trial_id = t.trial_id AND ts.user_id = {user_ph}
                )
            """
        else:
            is_saved_expr = "false"

        if keyword_val:
            rank_expr = f"""
                ts_rank(
                    to_tsvector('english', t.title || ' ' || COALESCE(t.summary, '')),
                    plainto_tsquery('english', ${params.index(keyword_val) + 1})
                )
            """
            rank_col = f"{rank_expr} AS rank"
        else:
            rank_col = "0::float4 AS rank"

        if sort_by == "relevance" and keyword_val:
            order_by = "ORDER BY rank DESC, t.created_at DESC"
        elif sort_by == "newest":
            order_by = "ORDER BY t.created_at DESC"
        elif sort_by == "enrollment":
            order_by = "ORDER BY t.enrollment DESC NULLS LAST"
        else:
            order_by = "ORDER BY t.created_at DESC"

        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)

        location_agg = """
            (
                SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                FROM trial_sites ts
                WHERE ts.trial_id = t.trial_id
            ) AS location
        """

        # Aliasing trial_id AS id
        query = f"""
            SELECT
                t.trial_id AS id,
                t.title,
                t.phase,
                t.status,
                t.disease_area,
                {location_agg},
                t.enrollment AS enrollment_count,
                {is_saved_expr} AS is_saved,
                {rank_col}
            FROM clinical_trials t
            {where_clause}
            {order_by}
            OFFSET {offset_ph} LIMIT {limit_ph}
        """

        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

        # Count Query Logic
        count_params = []
        def add_c_param(value):
            count_params.append(value)
            return f"${len(count_params)}"
        
        c_conditions = []
        if keyword_val:
            kp = add_c_param(keyword_val)
            c_conditions.append(f"to_tsvector('english', t.title || ' ' || COALESCE(t.summary, '')) @@ plainto_tsquery('english', {kp})")
        if disease_areas:
            dp = add_c_param(disease_areas)
            c_conditions.append(f"t.disease_area = ANY({dp})")
        if phases:
            pp = add_c_param(phases)
            c_conditions.append(f"t.phase = ANY({pp})")
        if statuses:
            sp = add_c_param(statuses)
            c_conditions.append(f"t.status = ANY({sp})")
        if location:
            lp = add_c_param(f"%{location}%")
            c_conditions.append(f"EXISTS (SELECT 1 FROM trial_sites ts WHERE ts.trial_id = t.trial_id AND (ts.country ILIKE {lp} OR ts.city ILIKE {lp}))")
        if sponsor:
            spp = add_c_param(f"%{sponsor}%")
            c_conditions.append(f"t.sponsor ILIKE {spp}")
            
        c_where = "WHERE " + " AND ".join(c_conditions) if c_conditions else ""
        
        c_sql = f"SELECT COUNT(*) FROM clinical_trials t {c_where}"
        total = await self.conn.fetchval(c_sql, *count_params) or 0
        
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    # ------------------------------------------------------------------
    # 2. GET TRIAL BY ID
    # ------------------------------------------------------------------
    async def get_trial_by_id(self, trial_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        params = [trial_id]
        if user_id:
            params.append(user_id)
            saved_expr = "EXISTS (SELECT 1 FROM trial_saves ts WHERE ts.trial_id = t.trial_id AND ts.user_id = $2)"
        else:
            saved_expr = "false"

        # Aliasing trial_id AS id
        query = f"""
            SELECT
                t.trial_id AS id,
                t.nct_id,
                t.title,
                t.summary,
                t.disease_area,
                t.phase,
                t.status,
                t.sponsor,
                t.countries, 
                t.eligibility_criteria,
                t.enrollment AS enrollment_count,
                t.max_enrollment,
                t.start_date,
                t.estimated_completion,
                t.contact,
                t.metadata,
                t.created_at,
                t.last_updated AS updated_at,
                {saved_expr} AS is_saved,
                COALESCE(
                    (SELECT jsonb_agg(jsonb_build_object(
                        'site_id', ts.site_id,
                        'site_name', ts.site_name,
                        'country', ts.country,
                        'city', ts.city,
                        'address', ts.address,
                        'contact_email', ts.contact_email,
                        'contact_phone', ts.contact_phone,
                        'is_recruiting', ts.is_recruiting
                    ))
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id),
                    '[]'::jsonb
                ) AS sites,
                (
                    SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                ) AS location
            FROM clinical_trials t
            WHERE t.trial_id = $1
        """
        record = await self.conn.fetchrow(query, *params)
        if not record:
            return None
        
        data = dict(record)
        
        # Deserialize JSON fields if they are strings
        for field in ['sites', 'countries', 'metadata', 'objectives', 'safety_info']:
            if field in data and isinstance(data[field], str):
                try:
                    data[field] = json.loads(data[field])
                except Exception:
                    # Fallback to empty default or raw
                    if field == 'sites': data[field] = []
                    elif field == 'countries': data[field] = []
                    elif field == 'metadata': data[field] = {}
        
        # Ensure lists are lists
        if data.get('countries') is None: data['countries'] = []
        if data.get('sites') is None: data['sites'] = []
        
        return data

    # ------------------------------------------------------------------
    # 3. SAVE / UNSAVE
    # ------------------------------------------------------------------
    async def save_trial(self, user_id: str, trial_id: str, notes: Optional[str] = None) -> bool:
        query = """
            INSERT INTO trial_saves (user_id, trial_id, notes, saved_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, trial_id) DO NOTHING
            RETURNING user_id
        """
        val = await self.conn.fetchval(query, user_id, trial_id, notes)
        return bool(val)

    async def unsave_trial(self, user_id: str, trial_id: str) -> bool:
        query = """
            DELETE FROM trial_saves
            WHERE user_id = $1 AND trial_id = $2
            RETURNING 1
        """
        val = await self.conn.fetchval(query, user_id, trial_id)
        return bool(val)

    async def get_saved_trials(self, user_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT
                t.trial_id AS id,
                t.title,
                t.phase,
                t.status,
                t.enrollment AS enrollment_count,
                (
                    SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                ) AS location,
                tsave.saved_at
            FROM trial_saves tsave
            JOIN clinical_trials t ON tsave.trial_id = t.trial_id
            WHERE tsave.user_id = $1
            ORDER BY tsave.saved_at DESC
        """
        records = await self.conn.fetch(query, user_id)
        return self._records_to_list(records)

    # ------------------------------------------------------------------
    # 4. INTEREST
    # ------------------------------------------------------------------
    async def express_interest(self, user_id: str, trial_id: str, message: Optional[str]) -> Dict[str, Any]:
        await self.conn.execute(
            """
            INSERT INTO user_activity_log (user_id, action, entity_type, entity_id, metadata)
            VALUES ($1, 'express_interest', 'trial', $2, $3)
            """,
            user_id, trial_id, json.dumps({"message_length": len(message) if message else 0})
        )
        
        return {
            "trial_id": trial_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc)
        }

    # ------------------------------------------------------------------
    # 5. ALERTS
    # ------------------------------------------------------------------
    async def create_trial_alert(
        self,
        user_id: str,
        *,
        disease_area: Optional[str] = None,
        location: Optional[str] = None,
        phase: Optional[str] = None,
        filter_criteria: Optional[Dict] = None,
        alert_frequency: str = "weekly",
        trial_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        # JSON serialize filter_criteria
        query = """
            INSERT INTO trial_alerts (
                user_id, trial_id, disease_area, location, phase,
                filter_criteria, alert_frequency, is_active, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW(), NOW())
            RETURNING alert_id, created_at, updated_at, is_active, 
                      disease_area, location, phase, filter_criteria, alert_frequency
        """
        row = await self.conn.fetchrow(
            query,
            user_id,
            trial_id,
            disease_area,
            location,
            phase,
            json.dumps(filter_criteria or {}),
            alert_frequency,
        )
        data = self._record_to_dict(row)
        if isinstance(data.get("filter_criteria"), str):
            try:
                data["filter_criteria"] = json.loads(data["filter_criteria"])
            except:
                data["filter_criteria"] = {}
        return data

    async def get_my_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        query = """
            SELECT
                alert_id,
                disease_area,
                location,
                phase,
                filter_criteria,
                alert_frequency,
                is_active,
                created_at,
                updated_at
            FROM trial_alerts
            WHERE user_id = $1
            ORDER BY created_at DESC
        """
        rows = await self.conn.fetch(query, user_id)
        # Deserialize JSONB
        results = []
        for r in rows:
            d = dict(r)
            if isinstance(d.get("filter_criteria"), str):
                 try:
                     d["filter_criteria"] = json.loads(d["filter_criteria"])
                 except:
                     pass
            results.append(d)
        return results

    async def delete_trial_alert(self, alert_id: str, user_id: str) -> bool:
        query = "DELETE FROM trial_alerts WHERE alert_id = $1 AND user_id = $2 RETURNING 1"
        val = await self.conn.fetchval(query, alert_id, user_id)
        return bool(val)
        
    async def update_trial_alert(self, alert_id: str, user_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not updates:
            return None
            
        set_parts = []
        vals = [alert_id, user_id]
        
        for k, v in updates.items():
            if k == 'filter_criteria':
                vals.append(json.dumps(v))
            else:
                vals.append(v)
            set_parts.append(f"{k} = ${len(vals)}")
            
        set_parts.append("updated_at = NOW()")
        
        query = f"""
            UPDATE trial_alerts
            SET {", ".join(set_parts)}
            WHERE alert_id = $1 AND user_id = $2
            RETURNING alert_id, disease_area, location, phase, 
                      filter_criteria, alert_frequency, is_active, created_at, updated_at
        """
        row = await self.conn.fetchrow(query, *vals)
        if not row:
            return None
        data = self._record_to_dict(row)
        if isinstance(data.get("filter_criteria"), str):
            try:
                data["filter_criteria"] = json.loads(data["filter_criteria"])
            except:
                pass
        return data