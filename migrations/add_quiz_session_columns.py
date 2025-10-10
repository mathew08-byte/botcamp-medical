"""
Migration to add new columns to QuizSession table for Step 3 quiz engine.
"""
import sqlite3
import os
from pathlib import Path

def run_migration():
    """Add new columns to quiz_sessions table."""
    db_path = Path(__file__).parent.parent / "botcamp_medical.db"
    
    if not db_path.exists():
        print(f"Database not found at {db_path}")
        return
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(quiz_sessions)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add question_ids column if it doesn't exist
        if 'question_ids' not in columns:
            cursor.execute("ALTER TABLE quiz_sessions ADD COLUMN question_ids TEXT")
            print("Added question_ids column")
        else:
            print("question_ids column already exists")
        
        # Add score_percent column if it doesn't exist
        if 'score_percent' not in columns:
            cursor.execute("ALTER TABLE quiz_sessions ADD COLUMN score_percent INTEGER")
            print("Added score_percent column")
        else:
            print("score_percent column already exists")
        
        # Add grade column if it doesn't exist
        if 'grade' not in columns:
            cursor.execute("ALTER TABLE quiz_sessions ADD COLUMN grade VARCHAR")
            print("Added grade column")
        else:
            print("grade column already exists")
        
        conn.commit()
        print("Migration completed successfully!")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
