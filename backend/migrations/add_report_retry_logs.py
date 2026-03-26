"""
Migration: Add report_retry_logs table

Creates table for tracking report generation retries when Garmin data is stale.
"""
from sqlalchemy import create_engine, text
from app.core.config import settings


def upgrade():
    """Create report_retry_logs table using raw SQL."""
    engine = create_engine(settings.database_path)
    
    with engine.connect() as conn:
        # Check if table already exists
        result = conn.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='report_retry_logs'"
        ))
        if result.fetchone():
            print("[OK] Table report_retry_logs already exists")
            return
        
        # Create table
        conn.execute(text("""
            CREATE TABLE report_retry_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                report_type VARCHAR(20) NOT NULL,
                report_date DATE NOT NULL,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 3,
                next_retry_at DATETIME,
                last_retry_at DATETIME,
                status VARCHAR(20) NOT NULL DEFAULT 'pending',
                last_error TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """))
        
        # Create indexes
        conn.execute(text(
            "CREATE INDEX ix_report_retry_logs_id ON report_retry_logs(id)"
        ))
        conn.execute(text(
            "CREATE INDEX ix_report_retry_logs_user_id ON report_retry_logs(user_id)"
        ))
        conn.execute(text(
            "CREATE INDEX ix_report_retry_logs_report_date ON report_retry_logs(report_date)"
        ))
        conn.execute(text(
            "CREATE INDEX ix_report_retry_logs_user_date ON report_retry_logs(user_id, report_date)"
        ))
        conn.execute(text(
            "CREATE INDEX ix_report_retry_logs_next_retry ON report_retry_logs(next_retry_at, status)"
        ))
        
        conn.commit()
        print("[OK] Created report_retry_logs table")


def downgrade():
    """Drop report_retry_logs table."""
    engine = create_engine(settings.database_path)
    
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS report_retry_logs"))
        conn.commit()
        print("[OK] Dropped report_retry_logs table")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'downgrade':
        downgrade()
    else:
        upgrade()
