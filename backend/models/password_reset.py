import uuid
import secrets
from datetime import datetime, timedelta
from backend.models.database import get_db_connection


class PasswordReset:
    def __init__(self, reset_id, user_id, token, expires_at, used=0, created_at=None):
        self.reset_id = reset_id
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at
        self.used = used
        self.created_at = created_at

    @staticmethod
    def create(user_id: str, expires_in_minutes: int = 30):
        reset_id = str(uuid.uuid4())
        token = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(minutes=expires_in_minutes)).isoformat()

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO password_resets (reset_id, user_id, token, expires_at, used)
                VALUES (%s, %s, %s, %s, 0)
            """, (reset_id, user_id, token, expires_at))
            conn.commit()

        return PasswordReset.get_by_token(token)

    @staticmethod
    def get_by_token(token: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM password_resets WHERE token = %s", (token,))
            row = cursor.fetchone()
            if row:
                return PasswordReset(**dict(row))
        return None

    def is_valid(self) -> bool:
        if self.used:
            return False
        return datetime.fromisoformat(self.expires_at) >= datetime.now()

    def mark_used(self):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE password_resets SET used = 1 WHERE reset_id = %s", (self.reset_id,))
            conn.commit()
        self.used = 1

    @staticmethod
    def cleanup_expired():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM password_resets WHERE expires_at < %s OR used = 1", (datetime.now().isoformat(),))
            conn.commit()
            return cursor.rowcount