"""
Add missing strava_client_id and strava_client_secret columns to strava_connections table.
Run this script to update the database schema.
"""
import sqlite3
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.config import settings


def migrate():
    """Add missing columns to strava_connections table."""
    db_path = settings.database_url.replace("sqlite:///", "").replace("sqlite://", "")

    if not os.path.exists(db_path):
        print(f"Database not found at: {db_path}")
        return False

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(strava_connections)")
        columns = [col[1] for col in cursor.fetchall()]

        columns_to_add = []
        if "strava_client_id" not in columns:
            columns_to_add.append("strava_client_id TEXT")
        if "strava_client_secret" not in columns:
            columns_to_add.append("strava_client_secret TEXT")

        if not columns_to_add:
            print("Database schema is up to date. No migration needed.")
            return True

        # Add missing columns
        for column_def in columns_to_add:
            sql = f"ALTER TABLE strava_connections ADD COLUMN {column_def}"
            cursor.execute(sql)
            print(f"Added column: {column_def}")

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
