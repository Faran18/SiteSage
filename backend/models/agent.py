# backend/models/agent.py

import uuid
from datetime import datetime

from backend.models.database import get_db_connection

try:
    from backend.core.vector_db import delete_agent_collection
except Exception:
    delete_agent_collection = None


def _safe_delete_vector_collection(agent_id: str) -> None:
    if delete_agent_collection is None:
        return
    try:
        delete_agent_collection(agent_id)
    except Exception:
        return


class Agent:
    def __init__(
        self,
        agent_id,
        user_id,
        name,
        role,
        status="active",
        created_at=None,
        updated_at=None,
        last_scraped=None,
        chunks_count=0,
    ):
        self.agent_id = agent_id
        self.user_id = user_id
        self.name = name
        self.role = role
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.last_scraped = last_scraped
        self.chunks_count = chunks_count

    @staticmethod
    def create(user_id, name, role):
        agent_id = str(uuid.uuid4())

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO agents (agent_id, user_id, name, role)
                VALUES (%s, %s, %s, %s)
                """,
                (agent_id, user_id, name, role),
            )
            conn.commit()

        return Agent.get_by_id(agent_id)

    @staticmethod
    def get_by_id(agent_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents WHERE agent_id = %s", (agent_id,))
            row = cursor.fetchone()
            return Agent(**dict(row)) if row else None

    @staticmethod
    def get_all(status=None, user_id=None):
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if status and user_id:
                cursor.execute(
                    "SELECT * FROM agents WHERE status = %s AND user_id = %s ORDER BY created_at DESC",
                    (status, user_id),
                )
            elif status:
                cursor.execute(
                    "SELECT * FROM agents WHERE status = %s ORDER BY created_at DESC",
                    (status,),
                )
            elif user_id:
                cursor.execute(
                    "SELECT * FROM agents WHERE user_id = %s ORDER BY created_at DESC",
                    (user_id,),
                )
            else:
                cursor.execute("SELECT * FROM agents ORDER BY created_at DESC")

            rows = cursor.fetchall()
            return [Agent(**dict(r)) for r in rows]

    @staticmethod
    def get_by_user(user_id, status=None):
        return Agent.get_all(status=status, user_id=user_id)

    @staticmethod
    def count_by_user(user_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM agents WHERE user_id = %s", (user_id,))
            row = cursor.fetchone()
            return row["count"] if row else 0

    def update(self, **kwargs):
        allowed_fields = ["name", "role", "status", "last_scraped", "chunks_count"]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return

        updates["updated_at"] = datetime.now().isoformat()

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [self.agent_id]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE agents SET {set_clause} WHERE agent_id = %s", values)
            conn.commit()

        for k, v in updates.items():
            setattr(self, k, v)

    def is_owned_by(self, user_id):
        return self.user_id == user_id

    @staticmethod
    def delete_with_related(agent_id: str) -> bool:
        _safe_delete_vector_collection(agent_id)

        with get_db_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM scrape_configs WHERE agent_id = %s", (agent_id,))
            cursor.execute("DELETE FROM subscriptions WHERE agent_id = %s", (agent_id,))
            cursor.execute("DELETE FROM change_history WHERE agent_id = %s", (agent_id,))

            cursor.execute("DELETE FROM agents WHERE agent_id = %s", (agent_id,))
            conn.commit()

            return cursor.rowcount > 0

    @staticmethod
    def delete_all_for_user(user_id: str) -> bool:
        agents = Agent.get_by_user(user_id)
        for a in agents:
            Agent.delete_with_related(a.agent_id)
        return True

    @staticmethod
    def delete(agent_id):
        return Agent.delete_with_related(agent_id)

    def to_dict(self):
        return {
            "agent_id": self.agent_id,
            "user_id": self.user_id,
            "name": self.name,
            "role": self.role,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_scraped": self.last_scraped,
            "chunks_count": self.chunks_count,
        }

    def __repr__(self):
        return f"<Agent {self.agent_id}: {self.name} (user: {self.user_id}, status: {self.status})>"


class ScrapeConfig:
    def __init__(
        self,
        config_id,
        agent_id,
        url,
        css_selector=None,
        xpath=None,
        is_primary=1,
        auto_scrape=0,
        scrape_interval_hours=24,
        last_content_hash=None,
        created_at=None,
    ):
        self.config_id = config_id
        self.agent_id = agent_id
        self.url = url
        self.css_selector = css_selector
        self.xpath = xpath
        self.is_primary = is_primary
        self.auto_scrape = auto_scrape
        self.scrape_interval_hours = scrape_interval_hours
        self.last_content_hash = last_content_hash
        self.created_at = created_at

    @staticmethod
    def create(
        agent_id,
        url,
        css_selector=None,
        xpath=None,
        is_primary=True,
        auto_scrape=False,
        scrape_interval_hours=24,
    ):
        config_id = str(uuid.uuid4())

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO scrape_configs
                (config_id, agent_id, url, css_selector, xpath, is_primary,
                 auto_scrape, scrape_interval_hours)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    config_id,
                    agent_id,
                    url,
                    css_selector,
                    xpath,
                    1 if is_primary else 0,
                    1 if auto_scrape else 0,
                    scrape_interval_hours,
                ),
            )
            conn.commit()

        return ScrapeConfig.get_by_id(config_id)

    @staticmethod
    def get_by_id(config_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_configs WHERE config_id = %s", (config_id,))
            row = cursor.fetchone()
            return ScrapeConfig(**dict(row)) if row else None

    @staticmethod
    def get_by_agent(agent_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scrape_configs WHERE agent_id = %s ORDER BY is_primary DESC, created_at DESC",
                (agent_id,),
            )
            rows = cursor.fetchall()
            return [ScrapeConfig(**dict(r)) for r in rows]

    @staticmethod
    def get_primary(agent_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM scrape_configs WHERE agent_id = %s AND is_primary = 1 LIMIT 1",
                (agent_id,),
            )
            row = cursor.fetchone()
            return ScrapeConfig(**dict(row)) if row else None

    @staticmethod
    def get_all_auto_scrape():
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM scrape_configs WHERE auto_scrape = 1")
            rows = cursor.fetchall()
            return [ScrapeConfig(**dict(r)) for r in rows]

    def update(self, **kwargs):
        allowed_fields = [
            "url",
            "css_selector",
            "xpath",
            "auto_scrape",
            "scrape_interval_hours",
            "last_content_hash",
            "is_primary",
        ]
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            return

        set_clause = ", ".join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [self.config_id]

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"UPDATE scrape_configs SET {set_clause} WHERE config_id = %s", values)
            conn.commit()

        for k, v in updates.items():
            setattr(self, k, v)

    @staticmethod
    def delete(config_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM scrape_configs WHERE config_id = %s", (config_id,))
            conn.commit()
            return cursor.rowcount > 0

    def to_dict(self):
        return {
            "config_id": self.config_id,
            "agent_id": self.agent_id,
            "url": self.url,
            "css_selector": self.css_selector,
            "xpath": self.xpath,
            "is_primary": bool(self.is_primary),
            "auto_scrape": bool(self.auto_scrape),
            "scrape_interval_hours": self.scrape_interval_hours,
            "last_content_hash": self.last_content_hash,
            "created_at": self.created_at,
        }


class Subscription:
    def __init__(self, subscription_id, agent_id, email, is_active=1, created_at=None):
        self.subscription_id = subscription_id
        self.agent_id = agent_id
        self.email = email
        self.is_active = is_active
        self.created_at = created_at

    @staticmethod
    def create(agent_id, email):
        subscription_id = str(uuid.uuid4())

        with get_db_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    """
                    INSERT INTO subscriptions (subscription_id, agent_id, email)
                    VALUES (%s, %s, %s)
                    """,
                    (subscription_id, agent_id, email),
                )
                conn.commit()
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    cursor.execute(
                        """
                        SELECT subscription_id FROM subscriptions
                        WHERE agent_id = %s AND email = %s
                        """,
                        (agent_id, email),
                    )
                    row = cursor.fetchone()
                    if row:
                        return Subscription.get_by_id(row["subscription_id"])
                raise

        return Subscription.get_by_id(subscription_id)

    @staticmethod
    def get_by_id(subscription_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptions WHERE subscription_id = %s", (subscription_id,))
            row = cursor.fetchone()
            return Subscription(**dict(row)) if row else None

    @staticmethod
    def get_by_agent(agent_id, active_only=True):
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                cursor.execute(
                    "SELECT * FROM subscriptions WHERE agent_id = %s AND is_active = 1",
                    (agent_id,),
                )
            else:
                cursor.execute("SELECT * FROM subscriptions WHERE agent_id = %s", (agent_id,))

            rows = cursor.fetchall()
            return [Subscription(**dict(r)) for r in rows]

    @staticmethod
    def get_by_email(email):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM subscriptions WHERE email = %s", (email,))
            rows = cursor.fetchall()
            return [Subscription(**dict(r)) for r in rows]

    def update(self, is_active):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE subscriptions SET is_active = %s WHERE subscription_id = %s",
                (1 if is_active else 0, self.subscription_id),
            )
            conn.commit()

        self.is_active = 1 if is_active else 0

    @staticmethod
    def delete(subscription_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM subscriptions WHERE subscription_id = %s", (subscription_id,))
            conn.commit()
            return cursor.rowcount > 0

    def to_dict(self):
        return {
            "subscription_id": self.subscription_id,
            "agent_id": self.agent_id,
            "email": self.email,
            "is_active": bool(self.is_active),
            "created_at": self.created_at,
        }


class ChangeHistory:
    def __init__(
        self,
        change_id,
        agent_id,
        config_id,
        old_content_preview=None,
        new_content_preview=None,
        change_summary=None,
        detected_at=None,
    ):
        self.change_id = change_id
        self.agent_id = agent_id
        self.config_id = config_id
        self.old_content_preview = old_content_preview
        self.new_content_preview = new_content_preview
        self.change_summary = change_summary
        self.detected_at = detected_at

    @staticmethod
    def create(agent_id, config_id, old_content, new_content, change_summary):
        change_id = str(uuid.uuid4())

        old_preview = old_content[:500] if old_content else ""
        new_preview = new_content[:500] if new_content else ""

        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO change_history
                (change_id, agent_id, config_id, old_content_preview,
                 new_content_preview, change_summary)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (change_id, agent_id, config_id, old_preview, new_preview, change_summary),
            )
            conn.commit()

        return ChangeHistory.get_by_id(change_id)

    @staticmethod
    def get_by_id(change_id):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM change_history WHERE change_id = %s", (change_id,))
            row = cursor.fetchone()
            return ChangeHistory(**dict(row)) if row else None

    @staticmethod
    def get_by_agent(agent_id, limit=10):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM change_history
                WHERE agent_id = %s
                ORDER BY detected_at DESC
                LIMIT %s
                """,
                (agent_id, limit),
            )
            rows = cursor.fetchall()
            return [ChangeHistory(**dict(r)) for r in rows]

    @staticmethod
    def get_by_config(config_id, limit=10):
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM change_history
                WHERE config_id = %s
                ORDER BY detected_at DESC
                LIMIT %s
                """,
                (config_id, limit),
            )
            rows = cursor.fetchall()
            return [ChangeHistory(**dict(r)) for r in rows]

    def to_dict(self):
        return {
            "change_id": self.change_id,
            "agent_id": self.agent_id,
            "config_id": self.config_id,
            "old_content_preview": self.old_content_preview,
            "new_content_preview": self.new_content_preview,
            "change_summary": self.change_summary,
            "detected_at": self.detected_at,
        }