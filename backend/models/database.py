# backend/models/database.py

import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
from backend.core.config import SUPABASE_DB_URL

if not SUPABASE_DB_URL:
    raise RuntimeError(
        "SUPABASE_DB_URL is not set. Add it to your .env - "
        "Supabase dashboard > Project Settings > Database > Connection string > URI."
    )

_pool = pg_pool.ThreadedConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=SUPABASE_DB_URL,
    cursor_factory=RealDictCursor,
)


@contextmanager
def get_db_connection():
    """
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents")

    Borrows a connection from the pool instead of opening a new one each
    call, and always returns it to the pool when done (or discards it if
    something went wrong mid-transaction, so a bad connection doesn't get
    handed to the next caller).
    cursor_factory=RealDictCursor makes rows behave like sqlite3.Row did -
    dict(row) still works everywhere it's used in the model files.
    """
    conn = _pool.getconn()

    try:
        yield conn  # Give the connection to the code block
    except Exception:
        conn.rollback()  # undo any partial transaction before it goes back
        raise
    finally:
        _pool.putconn(conn)  # Return to the pool instead of closing


# backend/models/database.py

def init_database():

    with get_db_connection() as conn:
        cursor = conn.cursor()


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                full_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                is_active INTEGER DEFAULT 1
            )
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                token TEXT UNIQUE NOT NULL,
                expires_at TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)


        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agents (
                agent_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT NOT NULL,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_scraped TIMESTAMP,
                chunks_count INTEGER DEFAULT 0,

                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # UPDATED: Scrape configs with scheduler
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scrape_configs (
                config_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                url TEXT NOT NULL,
                css_selector TEXT,
                xpath TEXT,
                is_primary INTEGER DEFAULT 1,
                auto_scrape INTEGER DEFAULT 0,
                scrape_interval_hours INTEGER DEFAULT 24,
                last_content_hash TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
        """)

        # NEW: Email subscriptions for agents
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                subscription_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                email TEXT NOT NULL,
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
                UNIQUE(agent_id, email)
            )
        """)

        # NEW: Change history for tracking updates
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS change_history (
                change_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                config_id TEXT NOT NULL,
                old_content_preview TEXT,
                new_content_preview TEXT,
                change_summary TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE,
                FOREIGN KEY (config_id) REFERENCES scrape_configs(config_id) ON DELETE CASCADE
            )
        """)

        # Conversations and messages (unchanged)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                agent_id TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                title TEXT,

                FOREIGN KEY (agent_id) REFERENCES agents(agent_id) ON DELETE CASCADE
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminders (
                reminder_id TEXT PRIMARY KEY,
                user_id TEXT,
                url TEXT NOT NULL,
                email TEXT NOT NULL,
                interval_hours INTEGER NOT NULL DEFAULT 24,
                css_selector TEXT,
                xpath TEXT,
                is_active INTEGER DEFAULT 1,
                last_content_hash TEXT,
                last_scraped TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        """)

        # Reminder History (track changes for reminders)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reminder_history (
                history_id TEXT PRIMARY KEY,
                reminder_id TEXT NOT NULL,
                old_content_preview TEXT,
                new_content_preview TEXT,
                change_summary TEXT,
                detected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

                FOREIGN KEY (reminder_id) REFERENCES reminders(reminder_id) ON DELETE CASCADE
            )
        """)


        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrape_configs_agent ON scrape_configs(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scrape_configs_auto ON scrape_configs(auto_scrape)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_agent ON subscriptions(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_subscriptions_active ON subscriptions(is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_change_history_agent ON change_history(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_conversations_agent ON conversations(agent_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_agents_user ON agents(user_id)")

        cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            reset_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            token TEXT NOT NULL UNIQUE,
            expires_at TEXT NOT NULL,
            used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
        """)

        # Postgres supports "ADD COLUMN IF NOT EXISTS" natively, so the
        # sqlite try/except-on-duplicate-column dance isn't needed anymore.
        cursor.execute("ALTER TABLE reminders ADD COLUMN IF NOT EXISTS user_id TEXT")

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id)")

        conn.commit()
        print("Database initialized successfully (Supabase/Postgres)")

init_database()