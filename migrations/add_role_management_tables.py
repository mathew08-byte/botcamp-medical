"""
Migration to add Role Management tables for Part 4
"""

import sqlite3
import os
from pathlib import Path
from datetime import datetime

def run_migration():
    """Add new tables for Role Management (Part 4)"""
    
    # Get database path
    db_path = Path(__file__).parent.parent / "botcamp_medical.db"
    
    if not db_path.exists():
        print("Database not found, skipping migration")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Create AdminAccessCode table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS admin_access_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                created_by INTEGER,
                is_active BOOLEAN DEFAULT 1,
                used_by INTEGER,
                used_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                FOREIGN KEY (created_by) REFERENCES users (user_id),
                FOREIGN KEY (used_by) REFERENCES users (user_id)
            )
        """)
        print("Created admin_access_codes table")
        
        # Create QuestionUpload table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS question_uploads (
                upload_id INTEGER PRIMARY KEY AUTOINCREMENT,
                uploaded_by INTEGER,
                approved_by INTEGER,
                upload_type TEXT NOT NULL,
                ai_processed BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'pending',
                questions_count INTEGER DEFAULT 0,
                ai_confidence REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed_at TIMESTAMP,
                approved_at TIMESTAMP,
                FOREIGN KEY (uploaded_by) REFERENCES users (user_id),
                FOREIGN KEY (approved_by) REFERENCES users (user_id)
            )
        """)
        print("Created question_uploads table")
        
        # Create RoleAuditLog table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS role_audit_logs (
                log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                old_role TEXT,
                new_role TEXT,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        print("Created role_audit_logs table")
        
        # Update users table to ensure role column exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'student'")
            print("Added role column to users table")
        except sqlite3.OperationalError:
            print("Role column already exists in users table")
        
        # Update users table to ensure is_active column exists
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT 1")
            print("Added is_active column to users table")
        except sqlite3.OperationalError:
            print("is_active column already exists in users table")
        
        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_access_codes_code ON admin_access_codes (code)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_access_codes_created_by ON admin_access_codes (created_by)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_admin_access_codes_is_active ON admin_access_codes (is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_uploads_uploaded_by ON question_uploads (uploaded_by)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_uploads_status ON question_uploads (status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_role_audit_logs_user_id ON role_audit_logs (user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_role_audit_logs_action ON role_audit_logs (action)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users (role)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_is_active ON users (is_active)")
        print("Created indexes")
        
        # Create a default super admin user if none exists
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'super_admin'")
        super_admin_count = cursor.fetchone()[0]
        
        if super_admin_count == 0:
            # Create a default super admin (you should change this in production)
            cursor.execute("""
                INSERT INTO users (telegram_id, username, first_name, role, is_active, created_at)
                VALUES (123456789, 'superadmin', 'Super Admin', 'super_admin', 1, ?)
            """, (datetime.now(),))
            print("Created default super admin user (ID: 123456789)")
            print("⚠️  IMPORTANT: Change the super admin credentials in production!")
        
        conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
