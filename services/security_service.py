"""
Security Service for BotCamp Medical
Handles authentication, role management, and security safeguards
"""

import hashlib
import time
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from database.db import SessionLocal
from database.models import User, SystemLog, EventLog
import os

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self):
        self.active_sessions = {}  # Store active admin sessions
        self.rate_limits = {}  # Store rate limiting data
        self.max_file_size = 10 * 1024 * 1024  # 10 MB
        self.max_uploads_per_hour = 10
        self.session_timeout = 2 * 60 * 60  # 2 hours
        
    def hash_password(self, password: str) -> str:
        """Hash password using SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.hash_password(password) == hashed_password
    
    def create_admin_session(self, telegram_id: int, role: str) -> str:
        """Create admin session"""
        session_id = f"{telegram_id}_{int(time.time())}"
        self.active_sessions[session_id] = {
            "telegram_id": telegram_id,
            "role": role,
            "created_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        
        # Log session creation
        self.log_security_event(telegram_id, "session_created", {"role": role, "session_id": session_id})
        
        return session_id
    
    def validate_session(self, telegram_id: int) -> bool:
        """Validate admin session"""
        current_time = datetime.utcnow()
        
        # Find active session for user
        for session_id, session_data in self.active_sessions.items():
            if session_data["telegram_id"] == telegram_id:
                # Check if session is expired
                if current_time - session_data["last_activity"] > timedelta(seconds=self.session_timeout):
                    # Session expired
                    del self.active_sessions[session_id]
                    self.log_security_event(telegram_id, "session_expired", {"session_id": session_id})
                    return False
                
                # Update last activity
                session_data["last_activity"] = current_time
                return True
        
        return False
    
    def get_user_role(self, telegram_id: int) -> str:
        """Get user role with session validation"""
        # Check if user has active admin session
        if self.validate_session(telegram_id):
            for session_data in self.active_sessions.values():
                if session_data["telegram_id"] == telegram_id:
                    return session_data["role"]
        
        # Fallback to database role
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            return user.role if user else "student"
        finally:
            db.close()
    
    def check_rate_limit(self, telegram_id: int, action: str) -> bool:
        """Check if user has exceeded rate limits"""
        current_time = time.time()
        hour_key = f"{telegram_id}_{action}_{int(current_time // 3600)}"
        
        if hour_key not in self.rate_limits:
            self.rate_limits[hour_key] = {"count": 0, "reset_time": current_time + 3600}
        
        rate_data = self.rate_limits[hour_key]
        
        # Clean up expired rate limits
        if current_time > rate_data["reset_time"]:
            rate_data["count"] = 0
            rate_data["reset_time"] = current_time + 3600
        
        # Check limits based on action
        if action == "upload":
            limit = self.max_uploads_per_hour
        else:
            limit = 100  # Default limit for other actions
        
        if rate_data["count"] >= limit:
            self.log_security_event(telegram_id, "rate_limit_exceeded", {"action": action, "limit": limit})
            return False
        
        rate_data["count"] += 1
        return True
    
    def validate_file_upload(self, file_size: int, file_type: str) -> Dict[str, Any]:
        """Validate file upload"""
        result = {"valid": True, "error": None}
        
        # Check file size
        if file_size > self.max_file_size:
            result["valid"] = False
            result["error"] = f"File too large. Maximum size: {self.max_file_size // (1024*1024)} MB"
            return result
        
        # Check file type
        allowed_types = ["pdf", "png", "jpg", "jpeg", "gif", "bmp"]
        if file_type.lower() not in allowed_types:
            result["valid"] = False
            result["error"] = f"File type not allowed. Allowed types: {', '.join(allowed_types)}"
            return result
        
        return result
    
    def sanitize_input(self, text: str) -> str:
        """Sanitize user input"""
        if not text:
            return ""
        
        # Remove HTML tags
        import re
        text = re.sub(r'<[^>]+>', '', text)
        
        # Remove potentially dangerous characters
        dangerous_chars = ['<', '>', '"', "'", '&', '\x00', '\r', '\n']
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Limit length
        if len(text) > 10000:  # 10KB limit
            text = text[:10000]
        
        return text.strip()
    
    def log_security_event(self, telegram_id: int, event_type: str, details: Dict[str, Any]):
        """Log security events"""
        try:
            db = SessionLocal()
            try:
                # Log to system logs
                system_log = SystemLog(
                    user_id=telegram_id,
                    action=f"security_{event_type}",
                    details=details,
                    timestamp=datetime.utcnow()
                )
                db.add(system_log)
                
                # Log to event logs
                event_log = EventLog(
                    user_id=telegram_id,
                    event_type=event_type,
                    context=details,
                    timestamp=datetime.utcnow()
                )
                db.add(event_log)
                
                db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error logging security event: {e}")
    
    def check_admin_permissions(self, telegram_id: int, required_role: str = "admin") -> bool:
        """Check if user has required admin permissions"""
        user_role = self.get_user_role(telegram_id)
        
        if required_role == "admin":
            return user_role in ["admin", "super_admin"]
        elif required_role == "super_admin":
            return user_role == "super_admin"
        
        return False
    
    def create_admin_user(self, telegram_id: int, username: str, role: str, created_by: int) -> bool:
        """Create new admin user (super admin only)"""
        try:
            if not self.check_admin_permissions(created_by, "super_admin"):
                return False
            
            db = SessionLocal()
            try:
                # Check if user already exists
                existing_user = db.query(User).filter(User.telegram_id == telegram_id).first()
                
                if existing_user:
                    # Update existing user role
                    existing_user.role = role
                    existing_user.name = username
                else:
                    # Create new user
                    new_user = User(
                        user_id=telegram_id,
                        telegram_id=telegram_id,
                        username=username,
                        name=username,
                        role=role,
                        created_at=datetime.utcnow()
                    )
                    db.add(new_user)
                
                db.commit()
                
                # Log admin creation
                self.log_security_event(created_by, "admin_created", {
                    "target_user": telegram_id,
                    "target_username": username,
                    "role": role
                })
                
                return True
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error creating admin user: {e}")
            return False
    
    def remove_admin_user(self, telegram_id: int, removed_by: int) -> bool:
        """Remove admin privileges (super admin only)"""
        try:
            if not self.check_admin_permissions(removed_by, "super_admin"):
                return False
            
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                
                if user and user.role in ["admin", "super_admin"]:
                    old_role = user.role
                    user.role = "student"
                    db.commit()
                    
                    # Log admin removal
                    self.log_security_event(removed_by, "admin_removed", {
                        "target_user": telegram_id,
                        "old_role": old_role
                    })
                    
                    return True
                
                return False
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error removing admin user: {e}")
            return False
    
    def get_admin_list(self, requester_id: int) -> Optional[list]:
        """Get list of admin users (super admin only)"""
        try:
            if not self.check_admin_permissions(requester_id, "super_admin"):
                return None
            
            db = SessionLocal()
            try:
                admins = db.query(User).filter(User.role.in_(["admin", "super_admin"])).all()
                
                admin_list = []
                for admin in admins:
                    admin_list.append({
                        "telegram_id": admin.telegram_id,
                        "username": admin.username,
                        "name": admin.name,
                        "role": admin.role,
                        "created_at": admin.created_at
                    })
                
                return admin_list
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"Error getting admin list: {e}")
            return None
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = datetime.utcnow()
        expired_sessions = []
        
        for session_id, session_data in self.active_sessions.items():
            if current_time - session_data["last_activity"] > timedelta(seconds=self.session_timeout):
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            session_data = self.active_sessions[session_id]
            self.log_security_event(
                session_data["telegram_id"], 
                "session_cleanup", 
                {"session_id": session_id}
            )
            del self.active_sessions[session_id]
    
    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        return {
            "active_sessions": len(self.active_sessions),
            "rate_limits_tracked": len(self.rate_limits),
            "max_file_size": self.max_file_size,
            "max_uploads_per_hour": self.max_uploads_per_hour,
            "session_timeout": self.session_timeout
        }
