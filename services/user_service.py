"""
User service for managing user roles, preferences, and authentication
"""

from database.db import SessionLocal
from database.models import User
from config.auth import verify_admin_code, verify_super_admin_code, get_admin_name, DEFAULT_SUPER_ADMIN_ID
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class UserService:
    def __init__(self):
        self.db = SessionLocal()
    
    def get_or_create_user(self, telegram_id: int, username: str = None, 
                          first_name: str = None, last_name: str = None) -> User:
        """Get existing user or create new one"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                # Create new user
                user = User(
                    user_id=telegram_id,
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    last_name=last_name,
                    name=first_name or username or f"User_{telegram_id}",
                    role="student"
                )
                self.db.add(user)
                self.db.commit()
                self.db.refresh(user)
                logger.info(f"Created new user: {user.name} (ID: {telegram_id})")
            else:
                # Update existing user info if needed
                updated = False
                if username and user.username != username:
                    user.username = username
                    updated = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated = True
                if updated:
                    self.db.commit()
                    logger.info(f"Updated user info: {user.name}")
            
            return user
        except Exception as e:
            logger.error(f"Error in get_or_create_user: {e}")
            self.db.rollback()
            raise
    
    def set_user_role(self, telegram_id: int, role: str, auth_code: str = None) -> bool:
        """Set user role with authentication"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            # Verify authentication based on role
            if role == "admin":
                if not verify_admin_code(auth_code):
                    return False
                user.role = "admin"
                logger.info(f"User {user.name} promoted to admin")
                
            elif role == "super_admin":
                if not verify_super_admin_code(auth_code):
                    return False
                user.role = "super_admin"
                logger.info(f"User {user.name} promoted to super admin")
                
            elif role == "student":
                user.role = "student"
                logger.info(f"User {user.name} set to student role")
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error in set_user_role: {e}")
            self.db.rollback()
            return False
    
    def get_user_role(self, telegram_id: int) -> str:
        """Get user role"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            return user.role if user else "student"
        except Exception as e:
            logger.error(f"Error in get_user_role: {e}")
            return "student"
    
    def set_user_preferences(self, telegram_id: int, university: str = None, 
                           course: str = None, year: int = None) -> bool:
        """Set user's university, course, and year preferences"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            updated = False
            if university and user.university != university:
                user.university = university
                updated = True
            if course and user.course != course:
                user.course = course
                updated = True
            if year and user.year != year:
                user.year = year
                updated = True
            
            if updated:
                self.db.commit()
                logger.info(f"Updated preferences for {user.name}: {university}, {course}, {year}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in set_user_preferences: {e}")
            self.db.rollback()
            return False
    
    def get_user_preferences(self, telegram_id: int) -> Dict[str, Any]:
        """Get user's stored preferences"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {}
            
            return {
                "university": user.university,
                "course": user.course,
                "year": user.year,
                "role": user.role,
                "name": user.name
            }
        except Exception as e:
            logger.error(f"Error in get_user_preferences: {e}")
            return {}
    
    def is_admin(self, telegram_id: int) -> bool:
        """Check if user is admin or super admin"""
        role = self.get_user_role(telegram_id)
        return role in ["admin", "super_admin"]
    
    def is_super_admin(self, telegram_id: int) -> bool:
        """Check if user is super admin"""
        role = self.get_user_role(telegram_id)
        return role == "super_admin"
    
    def get_user_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get user statistics"""
        try:
            user = self.db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {}
            
            return {
                "name": user.name,
                "role": user.role,
                "university": user.university,
                "course": user.course,
                "year": user.year,
                "total_quizzes_taken": user.total_quizzes_taken,
                "average_accuracy": user.average_accuracy,
                "upload_count": user.upload_count,
                "approved_count": user.approved_count,
                "created_at": user.created_at
            }
        except Exception as e:
            logger.error(f"Error in get_user_stats: {e}")
            return {}
    
    def close(self):
        """Close database session"""
        self.db.close()
