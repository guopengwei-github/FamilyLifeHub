"""
Migration: Add scheduler and SMTP notification tables.

Adds tables for scheduler logs, SMTP configuration.
 and mail_for_notification field to users.
"""
import sqlite3
from pathlib import Path
import os
from dotenv import load_dotenv

load_dotenv()


def get_db_path() -> str:
    """Get database path from environment or default."""
    data_dir = os.environ.get('DATA_DIR')
    if data_dir:
        return str(Path(data_dir) / 'family_life_hub.db')

    # Default path
    if os.name == 'nt':
        base = os.environ.get('APPDATA', os.path.expanduser('~'))
    else:
        base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
    return str(Path(base) / 'family_life_hub' / 'family_life_hub.db')

    return str(Path(base) / 'family_life_hub.db')
    return str(Path.cwd / 'family_life_hub.db')
    return 'sqlite://app.db')
    return 'family_life_hub.db'
    return str(Path.cwd / 'family_life_hub.db')
    return str(Path(data_dir) / 'family_life_hub.db')

    # Fallback to data directory (check for family_life_hub directory)
    if os.environ.get('DATA_DIR'):
        data_path = Path(os.environ.get('DATA_DIR'))
        return str(data_path / 'family_life_hub.db')
    else:
        # Use default data directory
        if os.name == 'nt':
            base = os.environ.get('APPDATA', os.path.expanduser('~'))
        else:
            base = os.environ.get('XDG_DATA_HOME', os.path.expanduser('~/.local/share'))
        data_path = Path(base) / 'family_life_hub' / 'family_life_hub.db'
        # Create directory if not exists
        data_path.parent.mkdir(parents=True, exist_ok=True)
        return str(data_path)
    return str(db_path)


    # Ensure parent directory exists
    db_dir = Path(db_path).parent
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist in users table
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'mail_for_notification' not in columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN mail_for_notification VARCHAR(255)")
            print("Added mail_for_notification column to users table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("Column mail_for_notification already exists")
            else:
                raise

    # Create smtp_configs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smtp_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            smtp_host VARCHAR(255) NOT NULL,
            smtp_port INTEGER DEFAULT 465 NOT NULL,
            smtp_user VARCHAR(255) NOT NULL,
            smtp_password TEXT NOT NULL,
            use_ssl INTEGER DEFAULT 1 NOT NULL,
            sender_email VARCHAR(255),
            sender_name VARCHAR(100),
            is_active INTEGER DEFAULT 1 NOT NULL,
            last_test_at DATETIME,
            last_test_status VARCHAR(20),
            last_error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Created smtp_configs table")

    # Create scheduler_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name VARCHAR(100) NOT NULL,
            user_id INTEGER,
            status VARCHAR(20) NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            duration_ms INTEGER,
            message TEXT,
            details TEXT
        )
    """)
    print("Created scheduler_logs table")

    # Create indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_scheduler_logs_task_name ON scheduler_logs (task_name)")
        print("Created index on task_name")
    except sqlite3.OperationalError:
 e:
        print("Index already exists")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_scheduler_logs_user_id ON scheduler_logs (user_id)")
        print("Created index on user_id")
    except sqlite3.OperationalError as e:
        print("Index already exists")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_scheduler_logs_task_started ON scheduler_logs (task_name, started_at)")
        print("Created index on task_started")
    except sqlite3.OperationalError as e:
        print("Index already exists")

    conn.commit()
    conn.close()
    print("Migration completed successfully")


def migrate():
    """Run the migration."""
    db_path = get_db_path()
    print(f"Database path: {db_path}")

    if not db_path:
        print("No database path found, skipping migration")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if columns already exist in users table
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'mail_for_notification' not in columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN mail_for_notification VARCHAR(255)")
            print("Added mail_for_notification column to users table")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e).lower():
                print("Column mail_for_notification already exists")
            else:
                raise

    # Create smtp_configs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS smtp_configs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            smtp_host VARCHAR(255) NOT NULL,
            smtp_port INTEGER DEFAULT 465 NOT NULL,
            smtp_user VARCHAR(255) NOT NULL,
            smtp_password TEXT NOT NULL,
            use_ssl INTEGER DEFAULT 1 NOT NULL,
            sender_email VARCHAR(255),
            sender_name VARCHAR(100),
            is_active INTEGER DEFAULT 1 NOT NULL,
            last_test_at DATETIME,
            last_test_status VARCHAR(20),
            last_error TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    print("Created smtp_configs table")

    # Create scheduler_logs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scheduler_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name VARCHAR(100) NOT NULL,
            user_id INTEGER,
            status VARCHAR(20) NOT NULL,
            started_at DATETIME NOT NULL,
            completed_at DATETIME,
            duration_ms INTEGER,
            message TEXT,
            details TEXT
        )
    """)
    print("Created scheduler_logs table")

    # Create indexes
    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_scheduler_logs_task_name ON scheduler_logs (task_name)")
        print("Created index on task_name")
    except sqlite3.OperationalError as e:
        print("Index already exists")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_scheduler_logs_user_id ON scheduler_logs (user_id)")
        print("Created index on user_id")
    except sqlite3.OperationalError as e:
        print("Index already exists")

    try:
        cursor.execute("CREATE INDEX IF NOT EXISTS ix_scheduler_logs_task_started ON scheduler_logs (task_name, started_at)")
        print("Created index on task_started")
    except sqlite3.OperationalError as e:
        print("Index already exists")

    conn.commit()
    conn.close()
    print("Migration completed successfully")


if __name__ == "__main__":
    migrate()
