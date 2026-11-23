import logging
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import date

logger = logging.getLogger(__name__)

from app.models.base_model import DBModel


def _is_empty(answer: Any) -> bool:
    return answer is None or (isinstance(answer, (str, list)) and len(answer) == 0) or (isinstance(answer, str) and not answer.strip())


def _rule_matches(rule: Dict[str, Any], answer: Any) -> bool:
    """Only the 'equals' condition is supported. A list answer matches if any item equals the value."""
    if rule.get("condition", "equals") != "equals":
        return False
    target = str(rule.get("value", "")).strip().lower()
    values = answer if isinstance(answer, list) else [answer]
    normalized = ["yes" if v is True else "no" if v is False else str(v).strip().lower() for v in values]
    return target in normalized


def answer_path(questions: List[Dict[str, Any]], answers: Dict[str, Any]) -> List[str]:
    """
    Ids of the questions a respondent actually reaches, in order. Starts at the first question;
    a matching branching rule jumps to its next_question_id, otherwise the next question follows.
    A rule pointing back to a question already on the path ends the path (no loops).
    """
    position = {str(q["question_id"]): i for i, q in enumerate(questions)}
    path, seen, i = [], set(), 0
    while i < len(questions):
        q_id = str(questions[i]["question_id"])
        if q_id in seen:
            break
        seen.add(q_id)
        path.append(q_id)
        nxt = i + 1
        answer = answers.get(q_id)
        if not _is_empty(answer):
            for rule in questions[i].get("branching_rules") or []:
                target = str(rule.get("next_question_id"))
                if target in position and _rule_matches(rule, answer):
                    nxt = position[target]
                    break
        i = nxt
    return path


def answer_error(q_type: str, options: Optional[List[Any]], answer: Any) -> Optional[str]:
    """Why an answer is invalid for its question type, or None when it is fine."""
    if q_type == "yes_no":
        return None if str(answer).lower() in ("yes", "no", "true", "false") else "requires a yes/no answer"
    if q_type in ("scale", "number"):
        if isinstance(answer, bool):
            return "requires a number"
        try:
            float(answer)
            return None
        except (ValueError, TypeError):
            return "requires a number"
    if q_type == "date":
        try:
            date.fromisoformat(str(answer))
            return None
        except ValueError:
            return "requires a date (YYYY-MM-DD)"
    if q_type == "single_choice":
        if isinstance(answer, list):
            return "allows only one option"
        return None if not options or answer in options else f"'{answer}' is not a valid option"
    if q_type == "multiple_choice" and options:
        for a in answer if isinstance(answer, list) else [answer]:
            if a not in options:
                return f"'{a}' is not a valid option"
    return None

