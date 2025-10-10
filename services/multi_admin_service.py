"""
Multi-Admin Coordination Service for BotCamp Medical
Implements Master Specification Section 13 - Multi-Admin Coordination and Conflict Handling
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import UploadBatch, UploadAudit, Question, User, AdminScope
from database.db_v2 import SessionLocal

logger = logging.getLogger(__name__)

class MultiAdminService:
    def __init__(self):
        self.db_session = SessionLocal
        self.lock_timeout_minutes = 15
    
    def create_upload_batch(self, uploader_id: int, questions_count: int = 0) -> Optional[int]:
        """Create a new upload batch"""
        try:
            session = self.db_session()
            
            batch = UploadBatch(
                uploader_id=uploader_id,
                questions_count=questions_count,
                status="draft"
            )
            
            session.add(batch)
            session.commit()
            session.refresh(batch)
            batch_id = batch.batch_id
            
            session.close()
            return batch_id
            
        except Exception as e:
            logger.error(f"Error creating upload batch: {e}")
            return None
    
    def lock_batch_for_review(self, batch_id: int, admin_id: int) -> Dict[str, Any]:
        """Lock a batch for review by an admin"""
        try:
            session = self.db_session()
            
            batch = session.query(UploadBatch).filter(UploadBatch.batch_id == batch_id).first()
            
            if not batch:
                session.close()
                return {"success": False, "message": "Batch not found"}
            
            # Check if already locked
            if batch.locked_by and batch.locked_by != admin_id:
                # Check if lock has expired
                if batch.locked_at and (datetime.utcnow() - batch.locked_at).total_seconds() < (self.lock_timeout_minutes * 60):
                    locker = session.query(User).filter(User.user_id == batch.locked_by).first()
                    locker_name = locker.username or locker.first_name if locker else "Unknown"
                    session.close()
                    return {
                        "success": False, 
                        "message": f"⚠️ This batch is currently being reviewed by @{locker_name}"
                    }
            
            # Lock the batch
            batch.locked_by = admin_id
            batch.locked_at = datetime.utcnow()
            batch.status = "review"
            
            session.commit()
            session.close()
            
            return {"success": True, "message": "Batch locked for review"}
            
        except Exception as e:
            logger.error(f"Error locking batch: {e}")
            return {"success": False, "message": "Error locking batch"}
    
    def unlock_batch(self, batch_id: int, admin_id: int) -> bool:
        """Unlock a batch (when review is complete or cancelled)"""
        try:
            session = self.db_session()
            
            batch = session.query(UploadBatch).filter(UploadBatch.batch_id == batch_id).first()
            
            if batch and batch.locked_by == admin_id:
                batch.locked_by = None
                batch.locked_at = None
                batch.status = "draft"
                session.commit()
            
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error unlocking batch: {e}")
            return False
    
    def get_available_batches_for_admin(self, admin_id: int) -> List[Dict[str, Any]]:
        """Get batches available for review by an admin"""
        try:
            session = self.db_session()
            
            # Get admin's scope
            admin_scope = session.query(AdminScope).filter(AdminScope.admin_id == admin_id).first()
            
            # Get batches that are either:
            # 1. Not locked by anyone
            # 2. Locked by this admin
            # 3. Locked but expired
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.lock_timeout_minutes)
            
            batches = session.query(UploadBatch).filter(
                (UploadBatch.locked_by.is_(None)) |
                (UploadBatch.locked_by == admin_id) |
                (UploadBatch.locked_at < cutoff_time)
            ).filter(UploadBatch.status.in_(["draft", "review"])).all()
            
            result = []
            for batch in batches:
                uploader = session.query(User).filter(User.user_id == batch.uploader_id).first()
                result.append({
                    "batch_id": batch.batch_id,
                    "uploader": uploader.username or uploader.first_name if uploader else "Unknown",
                    "questions_count": batch.questions_count,
                    "status": batch.status,
                    "locked_by": batch.locked_by,
                    "locked_at": batch.locked_at,
                    "created_at": batch.created_at
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting available batches: {e}")
            return []
    
    def get_admin_own_batches(self, admin_id: int) -> List[Dict[str, Any]]:
        """Get batches uploaded by the admin"""
        try:
            session = self.db_session()
            
            batches = session.query(UploadBatch).filter(
                UploadBatch.uploader_id == admin_id
            ).order_by(UploadBatch.created_at.desc()).all()
            
            result = []
            for batch in batches:
                result.append({
                    "batch_id": batch.batch_id,
                    "questions_count": batch.questions_count,
                    "status": batch.status,
                    "locked_by": batch.locked_by,
                    "created_at": batch.created_at,
                    "completed_at": batch.completed_at
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting admin own batches: {e}")
            return []
    
    def create_audit_record(self, upload_id: int, old_value: str, new_value: str, 
                          admin_id: int, action: str) -> bool:
        """Create audit trail record per Section 13.3"""
        try:
            session = self.db_session()
            
            audit = UploadAudit(
                upload_id=upload_id,
                old_value=old_value,
                new_value=new_value,
                admin_id=admin_id,
                action=action
            )
            
            session.add(audit)
            session.commit()
            session.close()
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating audit record: {e}")
            return False
    
    def get_audit_trail(self, upload_id: int) -> List[Dict[str, Any]]:
        """Get audit trail for a specific upload"""
        try:
            session = self.db_session()
            
            audits = session.query(UploadAudit).filter(
                UploadAudit.upload_id == upload_id
            ).order_by(UploadAudit.timestamp.desc()).all()
            
            result = []
            for audit in audits:
                admin = session.query(User).filter(User.user_id == audit.admin_id).first()
                result.append({
                    "audit_id": audit.audit_id,
                    "old_value": audit.old_value,
                    "new_value": audit.new_value,
                    "admin": admin.username or admin.first_name if admin else "Unknown",
                    "action": audit.action,
                    "timestamp": audit.timestamp
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting audit trail: {e}")
            return []
    
    def approve_batch(self, batch_id: int, admin_id: int) -> Dict[str, Any]:
        """Approve a batch and unlock it"""
        try:
            session = self.db_session()
            
            batch = session.query(UploadBatch).filter(UploadBatch.batch_id == batch_id).first()
            
            if not batch:
                session.close()
                return {"success": False, "message": "Batch not found"}
            
            if batch.locked_by != admin_id:
                session.close()
                return {"success": False, "message": "You don't have permission to approve this batch"}
            
            # Approve the batch
            batch.status = "approved"
            batch.completed_at = datetime.utcnow()
            batch.locked_by = None
            batch.locked_at = None
            
            # Update all questions in this batch
            questions = session.query(Question).filter(
                Question.uploader_id == batch.uploader_id,
                Question.created_at >= batch.created_at
            ).all()
            
            for question in questions:
                question.is_active = True
                question.needs_review = False
            
            session.commit()
            session.close()
            
            return {"success": True, "message": f"Batch approved. {len(questions)} questions activated."}
            
        except Exception as e:
            logger.error(f"Error approving batch: {e}")
            return {"success": False, "message": "Error approving batch"}
    
    def reject_batch(self, batch_id: int, admin_id: int, reason: str = "") -> Dict[str, Any]:
        """Reject a batch and unlock it"""
        try:
            session = self.db_session()
            
            batch = session.query(UploadBatch).filter(UploadBatch.batch_id == batch_id).first()
            
            if not batch:
                session.close()
                return {"success": False, "message": "Batch not found"}
            
            if batch.locked_by != admin_id:
                session.close()
                return {"success": False, "message": "You don't have permission to reject this batch"}
            
            # Reject the batch
            batch.status = "rejected"
            batch.completed_at = datetime.utcnow()
            batch.locked_by = None
            batch.locked_at = None
            
            # Deactivate all questions in this batch
            questions = session.query(Question).filter(
                Question.uploader_id == batch.uploader_id,
                Question.created_at >= batch.created_at
            ).all()
            
            for question in questions:
                question.is_active = False
                question.needs_review = False
            
            session.commit()
            session.close()
            
            return {"success": True, "message": f"Batch rejected. {len(questions)} questions deactivated."}
            
        except Exception as e:
            logger.error(f"Error rejecting batch: {e}")
            return {"success": False, "message": "Error rejecting batch"}
    
    def cleanup_expired_locks(self) -> int:
        """Clean up expired locks (run periodically)"""
        try:
            session = self.db_session()
            
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.lock_timeout_minutes)
            
            expired_batches = session.query(UploadBatch).filter(
                UploadBatch.locked_at < cutoff_time,
                UploadBatch.status == "review"
            ).all()
            
            count = 0
            for batch in expired_batches:
                batch.locked_by = None
                batch.locked_at = None
                batch.status = "draft"
                count += 1
            
            session.commit()
            session.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired locks: {e}")
            return 0
    
    def get_admin_scope(self, admin_id: int) -> Optional[Dict[str, Any]]:
        """Get admin's scope (university/course)"""
        try:
            session = self.db_session()
            
            scope = session.query(AdminScope).filter(AdminScope.admin_id == admin_id).first()
            
            if not scope:
                session.close()
                return None
            
            result = {
                "admin_id": admin_id,
                "university_id": scope.university_id,
                "course_id": scope.course_id,
                "university": scope.university.name if scope.university else None,
                "course": scope.course.name if scope.course else None
            }
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting admin scope: {e}")
            return None
