"""
Migration: Add body_battery_before_sleep column to health_metrics table.

Adds column to store body battery value before sleep for sleep recovery tracking.
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
    """Add body_battery_before_sleep column to health_metrics table."""
    db_path = get_db_path()
    print(f"Database path: {db_path}")

    if not Path(db_path).exists():
        print("Database file not found, skipping migration")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if column already exists
    cursor.execute("PRAGMA table_info(health_metrics)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'body_battery_before_sleep' in columns:
        print("Column body_battery_before_sleep already exists, skipping migration")
        conn.close()
        return

    # Add the column
    try:
        cursor.execute("ALTER TABLE health_metrics ADD COLUMN body_battery_before_sleep INTEGER")
        print("Added column: body_battery_before_sleep")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e).lower():
            print("Column body_battery_before_sleep already exists")
        else:
            raise

    conn.commit()
    conn.close()
    print("Migration completed successfully")


if __name__ == "__main__":
    migrate()