class SurveyModel(DBModel):
    """
    Model for Surveys & Research API domain.
    """

    @staticmethod
    def _deserialize_jsonb(data: Any) -> Any:
        if isinstance(data, str):
            try:
                return json.loads(data)
            except Exception:
                return []
        return data or []

    @staticmethod
    def _to_uuid(val: Any) -> uuid.UUID:
        if isinstance(val, uuid.UUID):
            return val
        return uuid.UUID(str(val))

    async def list_surveys(
        self,
        user_id: str,
        *,
        status_filter: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List active surveys eligible for user.
        """
        params: list = [self._to_uuid(user_id)]

        def add_param(value: Any) -> str:
            params.append(value)
            return f"${len(params)}"

        conditions = [
            "(s.published_date IS NULL OR s.published_date <= CURRENT_DATE)",
            "(s.closing_date IS NULL OR s.closing_date >= CURRENT_DATE)",
            "(s.target_audience IS NULL OR jsonb_array_length(s.target_audience) = 0 OR s.target_audience ? (SELECT user_type FROM users WHERE id = $1))"
        ]

        if status_filter:
            ph = add_param(status_filter)
            conditions.append(f"s.status = {ph}")
        else:
            conditions.append("s.status = 'active'")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        count_sql = f"SELECT COUNT(*) FROM surveys s {where_clause}"
        total = await self.conn.fetchval(count_sql, *params) or 0

        pagination_clause = ""
        if page is not None and limit is not None:
            offset = (page - 1) * limit
            offset_ph = add_param(offset)
            limit_ph = add_param(limit)
            pagination_clause = f"OFFSET {offset_ph} LIMIT {limit_ph}"

        query = f"""
            SELECT 
                s.survey_id, s.title, s.description, s.estimated_time, 
                s.incentive, s.status,
                EXISTS(
                    SELECT 1 FROM survey_completions sc 
                    WHERE sc.survey_id = s.survey_id AND sc.user_id = $1
                ) as already_completed
            FROM surveys s
            {where_clause}
            ORDER BY s.created_at DESC
            {pagination_clause}
        """

        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)

        effective_limit = limit if limit else (total if total > 0 else 1)
        pages = (total + effective_limit - 1) // effective_limit if effective_limit > 0 else 0
        effective_page = page if page else 1

        return {
            "data": items,
            "meta": {
                "total": total,
                "page": effective_page,
                "limit": effective_limit,
                "pages": pages,
            },
        }

    async def get_survey_questions(self, survey_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        query_survey = """
            SELECT survey_id, title, description, consent_text, estimated_time
            FROM surveys
            WHERE survey_id = $1
        """
        record_survey = await self.conn.fetchrow(query_survey, self._to_uuid(survey_id))
        if not record_survey:
            return None

        survey_data = self._record_to_dict(record_survey)

        query_questions = """
            SELECT question_id, question_text as text, question_type as type,
                   required, options, branching_rules
            FROM survey_questions
            WHERE survey_id = $1
            ORDER BY order_position ASC
        """
        record_questions = await self.conn.fetch(query_questions, self._to_uuid(survey_id))
        questions = self._records_to_list(record_questions)

        for q in questions:
            if q.get("options"):
                q["options"] = self._deserialize_jsonb(q["options"])
            else:
                q["options"] = None
            q["branching_rules"] = self._deserialize_jsonb(q.get("branching_rules"))

        survey_data["questions"] = questions
        survey_data["draft_answers"] = None
        if user_id:
            draft = await self.conn.fetchval(
                "SELECT draft_answers FROM survey_assignments WHERE survey_id = $1 AND patient_user_id = $2 "
                "AND status IN ('pending', 'in_progress')",
                self._to_uuid(survey_id), self._to_uuid(user_id),
            )
            survey_data["draft_answers"] = json.loads(draft) if isinstance(draft, str) else draft
        return survey_data

    async def submit_survey_response(
        self,
        survey_id: str,
        user_id: str,
        responses: List[Dict[str, Any]],
        anonymous: bool
    ) -> Dict[str, Any]:
        async with self.conn.transaction():
            survey = await self.conn.fetchrow(
                "SELECT status, published_date, closing_date FROM surveys WHERE survey_id = $1", 
                self._to_uuid(survey_id)
            )
            if not survey:
                raise ValueError("Survey not found")
            
            if survey["status"] != "active":
                raise ValueError("Survey is no longer active")

            # Time Validation
            today = date.today()
            if survey["published_date"] and survey["published_date"] > today:
                raise ValueError("Survey has not been published yet")
            if survey["closing_date"] and survey["closing_date"] < today:
                raise ValueError("Survey has already closed")

            # Duplicate check via completions table
            if not anonymous:
                existing = await self.conn.fetchrow(
                    "SELECT 1 FROM survey_completions WHERE survey_id = $1 AND user_id = $2 LIMIT 1",
                    self._to_uuid(survey_id), self._to_uuid(user_id)
                )
                if existing:
                    raise ValueError("You have already submitted a response for this survey")

            record_questions = await self.conn.fetch(
                "SELECT question_id, question_type, required, options, branching_rules "
                "FROM survey_questions WHERE survey_id = $1 ORDER BY order_position",
                self._to_uuid(survey_id)
            )
            questions = [dict(q) for q in record_questions]
            for q in questions:
                q["options"] = self._deserialize_jsonb(q["options"]) if q["options"] else None
                q["branching_rules"] = self._deserialize_jsonb(q["branching_rules"])
            by_id = {str(q["question_id"]): q for q in questions}
            submitted = {str(r["question_id"]): r["answer"] for r in responses}

            for q_id in submitted:
                if q_id not in by_id:
                    raise ValueError(f"Question {q_id} does not belong to this survey")

            # Only questions on the path the respondent took count; answers to skipped questions are dropped.
            path = answer_path(questions, submitted)
            response_map = {q_id: submitted[q_id] for q_id in path if not _is_empty(submitted.get(q_id))}
            for q_id in path:
                if by_id[q_id]["required"] and q_id not in response_map:
                    raise ValueError(f"Required question {q_id} is missing an answer")
            for q_id, answer in response_map.items():
                error = answer_error(by_id[q_id]["question_type"], by_id[q_id]["options"], answer)
                if error:
                    raise ValueError(f"Question {q_id} {error}")

            actual_user_id = None if anonymous else self._to_uuid(user_id)
            completion_id = uuid.uuid4()

            # Record Completion
            await self.conn.execute("""
                INSERT INTO survey_completions (completion_id, survey_id, user_id, is_anonymous, submitted_at)
                VALUES ($1, $2, $3, $4, NOW())
            """, completion_id, self._to_uuid(survey_id), actual_user_id, anonymous)
            
            insert_query = """
                INSERT INTO survey_responses (response_id, survey_id, user_id, question_id, answer, is_anonymous, submitted_at, completion_id)
                VALUES ($1, $2, $3, $4, $5, $6, NOW(), $7)
            """
            
            inserts = []
            for r_q_id, answer in response_map.items():
                answer_json = json.dumps(answer)
                inserts.append((
                    uuid.uuid4(),
                    self._to_uuid(survey_id),
                    actual_user_id,
                    self._to_uuid(r_q_id),
                    answer_json,
                    anonymous,
                    completion_id
                ))

            await self.conn.executemany(insert_query, inserts)

            # Close the respondent's assignment (if any) and drop the saved draft.
            await self.conn.execute(
                """
                UPDATE survey_assignments
                SET status = 'completed', completed_at = NOW(), draft_answers = '{}', updated_at = NOW()
                WHERE survey_id = $1 AND patient_user_id = $2 AND status IN ('pending', 'in_progress')
                """,
                self._to_uuid(survey_id), self._to_uuid(user_id),
            )

            logger.info("Survey response submitted", extra={
                "survey_id": survey_id,
                "user_id": user_id,
                "anonymous": anonymous,
                "completion_id": str(completion_id)
            })

        return {
            "message": "Thank you for your feedback!",
            "completion_id": str(completion_id)
        }

    async def get_user_completed_surveys(
        self,
        user_id: str,
        page: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        List surveys completed by the user.
        """
        user_uuid = self._to_uuid(user_id)
        
        count_sql = "SELECT COUNT(*) FROM survey_completions WHERE user_id = $1 AND is_anonymous = FALSE"
        total = await self.conn.fetchval(count_sql, user_uuid) or 0
        
        pagination_clause = ""
        params = [user_uuid]
        if page and limit:
            offset = (page - 1) * limit
            pagination_clause = f"OFFSET $2 LIMIT $3"
            params.extend([offset, limit])
            
        query = f"""
            SELECT sc.completion_id, sc.survey_id, s.title, sc.submitted_at
            FROM survey_completions sc
            JOIN surveys s ON sc.survey_id = s.survey_id
            WHERE sc.user_id = $1 AND sc.is_anonymous = FALSE
            ORDER BY sc.submitted_at DESC
            {pagination_clause}
        """
        records = await self.conn.fetch(query, *params)
        items = self._records_to_list(records)
        
        effective_limit = limit if limit else (total if total > 0 else 1)
        pages = (total + effective_limit - 1) // effective_limit if effective_limit > 0 else 0
        effective_page = page if page else 1

        return {
            "data": items,
            "meta": {
                "total": total,
                "page": effective_page,
                "limit": effective_limit,
                "pages": pages,
            },
        }

    async def get_completion_details(self, completion_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get full answers for a specific completion.
        """
        comp_uuid = self._to_uuid(completion_id)
        user_uuid = self._to_uuid(user_id)
        
        # Verify ownership and not anonymous
        comp = await self.conn.fetchrow("""
            SELECT completion_id, survey_id, submitted_at, is_anonymous, user_id
            FROM survey_completions
            WHERE completion_id = $1 AND user_id = $2 AND is_anonymous = FALSE
        """, comp_uuid, user_uuid)
        
        if not comp:
            return None
            
        query_responses = """
            SELECT sr.question_id, sq.question_text, sr.answer
            FROM survey_responses sr
            JOIN survey_questions sq ON sr.question_id = sq.question_id
            WHERE sr.completion_id = $1
            ORDER BY sq.order_position ASC
        """
        records = await self.conn.fetch(query_responses, comp_uuid)
        responses = []
        for r in records:
            ans = r["answer"]
            if isinstance(ans, str):
                try:
                    ans = json.loads(ans)
                except:
                    pass
            responses.append({
                "question_id": r["question_id"],
                "question_text": r["question_text"],
                "answer": ans
            })
            
        return {
            "completion_id": comp["completion_id"],
            "survey_id": comp["survey_id"],
            "submitted_at": comp["submitted_at"],
            "responses": responses
        }

    # ------------------------------------------------------------------
    # Phase 2: drafts, assignments, analytics
    # ------------------------------------------------------------------
    async def _require_open_survey(self, survey_id: str) -> Dict[str, Any]:
        survey = await self.conn.fetchrow(
            "SELECT survey_id, title, status, published_date, closing_date FROM surveys WHERE survey_id = $1",
            self._to_uuid(survey_id),
        )
        if not survey:
            raise ValueError("Survey not found")
        today = date.today()
        if survey["status"] != "active" or (survey["closing_date"] and survey["closing_date"] < today) \
                or (survey["published_date"] and survey["published_date"] > today):
            raise ValueError("Survey is not open")
        return dict(survey)

    async def save_draft(self, survey_id: str, user_id: str, answers: Dict[str, Any]) -> Dict[str, Any]:
        """Replace the user's saved answers. Creates a self-assignment when nobody assigned the survey."""
        await self._require_open_survey(survey_id)
        valid = {str(r["question_id"]) for r in await self.conn.fetch(
            "SELECT question_id FROM survey_questions WHERE survey_id = $1", self._to_uuid(survey_id))}
        unknown = [q for q in answers if q not in valid]
        if unknown:
            raise ValueError(f"Question {unknown[0]} does not belong to this survey")
        row = await self.conn.fetchrow(
            """
            INSERT INTO survey_assignments (survey_id, patient_user_id, status, draft_answers)
            VALUES ($1, $2, 'in_progress', $3::jsonb)
            ON CONFLICT (survey_id, patient_user_id) DO UPDATE
                SET draft_answers = EXCLUDED.draft_answers, status = 'in_progress', updated_at = NOW()
                WHERE survey_assignments.status IN ('pending', 'in_progress')
            RETURNING status, draft_answers, updated_at
            """,
            self._to_uuid(survey_id), self._to_uuid(user_id), json.dumps(answers),
        )
        if not row:
            raise PermissionError("This survey is already completed or expired")
        result = dict(row)
        result["draft_answers"] = self._deserialize_jsonb(result["draft_answers"]) or {}
        return result

    async def assign(self, survey_id: str, emails: List[str], assigned_by: str,
                     trial_id: Optional[str], due_date) -> Dict[str, Any]:
        """Assign to existing patient/caregiver accounts by email. Re-assigning someone is a no-op."""
        survey = await self._require_open_survey(survey_id)
        wanted = list(dict.fromkeys(e.lower() for e in emails))
        users = await self.conn.fetch(
            "SELECT id, lower(email) AS email FROM users WHERE lower(email) = ANY($1) "
            "AND is_active AND user_type IN ('patient', 'caregiver')",
            wanted,
        )
        found = {u["email"]: u["id"] for u in users}
        assigned, already = [], []
        for email, uid in found.items():
            row = await self.conn.fetchval(
                """
                INSERT INTO survey_assignments (survey_id, patient_user_id, assigned_by_id, trial_id, due_date)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (survey_id, patient_user_id) DO NOTHING
                RETURNING id
                """,
                self._to_uuid(survey_id), uid, self._to_uuid(assigned_by),
                self._to_uuid(trial_id) if trial_id else None, due_date,
            )
            (assigned if row else already).append({"email": email, "user_id": uid})
        return {
            "survey": survey,
            "assigned": assigned,
            "already_assigned": [a["email"] for a in already],
            "not_found": [e for e in wanted if e not in found],
        }

    async def analytics(self, survey_id: str) -> Optional[Dict[str, Any]]:
        survey = await self.conn.fetchrow("SELECT survey_id, title FROM surveys WHERE survey_id = $1", self._to_uuid(survey_id))
        if not survey:
            return None
        sid = self._to_uuid(survey_id)
        counts = await self.conn.fetchrow(
            """
            SELECT
                (SELECT count(*) FROM survey_completions WHERE survey_id = $1) AS responses,
                count(*) AS assigned,
                count(*) FILTER (WHERE status = 'completed') AS completed,
                avg(EXTRACT(EPOCH FROM completed_at - created_at)) FILTER (WHERE status = 'completed') AS avg_seconds
            FROM survey_assignments WHERE survey_id = $1
            """,
            sid,
        )
        questions = await self.conn.fetch(
            "SELECT question_id, question_text, question_type, options FROM survey_questions "
            "WHERE survey_id = $1 ORDER BY order_position",
            sid,
        )
        answers: Dict[str, List[Any]] = {}
        for r in await self.conn.fetch("SELECT question_id, answer FROM survey_responses WHERE survey_id = $1", sid):
            answers.setdefault(str(r["question_id"]), []).append(self._deserialize_jsonb(r["answer"]))

        per_question = []
        for q in questions:
            values = answers.get(str(q["question_id"]), [])
            item = {"question_id": q["question_id"], "question_text": q["question_text"],
                    "question_type": q["question_type"], "answered": len(values)}
            if q["question_type"] in ("yes_no", "single_choice", "multiple_choice"):
                dist: Dict[str, int] = {o: 0 for o in (self._deserialize_jsonb(q["options"]) or [])}
                for v in values:
                    for one in v if isinstance(v, list) else [v]:
                        key = ("yes" if one in (True, "true", "True") else "no" if one in (False, "false", "False")
                               else str(one)) if q["question_type"] == "yes_no" else str(one)
                        dist[key] = dist.get(key, 0) + 1
                item["distribution"] = dist
            elif q["question_type"] in ("scale", "number"):
                nums = [float(v) for v in values]
                item["average"] = round(sum(nums) / len(nums), 2) if nums else None
                item["min"] = min(nums) if nums else None
                item["max"] = max(nums) if nums else None
            # open_text and date: counts only; free text is not exposed in aggregate analytics
            per_question.append(item)

        assigned = counts["assigned"]
        return {
            "survey_id": survey["survey_id"],
            "title": survey["title"],
            "total_responses": counts["responses"],
            "assigned": assigned,
            "completed_assignments": counts["completed"],
            "completion_rate": round(100 * counts["completed"] / assigned, 1) if assigned else None,
            "avg_completion_hours": round(float(counts["avg_seconds"]) / 3600, 1) if counts["avg_seconds"] is not None else None,
            "questions": per_question,
        }

    # ------------------------------------------------------------------
    # Patient hub & builder
    # ------------------------------------------------------------------
    async def list_assigned(self, user_id: str) -> List[Dict[str, Any]]:
        rows = await self.conn.fetch(
            """
            SELECT s.survey_id, s.title, s.description, s.estimated_time, a.status, a.due_date,
                   a.draft_answers <> '{}'::jsonb AS has_draft, t.title AS trial_title, a.created_at AS assigned_at
            FROM survey_assignments a
            JOIN surveys s ON s.survey_id = a.survey_id
            LEFT JOIN clinical_trials t ON t.trial_id = a.trial_id
            WHERE a.patient_user_id = $1
            ORDER BY (a.status IN ('pending', 'in_progress')) DESC, a.due_date ASC NULLS LAST, a.created_at DESC
            """,
            self._to_uuid(user_id),
        )
        return self._records_to_list(rows)

    async def list_managed(self) -> List[Dict[str, Any]]:
        rows = await self.conn.fetch(
            """
            SELECT s.survey_id, s.title, s.status, s.created_at, s.closing_date,
                   (SELECT count(*) FROM survey_questions q WHERE q.survey_id = s.survey_id) AS question_count,
                   (SELECT count(*) FROM survey_completions c WHERE c.survey_id = s.survey_id) AS responses,
                   (SELECT count(*) FROM survey_assignments a WHERE a.survey_id = s.survey_id) AS assigned
            FROM surveys s
            ORDER BY s.created_at DESC
            """
        )
        return self._records_to_list(rows)

    async def create_survey(self, data: Dict[str, Any]) -> str:
        """Questions refer to branch targets by index; they become question ids once inserted."""
        questions = data["questions"]
        for i, q in enumerate(questions):
            if q["type"] in ("single_choice", "multiple_choice") and len(q.get("options") or []) < 2:
                raise ValueError(f"Question {i + 1} needs at least two options")
            if q["branching"] and q["type"] not in ("yes_no", "single_choice", "multiple_choice"):
                raise ValueError(f"Question {i + 1}: only yes/no and choice questions can branch")
            for b in q["branching"]:
                if not i < b["next"] < len(questions):
                    raise ValueError(f"Question {i + 1}: a branch must jump to a later question")
                allowed = ["yes", "no"] if q["type"] == "yes_no" else q.get("options") or []
                if b["value"] not in allowed:
                    raise ValueError(f"Question {i + 1}: '{b['value']}' is not one of its answers")

        async with self.conn.transaction():
            survey_id = await self.conn.fetchval(
                """
                INSERT INTO surveys (title, description, consent_text, estimated_time, target_audience,
                                     closing_date, status, published_date)
                VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7::varchar, CASE WHEN $7::varchar = 'active' THEN CURRENT_DATE END)
                RETURNING survey_id
                """,
                data["title"], data["description"], data.get("consent_text"), data.get("estimated_time"),
                json.dumps(data.get("target_audience") or []), data.get("closing_date"), data["status"],
            )
            ids = []
            for pos, q in enumerate(questions, start=1):
                ids.append(await self.conn.fetchval(
                    """
                    INSERT INTO survey_questions (survey_id, question_text, question_type, order_position, required, options)
                    VALUES ($1, $2, $3, $4, $5, $6::jsonb) RETURNING question_id
                    """,
                    survey_id, q["text"], q["type"], pos, q["required"],
                    json.dumps(q["options"]) if q.get("options") else None,
                ))
            for q_id, q in zip(ids, questions):
                if q["branching"]:
                    rules = [{"condition": "equals", "value": b["value"], "next_question_id": str(ids[b["next"]])}
                             for b in q["branching"]]
                    await self.conn.execute(
                        "UPDATE survey_questions SET branching_rules = $2::jsonb WHERE question_id = $1", q_id, json.dumps(rules))
        return str(survey_id)

    STATUS_TRANSITIONS = {"draft": {"active"}, "active": {"closed"}, "closed": set()}

    async def change_status(self, survey_id: str, new_status: str) -> Optional[str]:
        """Returns the previous status, or None when the survey does not exist. Raises on a disallowed move."""
        current = await self.conn.fetchval("SELECT status FROM surveys WHERE survey_id = $1", self._to_uuid(survey_id))
        if current is None:
            return None
        if new_status not in self.STATUS_TRANSITIONS[current]:
            raise ValueError(f"Cannot change a {current} survey to {new_status}")
        await self.conn.execute(
            "UPDATE surveys SET status = $2::varchar, updated_at = NOW(), "
            "published_date = COALESCE(published_date, CASE WHEN $2::varchar = 'active' THEN CURRENT_DATE END) "
            "WHERE survey_id = $1 AND status = $3::varchar",
            self._to_uuid(survey_id), new_status, current,
        )
        return current
