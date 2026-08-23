# backend/models/conversation.py

import uuid
from backend.models.database import get_db_connection


class Conversation:
    """One conversation per agent (simple 1:1 for now)."""

    @staticmethod
    def get_or_create_for_agent(agent_id: str) -> str:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT conversation_id FROM conversations WHERE agent_id = ? ORDER BY created_at DESC LIMIT 1",
                (agent_id,),
            )
            row = cursor.fetchone()
            if row:
                return row["conversation_id"]

            conversation_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO conversations (conversation_id, agent_id, title) VALUES (?, ?, ?)",
                (conversation_id, agent_id, "Chat"),
            )
            conn.commit()
            return conversation_id

    @staticmethod
    def clear_for_agent(agent_id: str) -> None:
        """Wipe conversation + messages for an agent (e.g. 'New Chat' button)."""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM conversations WHERE agent_id = ?", (agent_id,))
            conn.commit()


class Message:
    @staticmethod
    def add(conversation_id: str, role: str, content: str) -> None:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO messages (message_id, conversation_id, role, content) VALUES (?, ?, ?, ?)",
                (str(uuid.uuid4()), conversation_id, role, content),
            )
            conn.commit()

    @staticmethod
    def get_recent(conversation_id: str, limit: int = 6) -> list[dict]:
        """
        Returns the last `limit` messages, oldest first, as
        [{"role": "user"/"assistant", "content": "..."}]
        ready to feed straight into the Groq chat messages list.
        """
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT role, content FROM messages
                WHERE conversation_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (conversation_id, limit),
            )
            rows = cursor.fetchall()
            # rows come back newest-first; reverse to chronological order
            return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]