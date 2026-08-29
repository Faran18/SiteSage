import base64
import hashlib
import hmac
import os
import uuid
from datetime import datetime, timedelta

from backend.models.database import get_db_connection


def _pbkdf2_hash_password(password: str, iterations: int = 200_000) -> str:
    if not password:
        raise ValueError("Password is required")

    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)

    salt_b64 = base64.urlsafe_b64encode(salt).decode("utf-8").rstrip("=")
    dk_b64 = base64.urlsafe_b64encode(dk).decode("utf-8").rstrip("=")

    return f"pbkdf2_sha256${iterations}${salt_b64}${dk_b64}"


def _pbkdf2_verify_password(password: str, stored: str) -> bool:
    try:
        algo, iters_str, salt_b64, dk_b64 = stored.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False

        iterations = int(iters_str)
        salt = base64.urlsafe_b64decode(salt_b64 + "==")
        expected = base64.urlsafe_b64decode(dk_b64 + "==")

        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return hmac.compare_digest(dk, expected)
    except Exception:
        return False


class User:
    def __init__(
        self,
        user_id,
        email,
        password_hash,
        full_name=None,
        created_at=None,
        last_login=None,
        is_active=1,
    ):
        self.user_id = user_id
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name
        self.created_at = created_at
        self.last_login = last_login
        self.is_active = is_active

    @staticmethod
    def get_by_id(user_id: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            return User(**dict(row)) if row else None

    @staticmethod
    def get_by_email(email: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE email = %s", (email.strip().lower(),))
            row = cursor.fetchone()
            return User(**dict(row)) if row else None

    @staticmethod
    def verify_password(plain_password: str, password_hash: str) -> bool:
        return _pbkdf2_verify_password(plain_password, password_hash)

    @staticmethod
    def create(email: str, password: str, full_name: str):
        email = (email or "").strip().lower()
        if not email:
            raise ValueError("Email is required")
        if not password or len(password) < 6:
            raise ValueError("Password must be at least 6 characters long")
        if not full_name or not full_name.strip():
            raise ValueError("Full name is required")

        if User.get_by_email(email):
            raise ValueError("Email already registered")

        user_id = str(uuid.uuid4())
        password_hash = _pbkdf2_hash_password(password)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO users (user_id, email, password_hash, full_name, is_active)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (user_id, email, password_hash, full_name.strip(), 1),
            )
            conn.commit()

        return User.get_by_id(user_id)

    @staticmethod
    def authenticate(email: str, password: str):
        email = (email or "").strip().lower()
        user = User.get_by_email(email)
        if not user or not user.is_active:
            return None
        if not User.verify_password(password, user.password_hash):
            return None

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_login = %s WHERE user_id = %s", (datetime.now().isoformat(), user.user_id))
            conn.commit()

        return User.get_by_id(user.user_id)

    def update(self, **kwargs):
        allowed = {"full_name", "password", "is_active"}
        updates = {k: v for k, v in kwargs.items() if k in allowed}

        if "password" in updates:
            new_password = updates["password"]
            if not new_password or len(new_password) < 6:
                raise ValueError("Password must be at least 6 characters long")
            updates["password_hash"] = _pbkdf2_hash_password(new_password)
            del updates["password"]

        if "full_name" in updates and updates["full_name"] is not None:
            updates["full_name"] = updates["full_name"].strip()

        if not updates:
            return

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [self.user_id]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE users SET {set_clause} WHERE user_id = %s", values)
            conn.commit()

        fresh = User.get_by_id(self.user_id)
        self.email = fresh.email
        self.password_hash = fresh.password_hash
        self.full_name = fresh.full_name
        self.created_at = fresh.created_at
        self.last_login = fresh.last_login
        self.is_active = fresh.is_active

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "email": self.email,
            "full_name": self.full_name,
            "created_at": self.created_at,
            "last_login": self.last_login,
            "is_active": bool(self.is_active),
        }

    @staticmethod
    def delete_completely(user_id: str) -> bool:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0


class Session:
    def __init__(self, session_id, user_id, token, expires_at=None, created_at=None):
        self.session_id = session_id
        self.user_id = user_id
        self.token = token
        self.expires_at = expires_at
        self.created_at = created_at

    @staticmethod
    def create(user_id: str, expires_in_hours: int = 24):
        session_id = str(uuid.uuid4())
        token = str(uuid.uuid4())
        expires = datetime.now() + timedelta(hours=expires_in_hours)

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO sessions (session_id, user_id, token, expires_at)
                VALUES (%s, %s, %s, %s)
                """,
                (session_id, user_id, token, expires.isoformat()),
            )
            conn.commit()

        return Session.get_by_token(token)

    @staticmethod
    def get_by_token(token: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE token = %s", (token,))
            row = cursor.fetchone()
            return Session(**dict(row)) if row else None

    @staticmethod
    def get_by_user(user_id: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE user_id = %s", (user_id,))
            rows = cursor.fetchall()
            return [Session(**dict(r)) for r in rows]

    @staticmethod
    def delete_all_user_sessions(user_id: str):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sessions WHERE user_id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount

    @staticmethod
    def cleanup_expired() -> int:
        now_iso = datetime.now().isoformat()
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at < %s",
                (now_iso,),
            )
            conn.commit()
            return cursor.rowcount

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "token": self.token,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
        }