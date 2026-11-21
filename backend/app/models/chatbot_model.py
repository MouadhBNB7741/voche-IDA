import json
from typing import Any, Dict, List, Optional

from app.models.base_model import DBModel

CONVERSATION_COLUMNS = "id, title, context_type, context_reference_id, created_at, updated_at"
MESSAGE_COLUMNS = "id, sender_role, content, citations, safety_flagged, created_at"


class ChatbotModel(DBModel):
    """SQL for AI assistant conversations, messages and feedback. Every query is scoped to the owner."""

    @staticmethod
    def _message(record) -> Dict[str, Any]:
        msg = dict(record)
        if isinstance(msg.get("citations"), str):
            msg["citations"] = json.loads(msg["citations"])
        return msg

    async def create_conversation(self, user_id, title, context_type, context_reference_id) -> Dict[str, Any]:
        row = await self.conn.fetchrow(
            f"""
            INSERT INTO chat_conversations (user_id, title, context_type, context_reference_id)
            VALUES ($1, $2, $3, $4)
            RETURNING {CONVERSATION_COLUMNS}
            """,
            user_id, title, context_type, context_reference_id,
        )
        return dict(row)

    async def list_conversations(self, user_id) -> List[Dict[str, Any]]:
        rows = await self.conn.fetch(
            f"""
            SELECT {CONVERSATION_COLUMNS} FROM chat_conversations
            WHERE user_id = $1 AND is_archived = FALSE
            ORDER BY updated_at DESC
            """,
            user_id,
        )
        return self._records_to_list(rows)

    async def get_conversation(self, conversation_id, user_id) -> Optional[Dict[str, Any]]:
        row = await self.conn.fetchrow(
            f"SELECT {CONVERSATION_COLUMNS} FROM chat_conversations WHERE id = $1 AND user_id = $2",
            conversation_id, user_id,
        )
        return dict(row) if row else None

    async def get_messages(self, conversation_id, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        # Newest `limit` messages, returned oldest first.
        rows = await self.conn.fetch(
            f"""
            SELECT * FROM (
                SELECT {MESSAGE_COLUMNS} FROM chat_messages
                WHERE conversation_id = $1
                ORDER BY created_at DESC
                LIMIT $2
            ) recent ORDER BY created_at ASC
            """,
            conversation_id, limit,
        )
        return [self._message(r) for r in rows]

    async def delete_conversation(self, conversation_id, user_id) -> bool:
        result = await self.conn.execute(
            "DELETE FROM chat_conversations WHERE id = $1 AND user_id = $2",
            conversation_id, user_id,
        )
        return result != "DELETE 0"

    async def add_exchange(self, conversation_id, user_text, reply: Dict[str, Any], set_title: Optional[str]):
        """Save the user's message and the assistant's reply together, and bump the conversation."""
        async with self.conn.transaction():
            user_msg = await self.conn.fetchrow(
                f"""
                INSERT INTO chat_messages (conversation_id, sender_role, content)
                VALUES ($1, 'user', $2)
                RETURNING {MESSAGE_COLUMNS}
                """,
                conversation_id, user_text,
            )
            # clock_timestamp() so the reply always sorts after the question inside one transaction
            assistant_msg = await self.conn.fetchrow(
                f"""
                INSERT INTO chat_messages
                    (conversation_id, sender_role, content, citations, token_count, safety_flagged, created_at)
                VALUES ($1, 'assistant', $2, $3::jsonb, $4, $5, clock_timestamp())
                RETURNING {MESSAGE_COLUMNS}
                """,
                conversation_id, reply["content"], json.dumps(reply["citations"]),
                reply.get("token_count"), reply["safety_flagged"],
            )
            await self.conn.execute(
                "UPDATE chat_conversations SET updated_at = NOW(), title = COALESCE(title, $2) WHERE id = $1",
                conversation_id, set_title,
            )
        return self._message(user_msg), self._message(assistant_msg)

    async def save_feedback(self, message_id, user_id, rating: int, comment: Optional[str]) -> bool:
        """Upsert feedback on an assistant message in one of the user's own conversations."""
        row = await self.conn.fetchrow(
            """
            INSERT INTO chat_feedback (message_id, user_id, rating, comment)
            SELECT m.id, $2, $3, $4
            FROM chat_messages m
            JOIN chat_conversations c ON c.id = m.conversation_id
            WHERE m.id = $1 AND c.user_id = $2 AND m.sender_role = 'assistant'
            ON CONFLICT (message_id, user_id)
            DO UPDATE SET rating = EXCLUDED.rating, comment = EXCLUDED.comment, created_at = NOW()
            RETURNING id
            """,
            message_id, user_id, rating, comment,
        )
        return row is not None
