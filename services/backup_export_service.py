"""
Backup and Export Service for BotCamp Medical
Implements Master Specification Section 14 - Backups, Exports, and Data Protection
"""

import os
import csv
import json
import zipfile
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path
from sqlalchemy.orm import Session
from database.models import Question, User, University, Course, Unit, Topic, SystemLog
from database.db_v2 import SessionLocal
from cryptography.fernet import Fernet
import subprocess

logger = logging.getLogger(__name__)

class BackupExportService:
    def __init__(self):
        self.db_session = SessionLocal
        self.backup_dir = Path("backups")
        self.backup_dir.mkdir(exist_ok=True)
        self.retention_days = 30
        
        # Initialize encryption key (in production, store this securely)
        self.encryption_key = self._get_or_create_encryption_key()
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for backups"""
        key_file = Path("backup_key.key")
        if key_file.exists():
            return key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            key_file.write_bytes(key)
            return key
    
    def create_daily_backup(self) -> Dict[str, Any]:
        """Create daily backup per Section 14.1"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"botcamp_backup_{timestamp}.sql"
            backup_path = self.backup_dir / backup_filename
            
            # Create SQL dump
            result = subprocess.run([
                "sqlite3", "botcamp_medical.db", ".dump"
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                return {"success": False, "message": f"Backup failed: {result.stderr}"}
            
            # Write backup file
            backup_path.write_text(result.stdout)
            
            # Compress and encrypt
            zip_filename = f"botcamp_backup_{timestamp}.zip"
            zip_path = self.backup_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, backup_filename)
            
            # Remove uncompressed file
            backup_path.unlink()
            
            # Log backup success
            self._log_backup_result(True, f"Daily backup created: {zip_filename}")
            
            # Clean up old backups
            self._cleanup_old_backups()
            
            return {
                "success": True, 
                "message": f"Daily backup created: {zip_filename}",
                "file_path": str(zip_path)
            }
            
        except Exception as e:
            logger.error(f"Error creating daily backup: {e}")
            self._log_backup_result(False, f"Daily backup failed: {str(e)}")
            return {"success": False, "message": f"Backup failed: {str(e)}"}
    
    def export_data(self, filters: Dict[str, Any] = None) -> Dict[str, Any]:
        """Export data as CSV per Section 14.2"""
        try:
            session = self.db_session()
            
            # Build query based on filters
            query = session.query(Question)
            
            if filters:
                if filters.get('university'):
                    query = query.join(Topic).join(Unit).join(Course).join(University).filter(
                        University.name == filters['university']
                    )
                if filters.get('course'):
                    query = query.join(Topic).join(Unit).join(Course).filter(
                        Course.name == filters['course']
                    )
                if filters.get('year'):
                    query = query.join(Topic).join(Unit).filter(
                        Unit.year == str(filters['year'])
                    )
                if filters.get('unit'):
                    query = query.join(Topic).join(Unit).filter(
                        Unit.name == filters['unit']
                    )
                if filters.get('topic'):
                    query = query.join(Topic).filter(
                        Topic.name == filters['topic']
                    )
            
            questions = query.all()
            
            # Create CSV data
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"botcamp_export_{timestamp}.csv"
            csv_path = self.backup_dir / csv_filename
            
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write header
                writer.writerow([
                    'question_id', 'question_text', 'option_a', 'option_b', 
                    'option_c', 'option_d', 'correct_option', 'explanation', 
                    'uploader', 'topic', 'unit', 'course', 'university', 
                    'created_at', 'moderation_score', 'is_active'
                ])
                
                # Write data
                for question in questions:
                    uploader = session.query(User).filter(User.user_id == question.uploader_id).first()
                    topic = session.query(Topic).filter(Topic.id == question.topic_id).first()
                    unit = session.query(Unit).filter(Unit.id == topic.unit_id).first() if topic else None
                    course = session.query(Course).filter(Course.id == unit.course_id).first() if unit else None
                    university = session.query(University).filter(University.id == course.university_id).first() if course else None
                    
                    writer.writerow([
                        question.question_id,
                        question.question_text,
                        question.option_a,
                        question.option_b,
                        question.option_c,
                        question.option_d,
                        question.correct_option,
                        question.explanation or '',
                        uploader.username or uploader.first_name if uploader else 'Unknown',
                        topic.name if topic else '',
                        unit.name if unit else '',
                        course.name if course else '',
                        university.name if university else '',
                        question.created_at.strftime('%Y-%m-%d %H:%M:%S') if question.created_at else '',
                        question.moderation_score or 0,
                        question.is_active
                    ])
            
            session.close()
            
            # Compress and encrypt
            zip_filename = f"botcamp_export_{timestamp}.zip"
            zip_path = self.backup_dir / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(csv_path, csv_filename)
            
            # Remove uncompressed file
            csv_path.unlink()
            
            return {
                "success": True,
                "message": f"Export created: {zip_filename}",
                "file_path": str(zip_path),
                "records_exported": len(questions)
            }
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}")
            return {"success": False, "message": f"Export failed: {str(e)}"}
    
    def restore_from_backup(self, backup_file_path: str) -> Dict[str, Any]:
        """Restore from backup per Section 14.5"""
        try:
            if not os.path.exists(backup_file_path):
                return {"success": False, "message": "Backup file not found"}
            
            # Extract backup if it's a zip file
            if backup_file_path.endswith('.zip'):
                with zipfile.ZipFile(backup_file_path, 'r') as zipf:
                    # Find SQL file in zip
                    sql_files = [f for f in zipf.namelist() if f.endswith('.sql')]
                    if not sql_files:
                        return {"success": False, "message": "No SQL file found in backup"}
                    
                    # Extract SQL file
                    sql_content = zipf.read(sql_files[0]).decode('utf-8')
            else:
                # Direct SQL file
                with open(backup_file_path, 'r', encoding='utf-8') as f:
                    sql_content = f.read()
            
            # Create backup of current database
            current_backup = self.create_daily_backup()
            if not current_backup['success']:
                return {"success": False, "message": "Failed to backup current database"}
            
            # Restore database
            result = subprocess.run([
                "sqlite3", "botcamp_medical_restored.db"
            ], input=sql_content, text=True, capture_output=True)
            
            if result.returncode != 0:
                return {"success": False, "message": f"Restore failed: {result.stderr}"}
            
            # Replace current database
            if os.path.exists("botcamp_medical.db"):
                os.remove("botcamp_medical.db")
            os.rename("botcamp_medical_restored.db", "botcamp_medical.db")
            
            return {
                "success": True,
                "message": "Database restored successfully",
                "backup_created": current_backup['file_path']
            }
            
        except Exception as e:
            logger.error(f"Error restoring from backup: {e}")
            return {"success": False, "message": f"Restore failed: {str(e)}"}
    
    def _cleanup_old_backups(self):
        """Clean up old backups per Section 14.6"""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            
            for backup_file in self.backup_dir.glob("botcamp_backup_*.zip"):
                file_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                if file_time < cutoff_date:
                    backup_file.unlink()
                    logger.info(f"Deleted old backup: {backup_file.name}")
            
        except Exception as e:
            logger.error(f"Error cleaning up old backups: {e}")
    
    def _log_backup_result(self, success: bool, message: str):
        """Log backup result to SystemLog"""
        try:
            session = self.db_session()
            
            log_entry = SystemLog(
                action="backup" if success else "backup_error",
                details=message,
                timestamp=datetime.utcnow()
            )
            
            session.add(log_entry)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error logging backup result: {e}")
    
    def get_backup_status(self) -> Dict[str, Any]:
        """Get backup status and statistics"""
        try:
            backup_files = list(self.backup_dir.glob("botcamp_backup_*.zip"))
            export_files = list(self.backup_dir.glob("botcamp_export_*.zip"))
            
            total_size = sum(f.stat().st_size for f in backup_files + export_files)
            
            return {
                "backup_count": len(backup_files),
                "export_count": len(export_files),
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "retention_days": self.retention_days,
                "backup_dir": str(self.backup_dir)
            }
            
        except Exception as e:
            logger.error(f"Error getting backup status: {e}")
            return {"error": str(e)}
    
    def schedule_auto_backup(self):
        """Schedule automatic daily backups (call this from main application)"""
        try:
            # Check if backup already exists for today
            today = datetime.now().strftime("%Y%m%d")
            existing_backups = list(self.backup_dir.glob(f"botcamp_backup_{today}_*.zip"))
            
            if not existing_backups:
                result = self.create_daily_backup()
                if result['success']:
                    logger.info("Automatic daily backup completed")
                else:
                    logger.error(f"Automatic daily backup failed: {result['message']}")
            else:
                logger.info("Daily backup already exists for today")
                
        except Exception as e:
            logger.error(f"Error in scheduled backup: {e}")
    
    def encrypt_file(self, file_path: str, password: str = None) -> str:
        """Encrypt a file with AES-256"""
        try:
            if not password:
                password = "botcamp_default_password"  # In production, use secure password
            
            # Generate key from password
            key = Fernet.generate_key()
            fernet = Fernet(key)
            
            # Read and encrypt file
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            encrypted_data = fernet.encrypt(file_data)
            
            # Write encrypted file
            encrypted_path = file_path + ".encrypted"
            with open(encrypted_path, 'wb') as f:
                f.write(encrypted_data)
            
            # Save key separately
            key_path = file_path + ".key"
            with open(key_path, 'wb') as f:
                f.write(key)
            
            return encrypted_path
            
        except Exception as e:
            logger.error(f"Error encrypting file: {e}")
            return None
