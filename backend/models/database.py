# backend/models/database.py

import sqlite3
from contextlib import contextmanager
import os

# Database file location
DATABASE_PATH = "E:/web_scraper/data/agents.db"

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)


@contextmanager
def get_db_connection():
    """
    Usage:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM agents")
    
    This ensures connections are always closed, even if errors occur.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        yield conn  # Give the connection to the code block
    finally:
        conn.close()  # Always close connection when done


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
        
        # ✅ UPDATED: Scrape configs with scheduler
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
        
        # ✅ NEW: Email subscriptions for agents
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
        
        # ✅ NEW: Change history for tracking updates
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


        try:
            cursor.execute("ALTER TABLE reminders ADD COLUMN user_id TEXT")
            print("✅ Migrated: added user_id column to reminders table")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise  # unexpected error — don't swallow it silently

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_reminders_user ON reminders(user_id)")

        conn.commit()
        print("✅ Database initialized successfully at:", DATABASE_PATH)

init_database()