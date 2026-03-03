"""
Migration: Add user profile fields for health reports.

Adds age, gender, weight_kg columns to users table.
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
    """Add user profile columns to users table."""
    db_path = get_db_path()
    print(f"Database path: {db_path}")

    if not Path(db_path).exists():
        print("Database file not found, skipping migration")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    migrations_needed = []

    if 'age' not in columns:
        migrations_needed.append(('age', 'INTEGER'))

    if 'gender' not in columns:
        migrations_needed.append(('gender', 'VARCHAR(10)'))

    if 'weight_kg' not in columns:
        migrations_needed.append(('weight_kg', 'REAL'))

    if 'birth_date' not in columns:
        migrations_needed.append(('birth_date', 'DATE'))

    if 'height_cm' not in columns:
        migrations_needed.append(('height_cm', 'REAL'))

    if not migrations_needed:
        print("User profile columns already exist, skipping migration")
        conn.close()
        return

    # Add missing columns
    for col_name, col_type in migrations_needed:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column: {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print(f"Column {col_name} already exists")
            else:
                raise

    # Create health_reports table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            report_date DATE NOT NULL,
            report_type VARCHAR(20) NOT NULL,
            input_context TEXT,
            content TEXT NOT NULL,
            generated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            llm_model VARCHAR(50),
            retry_count INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Created health_reports table (if not exists)")

    # Create unique index
    try:
        cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS uq_user_date_type
            ON health_reports (user_id, report_date, report_type)
        """)
        print("Created unique index on health_reports")
    except sqlite3.OperationalError:
        print("Index already exists")

    conn.commit()
    conn.close()
    print("Migration completed successfully")


if __name__ == "__main__":
    migrate()
