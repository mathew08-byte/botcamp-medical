"""
Migration to add Master Specification tables (Sections 11-15)
"""

import sqlite3
import os
from pathlib import Path

def run_migration():
    """Add new tables for Master Specification Sections 11-15"""
    
    # Get database path
    db_path = Path(__file__).parent.parent / "botcamp_medical.db"
    
    if not db_path.exists():
        print("Database not found, skipping migration")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Create UserState table (Section 12)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                role TEXT NOT NULL,
                university TEXT,
                course TEXT,
                year INTEGER,
                unit TEXT,
                topic TEXT,
                last_action TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("Created user_states table")
        
        # Create UploadBatch table (Section 13)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_batches (
                batch_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploader_id INTEGER,
                status TEXT DEFAULT 'draft',
                locked_by INTEGER,
                locked_at TIMESTAMP,
                questions_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (uploader_id) REFERENCES users (user_id),
                FOREIGN KEY (locked_by) REFERENCES users (user_id)
            )
        """)
        print("Created upload_batches table")
        
        # Create UploadAudit table (Section 13)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upload_audits (
                audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                upload_id INTEGER,
                old_value TEXT,
                new_value TEXT,
                admin_id INTEGER,
                action TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (upload_id) REFERENCES questions (question_id),
                FOREIGN KEY (admin_id) REFERENCES users (user_id)
            )
        """)
        print("Created upload_audits table")
        
        # Create AdminScope table (Section 15)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_scopes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_id INTEGER,
                university_id INTEGER,
                course_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (admin_id) REFERENCES users (user_id),
                FOREIGN KEY (university_id) REFERENCES universities (id),
                FOREIGN KEY (course_id) REFERENCES courses (id)
            )
        """)
        print("Created admin_scopes table")
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_states_role ON user_states (role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_batches_status ON upload_batches (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_batches_locked_by ON upload_batches (locked_by)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_upload_audits_upload_id ON upload_audits (upload_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_scopes_admin_id ON admin_scopes (admin_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_scopes_university_id ON admin_scopes (university_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_scopes_course_id ON admin_scopes (course_id)")
        print("Created indexes")
        
        # Create backups directory
        backup_dir = Path(__file__).parent.parent / "backups"
        backup_dir.mkdir(exist_ok=True)
        print("Created backups directory")
        
        conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
