"""
Migration: Add mail_for_notification column to users table.
"""
import sqlite3
from pathlib import Path


def get_db_path() -> str:
    """Get database path from environment or default."""
    import os
    from dotenv import load_dotenv
    load_dotenv()

    data_dir = os.environ.get('DATA_DIR')
    if data_dir:
        return str(Path(data_dir) / 'family_life_hub.db')

    # Default path
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    return str(Path(base) / 'family_life_hub' / 'family_life_hub.db')


def migrate():
    """Add mail_for_notification column to users table."""
    db_path = get_db_path()
    print(f"Database path: {db_path}")

    if not Path(db_path).exists():
        print("Database file not found, skipping migration")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'mail_for_notification' in columns:
        print("Column mail_for_notification already exists, skipping migration")
        conn.close()
        return

    # Add the column
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN mail_for_notification VARCHAR(255)")
        print("Added column: mail_for_notification")
        conn.commit()
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column mail_for_notification already exists")
        else:
            raise

    conn.close()
    print("Migration completed successfully")


if __name__ == "__main__":
    migrate()
