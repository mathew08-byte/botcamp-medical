"""
Migration to add moderation and analytics fields to existing tables
"""

import sqlite3
import os
from pathlib import Path

def run_migration():
    """Add missing fields for moderation and analytics"""
    
    # Get database path
    db_path = Path(__file__).parent.parent / "botcamp_medical.db"
    
    if not db_path.exists():
        print("Database not found, skipping migration")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Add topic_accuracy_breakdown to quiz_sessions if it doesn't exist
        cursor.execute("PRAGMA table_info(quiz_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'topic_accuracy_breakdown' not in columns:
            cursor.execute("ALTER TABLE quiz_sessions ADD COLUMN topic_accuracy_breakdown TEXT")
            print("Added topic_accuracy_breakdown column to quiz_sessions")
        
        # Ensure all moderation fields exist in questions table
        cursor.execute("PRAGMA table_info(questions)")
        question_columns = [column[1] for column in cursor.fetchall()]
        
        moderation_fields = [
            ('moderation_score', 'INTEGER'),
            ('moderation_comments', 'TEXT'),
            ('moderated_by_ai', 'BOOLEAN'),
            ('needs_review', 'BOOLEAN'),
            ('reviewed_by_admin_id', 'INTEGER')
        ]
        
        for field_name, field_type in moderation_fields:
            if field_name not in question_columns:
                cursor.execute(f"ALTER TABLE questions ADD COLUMN {field_name} {field_type}")
                print(f"Added {field_name} column to questions")
        
        # Ensure all analytics fields exist in users table
        cursor.execute("PRAGMA table_info(users)")
        user_columns = [column[1] for column in cursor.fetchall()]
        
        analytics_fields = [
            ('upload_count', 'INTEGER DEFAULT 0'),
            ('approved_count', 'INTEGER DEFAULT 0'),
            ('flagged_count', 'INTEGER DEFAULT 0'),
            ('rejected_count', 'INTEGER DEFAULT 0'),
            ('average_moderation_score', 'INTEGER'),
            ('total_quizzes_taken', 'INTEGER DEFAULT 0'),
            ('average_accuracy', 'INTEGER')
        ]
        
        for field_name, field_type in analytics_fields:
            if field_name not in user_columns:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                print(f"Added {field_name} column to users")
        
        conn.commit()
        print("Migration completed successfully")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
