"""One-off SQLite migration: add email columns to clients."""
import os
import sqlite3

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.path.join(ROOT_DIR, 'gym_tracker.db')


def migrate():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE clients ADD COLUMN email VARCHAR(120)")
        cursor.execute("ALTER TABLE clients ADD COLUMN send_email_reminders BOOLEAN DEFAULT 0")
        conn.commit()
        print("Migration successful: added email and send_email_reminders columns.")
    except Exception as e:
        if "duplicate column name" in str(e).lower():
            print("Columns already exist, migration skipped.")
        else:
            conn.rollback()
            print(f"Error during migration: {e}")
    finally:
        conn.close()


if __name__ == '__main__':
    migrate()
