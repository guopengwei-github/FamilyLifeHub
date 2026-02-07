"""
Add missing garmin_oauth_tokens column to garmin_connections table.
Run this script to update the database schema.
"""
import sqlite3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def migrate():
    """Add missing garmin_oauth_tokens column to garmin_connections table."""
    db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")

    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if column already exists
        cursor.execute("PRAGMA table_info(garmin_connections)")
        columns = [col[1] for col in cursor.fetchall()]

        if "garmin_oauth_tokens" in columns:
            print("Database schema is up to date. No migration needed.")
            return True

        # Add missing column
        sql = "ALTER TABLE garmin_connections ADD COLUMN garmin_oauth_tokens TEXT"
        cursor.execute(sql)
        print(f"Added column: garmin_oauth_tokens TEXT")

        conn.commit()
        print("Migration completed successfully!")
        return True

    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    success = migrate()
    sys.exit(0 if success else 1)
