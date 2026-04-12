import logging
import json
import uuid
from typing import Any, Dict, List, Optional
from datetime import date

logger = logging.getLogger(__name__)

from app.models.base_model import DBModel

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

    async def get_survey_questions(self, survey_id: str) -> Optional[Dict[str, Any]]:
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
                   required, options
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

        survey_data["questions"] = questions
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
                "SELECT question_id, question_type, required, options FROM survey_questions WHERE survey_id = $1",
                self._to_uuid(survey_id)
            )
            valid_questions = {str(q["question_id"]): dict(q) for q in record_questions}
            response_map = {str(r["question_id"]): r["answer"] for r in responses}

            for q_id, q_data in valid_questions.items():
                if q_data["required"] and q_id not in response_map:
                    raise ValueError(f"Required question {q_id} is missing an answer")
                
            for r_q_id, answer in response_map.items():
                if r_q_id not in valid_questions:
                    raise ValueError(f"Question {r_q_id} does not belong to this survey")
                
                q_type = valid_questions[r_q_id]["question_type"]
                options = valid_questions[r_q_id].get("options")
                if options and isinstance(options, str):
                    try:
                        options = json.loads(options)
                    except Exception:
                        options = []
                        
                if q_type == "yes_no":
                    if str(answer).lower() not in ["yes", "no", "true", "false"]:
                        raise ValueError(f"Question {r_q_id} requires a yes/no answer")
                elif q_type == "scale":
                    try:
                        val = float(answer)
                    except (ValueError, TypeError):
                        raise ValueError(f"Question {r_q_id} requires a numeric scale answer")
                elif q_type == "multiple_choice":
                    if options:
                        ans_list = answer if isinstance(answer, list) else [answer]
                        for a in ans_list:
                            if a not in options:
                                raise ValueError(f"Answer '{a}' is not a valid option for question {r_q_id}")

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
