from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from app.models.base_model import DBModel


class ClinicalModel(DBModel):
    # ------------------------------------------------------------------
    # 1. SEARCH & LIST TRIALS (with filters, pagination, sorting, saved flag)
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
        """
        Full‑text search + filters + pagination + saved flag.
        Handles location via trial_sites table.
        """
        # --------------------------------------------------------------
        # Parameter helpers
        # --------------------------------------------------------------
        params = []
        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        # --------------------------------------------------------------
        # Keyword (for full‑text search & ranking)
        # --------------------------------------------------------------
        if keyword and keyword.strip():
            keyword_ph = add_param(keyword.strip())
        else:
            keyword = None

        # --------------------------------------------------------------
        # User ID (saved flag)
        # --------------------------------------------------------------
        if user_id:
            user_ph = add_param(user_id)
        else:
            user_ph = None

        # --------------------------------------------------------------
        # WHERE conditions builder
        # --------------------------------------------------------------
        where_conditions = []

        # ----- Full‑text search (using title + brief_description) -----
        if keyword:
            where_conditions.append(
                f"to_tsvector('english', t.title || ' ' || COALESCE(t.brief_description, '')) @@ plainto_tsquery('english', {keyword_ph})"
            )

        # ----- Disease areas (requires many‑to‑many table; if not present, skip or adapt) -----
        if disease_areas:
            # Assumes tables: disease_areas, trial_disease_areas (not in your schema)
            # If you don't have them, comment out or remove this block.
            da_ph = add_param(disease_areas)
            where_conditions.append(
                f"""
                EXISTS (
                    SELECT 1 FROM trial_disease_areas tda
                    JOIN disease_areas da ON tda.disease_area_id = da.id
                    WHERE tda.trial_id = t.trial_id AND da.name = ANY({da_ph})
                )
                """
            )

        # ----- Phases (direct column on clinical_trials) -----
        if phases:
            phase_ph = add_param(phases)
            where_conditions.append(f"t.phase = ANY({phase_ph})")

        # ----- Statuses (direct column) -----
        if statuses:
            status_ph = add_param(statuses)
            where_conditions.append(f"t.status = ANY({status_ph})")

        # ----- Location (via trial_sites: country OR city ILIKE) -----
        if location:
            loc_ph = add_param(f"%{location}%")
            where_conditions.append(
                f"""
                EXISTS (
                    SELECT 1 FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                      AND (ts.country ILIKE {loc_ph} OR ts.city ILIKE {loc_ph})
                )
                """
            )

        # ----- Sponsor (if you have a sponsors table) -----
        if sponsor:
            sponsor_ph = add_param(f"%{sponsor}%")
            # Assumes sponsors table exists (not in your schema). If not, adjust/remove.
            where_conditions.append(
                f"""
                EXISTS (
                    SELECT 1 FROM sponsors s
                    WHERE t.sponsor_id = s.id AND s.name ILIKE {sponsor_ph}
                )
                """
            )

        # --------------------------------------------------------------
        # WHERE clause
        # --------------------------------------------------------------
        where_clause = ""
        if where_conditions:
            where_clause = "WHERE " + " AND ".join(where_conditions)

        # --------------------------------------------------------------
        # Relevance rank (only if keyword exists)
        # --------------------------------------------------------------
        if keyword:
            rank_expr = f"""
                ts_rank(
                    to_tsvector('english', t.title || ' ' || COALESCE(t.brief_description, '')),
                    plainto_tsquery('english', {keyword_ph})
                ) AS rank
            """
        else:
            rank_expr = "0::float4 AS rank"

        # --------------------------------------------------------------
        # Saved flag (using trial_saves)
        # --------------------------------------------------------------
        if user_ph:
            saved_subquery = f"EXISTS (SELECT 1 FROM trial_saves ts WHERE ts.trial_id = t.trial_id AND ts.user_id = {user_ph})"
        else:
            saved_subquery = "false"

        # --------------------------------------------------------------
        # Location string (concatenated distinct cities/countries for display)
        # --------------------------------------------------------------
        location_subquery = """
            (
                SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                FROM trial_sites ts
                WHERE ts.trial_id = t.trial_id
            ) AS location
        """

        # --------------------------------------------------------------
        # SELECT clause
        # --------------------------------------------------------------
        select_clause = f"""
            SELECT
                t.trial_id AS id,
                t.title,
                t.phase,
                t.status,
                {location_subquery},
                t.enrollment_count AS enrollment,
                {saved_subquery} AS is_saved,
                {rank_expr}
        """

        # --------------------------------------------------------------
        # FROM (include trial_sites only if needed for location filter)
        # --------------------------------------------------------------
        from_clause = "FROM clinical_trials "

        # --------------------------------------------------------------
        # ORDER BY (whitelist)
        # --------------------------------------------------------------
        if sort_by == "relevance" and keyword:
            order_by = "ORDER BY rank DESC, t.created_at DESC"
        elif sort_by == "newest":
            order_by = "ORDER BY t.created_at DESC"
        elif sort_by == "enrollment":
            order_by = "ORDER BY t.enrollment_count DESC"
        else:
            order_by = "ORDER BY t.created_at DESC"

        # --------------------------------------------------------------
        # Pagination
        # --------------------------------------------------------------
        offset = (page - 1) * limit
        offset_ph = add_param(offset)
        limit_ph = add_param(limit)
        pagination = f"OFFSET {offset_ph} LIMIT {limit_ph}"

        # --------------------------------------------------------------
        # Execute main query
        # --------------------------------------------------------------
        main_query = f"""
            {select_clause}
            {from_clause}
            {where_clause}
            {order_by}
            {pagination}
        """
        records = await self.conn.fetch(main_query, *params)
        items = self._records_to_list(records)

        # --------------------------------------------------------------
        # COUNT query (same filters, no pagination)
        # --------------------------------------------------------------
        count_params = []
        def add_count_param(value: Any) -> str:
            count_params.append(value)
            return f"${len(count_params)}"

        count_conditions = []
        if keyword:
            kw_ph = add_count_param(keyword)
            count_conditions.append(
                f"to_tsvector('english', t.title || ' ' || COALESCE(t.brief_description, '')) @@ plainto_tsquery('english', {kw_ph})"
            )
        if disease_areas:
            da_ph = add_count_param(disease_areas)
            count_conditions.append(
                f"EXISTS (SELECT 1 FROM trial_disease_areas tda JOIN disease_areas da ON tda.disease_area_id = da.id WHERE tda.trial_id = t.trial_id AND da.name = ANY({da_ph}))"
            )
        if phases:
            ph_ph = add_count_param(phases)
            count_conditions.append(f"t.phase = ANY({ph_ph})")
        if statuses:
            st_ph = add_count_param(statuses)
            count_conditions.append(f"t.status = ANY({st_ph})")
        if location:
            loc_ph = add_count_param(f"%{location}%")
            count_conditions.append(
                f"EXISTS (SELECT 1 FROM trial_sites ts WHERE ts.trial_id = t.trial_id AND (ts.country ILIKE {loc_ph} OR ts.city ILIKE {loc_ph}))"
            )
        if sponsor:
            sp_ph = add_count_param(f"%{sponsor}%")
            count_conditions.append(
                f"EXISTS (SELECT 1 FROM sponsors s WHERE t.sponsor_id = s.id AND s.name ILIKE {sp_ph})"
            )

        count_where = ""
        if count_conditions:
            count_where = "WHERE " + " AND ".join(count_conditions)

        count_query = f"""
            SELECT COUNT(DISTINCT t.trial_id)
            FROM clinical_trials t
            {count_where}
        """
        total = await self.conn.fetchval(count_query, *count_params) or 0

        # --------------------------------------------------------------
        # Pagination metadata
        # --------------------------------------------------------------
        pages = (total + limit - 1) // limit if limit > 0 else 0

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": pages,
        }

    # ------------------------------------------------------------------
    # 2. GET TRIAL BY ID (full details, including sites, saves not needed)
    # ------------------------------------------------------------------
    async def get_trial_by_id(self, trial_id: str) -> Optional[Dict[str, Any]]:
        """Fetch complete trial with all related data in one query."""
        query = """
            SELECT
                t.trial_id AS id,
                t.nct_id,
                t.title,
                t.brief_description,
                t.detailed_description,
                t.objectives,
                t.phase,
                t.status,
                t.enrollment_target,
                t.enrollment_current,
                t.start_date,
                t.completion_date,
                t.created_at,
                t.updated_at,
                t.metadata,
                t.safety_info,
                -- Sponsor (if table exists)
                CASE WHEN s.id IS NOT NULL THEN
                    jsonb_build_object(
                        'id', s.id,
                        'name', s.name,
                        'contact_email', s.contact_email,
                        'website', s.website
                    )
                ELSE NULL END AS sponsor,
                -- Disease areas (if tables exist)
                COALESCE(
                    (SELECT jsonb_agg(jsonb_build_object('id', da.id, 'name', da.name))
                     FROM trial_disease_areas tda
                     JOIN disease_areas da ON tda.disease_area_id = da.id
                     WHERE tda.trial_id = t.trial_id),
                    '[]'::jsonb
                ) AS disease_areas,
                -- Eligibility criteria (if columns exist)
                jsonb_build_object(
                    'inclusion', t.eligibility_inclusion,
                    'exclusion', t.eligibility_exclusion,
                    'min_age', t.eligibility_min_age,
                    'max_age', t.eligibility_max_age,
                    'gender', t.eligibility_gender
                ) AS eligibility,
                -- Trial sites (from trial_sites table)
                COALESCE(
                    (SELECT jsonb_agg(jsonb_build_object(
                        'id', ts.site_id,
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
                -- Resources (if table exists)
                COALESCE(
                    (SELECT jsonb_agg(jsonb_build_object(
                        'id', tr.id,
                        'title', tr.title,
                        'file_url', tr.file_url,
                        'type', tr.resource_type,
                        'uploaded_at', tr.uploaded_at
                    ))
                     FROM trial_resources tr
                     WHERE tr.trial_id = t.trial_id),
                    '[]'::jsonb
                ) AS resources,
                -- Concatenated location for display
                (
                    SELECT string_agg(DISTINCT ts.city || ', ' || ts.country, '; ')
                    FROM trial_sites ts
                    WHERE ts.trial_id = t.trial_id
                ) AS location
            FROM clinical_trials t
            LEFT JOIN sponsors s ON t.sponsor_id = s.id
            WHERE t.trial_id = $1
        """
        record = await self.conn.fetchrow(query, trial_id)
        return self._record_to_dict(record) if record else None

    # ------------------------------------------------------------------
    # 3. SAVE TRIAL (bookmark)
    # ------------------------------------------------------------------
    async def save_trial(self, user_id: str, trial_id: str, notes: Optional[str] = None) -> bool:
        """Add a trial to user's saved list. Returns True if new save, False if already saved."""
        query = """
            INSERT INTO trial_saves (user_id, trial_id, notes, saved_at)
            VALUES ($1, $2, $3, NOW())
            ON CONFLICT (user_id, trial_id) DO NOTHING
            RETURNING 1
        """
        result = await self.conn.fetchval(query, user_id, trial_id, notes)
        return bool(result)

    # ------------------------------------------------------------------
    # 4. UNSAVE TRIAL
    # ------------------------------------------------------------------
    async def unsave_trial(self, user_id: str, trial_id: str) -> bool:
        """Remove a trial from user's saved list. Returns True if deleted, False if not found."""
        query = """
            DELETE FROM trial_saves
            WHERE user_id = $1 AND trial_id = $2
            RETURNING 1
        """
        result = await self.conn.fetchval(query, user_id, trial_id)
        return bool(result)

    # ------------------------------------------------------------------
    # 5. GET USER'S SAVED TRIALS (with full details + timestamp)
    # ------------------------------------------------------------------
    async def get_saved_trials(self, user_id: str) -> List[Dict[str, Any]]:
        """Retrieve all trials saved by the user, including save timestamp."""
        query = """
            SELECT
                t.trial_id AS id,
                t.title,
                t.phase,
                t.status,
                t.enrollment_count AS enrollment,
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
    # 6. EXPRESS INTEREST / CONTACT TRIAL
    # ------------------------------------------------------------------
    async def express_interest(
        self,
        user_id: str,
        trial_id: str,
        message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Log a user's interest in a trial.
        Returns the created lead record (you may have a leads table; otherwise log to analytics).
        """
        # If you have a leads table, insert here. Otherwise, log to a separate analytics store.
        # For this example, we'll just return a confirmation.
        # You can also increment an interest counter in clinical_trials if you add that column.
        try:
            # Optionally update a counter on the trial
            await self.conn.execute(
                "UPDATE clinical_trials SET metadata = jsonb_set(COALESCE(metadata, '{}'), '{interest_count}', (COALESCE(metadata->>'interest_count', '0')::int + 1)::text::jsonb) WHERE trial_id = $1",
                trial_id,
            )
        except:
            pass  # column may not exist; fail silently

        return {
            "lead_id": None,  # Not stored in given schema; could be added later
            "trial_id": trial_id,
            "user_id": user_id,
            "created_at": datetime.now(timezone.utc),
        }

    # ------------------------------------------------------------------
    # 7. CREATE TRIAL ALERT
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
        """Create a new alert subscription."""
        query = """
            INSERT INTO trial_alerts (
                user_id, trial_id, disease_area, location, phase,
                filter_criteria, alert_frequency, is_active, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, TRUE, NOW(), NOW())
            RETURNING alert_id, created_at
        """
        record = await self.conn.fetchrow(
            query,
            user_id,
            trial_id,
            disease_area,
            location,
            phase,
            filter_criteria or {},
            alert_frequency,
        )
        return self._record_to_dict(record)

    # ------------------------------------------------------------------
    # 8. DELETE TRIAL ALERT
    # ------------------------------------------------------------------
    async def delete_trial_alert(self, alert_id: str, user_id: str) -> bool:
        """Delete an alert only if it belongs to the user."""
        query = """
            DELETE FROM trial_alerts
            WHERE alert_id = $1 AND user_id = $2
            RETURNING 1
        """
        result = await self.conn.fetchval(query, alert_id, user_id)
        return bool(result)

    # ------------------------------------------------------------------
    # 9. GET USER'S TRIAL ALERTS
    # ------------------------------------------------------------------
    async def get_my_alerts(self, user_id: str) -> List[Dict[str, Any]]:
        """List all alert subscriptions for the current user."""
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
        records = await self.conn.fetch(query, user_id)
        return self._records_to_list(records)