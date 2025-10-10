"""
Role Management Service for BotCamp Medical
Implements Part 4 - Dynamic Role Management and Access Control
"""

import logging
import secrets
import hashlib
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import User, AdminAccessCode, QuestionUpload, RoleAuditLog, AdminScope
from database.db_v2 import SessionLocal
from cryptography.fernet import Fernet

logger = logging.getLogger(__name__)

class RoleManagementService:
    def __init__(self):
        self.db_session = SessionLocal
        self.encryption_key = self._get_or_create_encryption_key()
        self.fernet = Fernet(self.encryption_key)
    
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key for access codes"""
        import os
        key_file = "role_encryption.key"
        if os.path.exists(key_file):
            return open(key_file, 'rb').read()
        else:
            key = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key)
            return key
    
    def _encrypt_code(self, code: str) -> str:
        """Encrypt access code"""
        return self.fernet.encrypt(code.encode()).decode()
    
    def _decrypt_code(self, encrypted_code: str) -> str:
        """Decrypt access code"""
        return self.fernet.decrypt(encrypted_code.encode()).decode()
    
    def generate_admin_access_code(self, created_by: int, expires_hours: int = 24) -> Dict[str, Any]:
        """Generate a new admin access code per Part 4"""
        try:
            session = self.db_session()
            
            # Generate secure random code
            code = secrets.token_urlsafe(16)
            encrypted_code = self._encrypt_code(code)
            
            # Set expiration
            expires_at = datetime.utcnow() + timedelta(hours=expires_hours)
            
            access_code = AdminAccessCode(
                code=encrypted_code,
                created_by=created_by,
                expires_at=expires_at
            )
            
            session.add(access_code)
            session.commit()
            session.refresh(access_code)
            
            # Log the action
            self._log_role_action(
                created_by, 
                "admin_code_generated", 
                details=f"Generated admin access code: {access_code.id}"
            )
            
            session.close()
            
            return {
                "success": True,
                "code": code,  # Return unencrypted code for display
                "code_id": access_code.id,
                "expires_at": expires_at,
                "message": f"Admin access code generated: {code}"
            }
            
        except Exception as e:
            logger.error(f"Error generating admin access code: {e}")
            return {"success": False, "message": f"Error generating code: {str(e)}"}
    
    def verify_admin_access_code(self, code: str, user_id: int) -> Dict[str, Any]:
        """Verify admin access code and grant admin role"""
        try:
            session = self.db_session()
            
            # Find active, unused code
            access_codes = session.query(AdminAccessCode).filter(
                AdminAccessCode.is_active == True,
                AdminAccessCode.used_by.is_(None),
                AdminAccessCode.expires_at > datetime.utcnow()
            ).all()
            
            for access_code in access_codes:
                try:
                    decrypted_code = self._decrypt_code(access_code.code)
                    if decrypted_code == code:
                        # Code matches, grant admin role
                        user = session.query(User).filter(User.user_id == user_id).first()
                        if not user:
                            session.close()
                            return {"success": False, "message": "User not found"}
                        
                        old_role = user.role
                        user.role = "admin"
                        
                        # Mark code as used
                        access_code.used_by = user_id
                        access_code.used_at = datetime.utcnow()
                        
                        session.commit()
                        
                        # Log the role change
                        self._log_role_action(
                            user_id,
                            "role_change",
                            old_role=old_role,
                            new_role="admin",
                            details=f"Admin access granted via code: {access_code.id}"
                        )
                        
                        session.close()
                        
                        return {
                            "success": True,
                            "message": f"✅ Welcome Admin {user.first_name or user.username}! You can now upload and review questions.",
                            "new_role": "admin"
                        }
                except Exception:
                    continue  # Try next code
            
            session.close()
            return {"success": False, "message": "❌ Invalid or expired access code"}
            
        except Exception as e:
            logger.error(f"Error verifying admin access code: {e}")
            return {"success": False, "message": "Error verifying access code"}
    
    def verify_super_admin_key(self, key: str, user_id: int) -> Dict[str, Any]:
        """Verify super admin master key"""
        try:
            # Get super admin key from environment or config
            import os
            master_key = os.getenv("SUPER_ADMIN_KEY", "superadmin456")  # Default for development
            
            if key == master_key:
                session = self.db_session()
                user = session.query(User).filter(User.user_id == user_id).first()
                
                if user:
                    old_role = user.role
                    user.role = "super_admin"
                    session.commit()
                    
                    # Log the role change
                    self._log_role_action(
                        user_id,
                        "role_change",
                        old_role=old_role,
                        new_role="super_admin",
                        details="Super admin access granted via master key"
                    )
                    
                    session.close()
                    
                    return {
                        "success": True,
                        "message": f"✅ Welcome Super Admin {user.first_name or user.username}! You have full system control.",
                        "new_role": "super_admin"
                    }
                
                session.close()
                return {"success": False, "message": "User not found"}
            
            return {"success": False, "message": "❌ Invalid super admin key"}
            
        except Exception as e:
            logger.error(f"Error verifying super admin key: {e}")
            return {"success": False, "message": "Error verifying super admin key"}
    
    def promote_to_admin(self, target_user_id: int, promoted_by: int) -> Dict[str, Any]:
        """Promote user to admin role"""
        try:
            session = self.db_session()
            
            # Check if promoter is super admin
            promoter = session.query(User).filter(User.user_id == promoted_by).first()
            if not promoter or promoter.role != "super_admin":
                session.close()
                return {"success": False, "message": "❌ Super admin privileges required"}
            
            # Get target user
            target_user = session.query(User).filter(User.user_id == target_user_id).first()
            if not target_user:
                session.close()
                return {"success": False, "message": "User not found"}
            
            old_role = target_user.role
            target_user.role = "admin"
            session.commit()
            
            # Log the promotion
            self._log_role_action(
                promoted_by,
                "admin_promotion",
                details=f"Promoted user {target_user.username or target_user.first_name} to admin"
            )
            
            self._log_role_action(
                target_user_id,
                "role_change",
                old_role=old_role,
                new_role="admin",
                details=f"Promoted to admin by {promoter.username or promoter.first_name}"
            )
            
            session.close()
            
            return {
                "success": True,
                "message": f"✅ {target_user.first_name or target_user.username} promoted to Admin"
            }
            
        except Exception as e:
            logger.error(f"Error promoting user to admin: {e}")
            return {"success": False, "message": f"Error promoting user: {str(e)}"}
    
    def demote_admin(self, target_user_id: int, demoted_by: int) -> Dict[str, Any]:
        """Demote admin to student role"""
        try:
            session = self.db_session()
            
            # Check if demoter is super admin
            demoter = session.query(User).filter(User.user_id == demoted_by).first()
            if not demoter or demoter.role != "super_admin":
                session.close()
                return {"success": False, "message": "❌ Super admin privileges required"}
            
            # Get target user
            target_user = session.query(User).filter(User.user_id == target_user_id).first()
            if not target_user:
                session.close()
                return {"success": False, "message": "User not found"}
            
            if target_user.role != "admin":
                session.close()
                return {"success": False, "message": "User is not an admin"}
            
            old_role = target_user.role
            target_user.role = "student"
            session.commit()
            
            # Log the demotion
            self._log_role_action(
                demoted_by,
                "admin_demotion",
                details=f"Demoted admin {target_user.username or target_user.first_name} to student"
            )
            
            self._log_role_action(
                target_user_id,
                "role_change",
                old_role=old_role,
                new_role="student",
                details=f"Demoted to student by {demoter.username or demoter.first_name}"
            )
            
            session.close()
            
            return {
                "success": True,
                "message": f"✅ {target_user.first_name or target_user.username} demoted to Student"
            }
            
        except Exception as e:
            logger.error(f"Error demoting admin: {e}")
            return {"success": False, "message": f"Error demoting admin: {str(e)}"}
    
    def disable_admin(self, target_user_id: int, disabled_by: int) -> Dict[str, Any]:
        """Disable admin account"""
        try:
            session = self.db_session()
            
            # Check if disabler is super admin
            disabler = session.query(User).filter(User.user_id == disabled_by).first()
            if not disabler or disabler.role != "super_admin":
                session.close()
                return {"success": False, "message": "❌ Super admin privileges required"}
            
            # Get target user
            target_user = session.query(User).filter(User.user_id == target_user_id).first()
            if not target_user:
                session.close()
                return {"success": False, "message": "User not found"}
            
            if target_user.role not in ["admin", "super_admin"]:
                session.close()
                return {"success": False, "message": "User is not an admin"}
            
            # Disable the user
            target_user.is_active = False
            session.commit()
            
            # Log the action
            self._log_role_action(
                disabled_by,
                "admin_disabled",
                details=f"Disabled admin {target_user.username or target_user.first_name}"
            )
            
            session.close()
            
            return {
                "success": True,
                "message": f"✅ {target_user.first_name or target_user.username} account disabled"
            }
            
        except Exception as e:
            logger.error(f"Error disabling admin: {e}")
            return {"success": False, "message": f"Error disabling admin: {str(e)}"}
    
    def get_user_role(self, user_id: int) -> Optional[str]:
        """Get user's current role"""
        try:
            session = self.db_session()
            user = session.query(User).filter(User.user_id == user_id).first()
            session.close()
            return user.role if user else None
        except Exception as e:
            logger.error(f"Error getting user role: {e}")
            return None
    
    def get_admin_list(self) -> List[Dict[str, Any]]:
        """Get list of all admins and super admins"""
        try:
            session = self.db_session()
            
            admins = session.query(User).filter(
                User.role.in_(["admin", "super_admin"]),
                User.is_active == True
            ).all()
            
            result = []
            for admin in admins:
                # Get admin scope if exists
                scope = session.query(AdminScope).filter(AdminScope.admin_id == admin.user_id).first()
                
                result.append({
                    "user_id": admin.user_id,
                    "username": admin.username,
                    "first_name": admin.first_name,
                    "role": admin.role,
                    "university": scope.university.name if scope and scope.university else None,
                    "course": scope.course.name if scope and scope.course else None,
                    "last_activity": admin.last_activity,
                    "is_active": admin.is_active
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting admin list: {e}")
            return []
    
    def get_active_access_codes(self) -> List[Dict[str, Any]]:
        """Get list of active admin access codes"""
        try:
            session = self.db_session()
            
            codes = session.query(AdminAccessCode).filter(
                AdminAccessCode.is_active == True,
                AdminAccessCode.expires_at > datetime.utcnow()
            ).all()
            
            result = []
            for code in codes:
                creator = session.query(User).filter(User.user_id == code.created_by).first()
                user = session.query(User).filter(User.user_id == code.used_by).first() if code.used_by else None
                
                result.append({
                    "code_id": code.id,
                    "created_by": creator.username or creator.first_name if creator else "Unknown",
                    "used_by": user.username or user.first_name if user else None,
                    "is_used": code.used_by is not None,
                    "created_at": code.created_at,
                    "expires_at": code.expires_at
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting active access codes: {e}")
            return []
    
    def revoke_access_code(self, code_id: int, revoked_by: int) -> Dict[str, Any]:
        """Revoke an admin access code"""
        try:
            session = self.db_session()
            
            # Check if revoker is super admin
            revoker = session.query(User).filter(User.user_id == revoked_by).first()
            if not revoker or revoker.role != "super_admin":
                session.close()
                return {"success": False, "message": "❌ Super admin privileges required"}
            
            # Find and revoke code
            access_code = session.query(AdminAccessCode).filter(AdminAccessCode.id == code_id).first()
            if not access_code:
                session.close()
                return {"success": False, "message": "Access code not found"}
            
            access_code.is_active = False
            session.commit()
            
            # Log the action
            self._log_role_action(
                revoked_by,
                "access_code_revoked",
                details=f"Revoked access code: {code_id}"
            )
            
            session.close()
            
            return {
                "success": True,
                "message": f"✅ Access code {code_id} revoked"
            }
            
        except Exception as e:
            logger.error(f"Error revoking access code: {e}")
            return {"success": False, "message": f"Error revoking access code: {str(e)}"}
    
    def _log_role_action(self, user_id: int, action: str, old_role: str = None, 
                        new_role: str = None, details: str = None):
        """Log role-related actions for audit trail"""
        try:
            session = self.db_session()
            
            audit_log = RoleAuditLog(
                user_id=user_id,
                action=action,
                old_role=old_role,
                new_role=new_role,
                details=details,
                timestamp=datetime.utcnow()
            )
            
            session.add(audit_log)
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error logging role action: {e}")
    
    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent audit logs"""
        try:
            session = self.db_session()
            
            logs = session.query(RoleAuditLog).order_by(
                RoleAuditLog.timestamp.desc()
            ).limit(limit).all()
            
            result = []
            for log in logs:
                user = session.query(User).filter(User.user_id == log.user_id).first()
                result.append({
                    "log_id": log.log_id,
                    "user": user.username or user.first_name if user else "Unknown",
                    "action": log.action,
                    "old_role": log.old_role,
                    "new_role": log.new_role,
                    "details": log.details,
                    "timestamp": log.timestamp
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting audit logs: {e}")
            return []
    
    def cleanup_expired_codes(self) -> int:
        """Clean up expired access codes"""
        try:
            session = self.db_session()
            
            expired_codes = session.query(AdminAccessCode).filter(
                AdminAccessCode.expires_at < datetime.utcnow(),
                AdminAccessCode.is_active == True
            ).all()
            
            count = 0
            for code in expired_codes:
                code.is_active = False
                count += 1
            
            session.commit()
            session.close()
            
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up expired codes: {e}")
            return 0
