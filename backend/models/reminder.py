# backend/models/reminder.py

import uuid
from datetime import datetime
from backend.models.database import get_db_connection


class Reminder:
    """Standalone reminder model for URL monitoring"""
    
    def __init__(self, reminder_id, url, email, interval_hours=24, 
                 css_selector=None, xpath=None, is_active=1, 
                 last_content_hash=None, last_scraped=None, 
                 created_at=None, updated_at=None, user_id=None):
        self.reminder_id = reminder_id
        self.user_id = user_id
        self.url = url
        self.email = email
        self.interval_hours = interval_hours
        self.css_selector = css_selector
        self.xpath = xpath
        self.is_active = is_active
        self.last_content_hash = last_content_hash
        self.last_scraped = last_scraped
        self.created_at = created_at
        self.updated_at = updated_at
    
    @staticmethod
    def create(user_id, url, email, interval_hours=24, css_selector=None, xpath=None):
        """Create a new reminder, owned by user_id"""
        reminder_id = str(uuid.uuid4())
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminders 
                (reminder_id, user_id, url, email, interval_hours, css_selector, xpath)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (reminder_id, user_id, url, email, interval_hours, css_selector, xpath))
            conn.commit()
        
        return Reminder.get_by_id(reminder_id)
    
    @staticmethod
    def get_by_id(reminder_id):
        """Get reminder by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reminders WHERE reminder_id = ?", (reminder_id,))
            row = cursor.fetchone()
            
            if row:
                return Reminder(**dict(row))
            return None

    @staticmethod
    def get_by_user(user_id, active_only=True):
        """Get all reminders belonging to a specific user"""
        with get_db_connection() as conn:
            cursor = conn.cursor()

            if active_only:
                cursor.execute(
                    "SELECT * FROM reminders WHERE user_id = ? AND is_active = 1 ORDER BY created_at DESC",
                    (user_id,)
                )
            else:
                cursor.execute(
                    "SELECT * FROM reminders WHERE user_id = ? ORDER BY created_at DESC",
                    (user_id,)
                )

            rows = cursor.fetchall()
            return [Reminder(**dict(row)) for row in rows]
    
    @staticmethod
    def get_all(active_only=True):
        """Get all reminders"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            if active_only:
                cursor.execute(
                    "SELECT * FROM reminders WHERE is_active = 1 ORDER BY created_at DESC"
                )
            else:
                cursor.execute("SELECT * FROM reminders ORDER BY created_at DESC")
            
            rows = cursor.fetchall()
            return [Reminder(**dict(row)) for row in rows]
    
    @staticmethod
    def get_by_email(email):
        """Get all reminders for an email"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM reminders WHERE email = ? ORDER BY created_at DESC",
                (email,)
            )
            rows = cursor.fetchall()
            return [Reminder(**dict(row)) for row in rows]
    
    @staticmethod
    def get_all_active():
        """Get all active reminders for scheduling"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reminders WHERE is_active = 1")
            rows = cursor.fetchall()
            return [Reminder(**dict(row)) for row in rows]
    
    def update(self, **kwargs):
        """Update reminder fields"""
        allowed_fields = ['url', 'email', 'interval_hours', 'css_selector', 
                         'xpath', 'is_active', 'last_content_hash', 'last_scraped']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        updates['updated_at'] = datetime.now().isoformat()
        
        if not updates:
            return
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [self.reminder_id]
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE reminders SET {set_clause} WHERE reminder_id = ?",
                values
            )
            conn.commit()
        
        for k, v in updates.items():
            setattr(self, k, v)
    
    @staticmethod
    def delete(reminder_id):
        """Delete a reminder"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reminders WHERE reminder_id = ?", (reminder_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'reminder_id': self.reminder_id,
            'user_id': self.user_id,
            'url': self.url,
            'email': self.email,
            'interval_hours': self.interval_hours,
            'css_selector': self.css_selector,
            'xpath': self.xpath,
            'is_active': bool(self.is_active),
            'last_content_hash': self.last_content_hash,
            'last_scraped': self.last_scraped,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def __repr__(self):
        return f"<Reminder {self.reminder_id}: {self.url}>"


class ReminderHistory:
    """Track content changes for reminders"""
    
    def __init__(self, history_id, reminder_id, old_content_preview=None,
                 new_content_preview=None, change_summary=None, detected_at=None):
        self.history_id = history_id
        self.reminder_id = reminder_id
        self.old_content_preview = old_content_preview
        self.new_content_preview = new_content_preview
        self.change_summary = change_summary
        self.detected_at = detected_at
    
    @staticmethod
    def create(reminder_id, old_content, new_content, change_summary):
        """Record a detected change"""
        history_id = str(uuid.uuid4())
        
        old_preview = old_content[:500] if old_content else ""
        new_preview = new_content[:500] if new_content else ""
        
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO reminder_history 
                (history_id, reminder_id, old_content_preview, 
                 new_content_preview, change_summary)
                VALUES (?, ?, ?, ?, ?)
            """, (history_id, reminder_id, old_preview, new_preview, change_summary))
            conn.commit()
        
        return ReminderHistory.get_by_id(history_id)
    
    @staticmethod
    def get_by_id(history_id):
        """Get history by ID"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM reminder_history WHERE history_id = ?", (history_id,))
            row = cursor.fetchone()
            
            if row:
                return ReminderHistory(**dict(row))
            return None
    
    @staticmethod
    def get_by_reminder(reminder_id, limit=10):
        """Get recent changes for a reminder"""
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM reminder_history 
                   WHERE reminder_id = ? 
                   ORDER BY detected_at DESC 
                   LIMIT ?""",
                (reminder_id, limit)
            )
            rows = cursor.fetchall()
            return [ReminderHistory(**dict(row)) for row in rows]
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'history_id': self.history_id,
            'reminder_id': self.reminder_id,
            'old_content_preview': self.old_content_preview,
            'new_content_preview': self.new_content_preview,
            'change_summary': self.change_summary,
            'detected_at': self.detected_at
        }