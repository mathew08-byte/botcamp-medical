"""
Session Management Service for BotCamp Medical
Handles user state, memory, and session persistence per Master Specification Section 12
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import UserState, User, University, Course, Unit, Topic
from database.db_v2 import SessionLocal

logger = logging.getLogger(__name__)

class SessionService:
    def __init__(self):
        self.db_session = SessionLocal
    
    def get_user_state(self, user_id: int) -> Optional[UserState]:
        """Get user's current state from database"""
        try:
            session = self.db_session()
            user_state = session.query(UserState).filter(UserState.user_id == user_id).first()
            session.close()
            return user_state
        except Exception as e:
            logger.error(f"Error getting user state: {e}")
            return None
    
    def save_user_state(self, user_id: int, role: str, **kwargs) -> bool:
        """Save or update user state"""
        try:
            session = self.db_session()
            
            # Get existing state or create new
            user_state = session.query(UserState).filter(UserState.user_id == user_id).first()
            
            if not user_state:
                user_state = UserState(user_id=user_id, role=role)
                session.add(user_state)
            
            # Update fields
            user_state.role = role
            user_state.updated_at = datetime.utcnow()
            
            # Update optional fields
            for key, value in kwargs.items():
                if hasattr(user_state, key):
                    setattr(user_state, key, value)
            
            session.commit()
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error saving user state: {e}")
            return False
    
    def update_user_action(self, user_id: int, action: str) -> bool:
        """Update user's last action"""
        try:
            session = self.db_session()
            user_state = session.query(UserState).filter(UserState.user_id == user_id).first()
            
            if user_state:
                user_state.last_action = action
                user_state.updated_at = datetime.utcnow()
                session.commit()
            
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error updating user action: {e}")
            return False
    
    def clear_user_state(self, user_id: int) -> bool:
        """Clear user state (on logout or role change)"""
        try:
            session = self.db_session()
            user_state = session.query(UserState).filter(UserState.user_id == user_id).first()
            
            if user_state:
                session.delete(user_state)
                session.commit()
            
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"Error clearing user state: {e}")
            return False
    
    def get_resume_message(self, user_id: int) -> Optional[str]:
        """Generate resume message for returning user"""
        try:
            user_state = self.get_user_state(user_id)
            if not user_state:
                return None
            
            # Get user info
            session = self.db_session()
            user = session.query(User).filter(User.user_id == user_id).first()
            session.close()
            
            if not user:
                return None
            
            name = user.first_name or user.username or "User"
            
            message = f"Welcome back, {name}! Resuming from where you left off:\n"
            
            if user_state.university:
                message += f"- University: {user_state.university}\n"
            if user_state.course:
                message += f"- Course: {user_state.course}\n"
            if user_state.year:
                message += f"- Year: {user_state.year}\n"
            if user_state.unit:
                message += f"- Unit: {user_state.unit}\n"
            if user_state.topic:
                message += f"- Topic: {user_state.topic}\n"
            
            return message
            
        except Exception as e:
            logger.error(f"Error generating resume message: {e}")
            return None
    
    def get_hierarchy_data(self, university: str = None, course: str = None, year: int = None) -> Dict[str, Any]:
        """Get hierarchy data for UI dropdowns"""
        try:
            session = self.db_session()
            data = {}
            
            # Get universities
            universities = session.query(University).filter(University.is_active == True).all()
            data['universities'] = [{"id": u.id, "name": u.name} for u in universities]
            
            if university:
                # Get courses for university
                courses = session.query(Course).join(University).filter(
                    University.name == university,
                    Course.is_active == True
                ).all()
                data['courses'] = [{"id": c.id, "name": c.name} for c in courses]
            
            if course:
                # Get units for course and year
                units = session.query(Unit).join(Course).filter(
                    Course.name == course,
                    Unit.is_active == True
                )
                if year:
                    units = units.filter(Unit.year == str(year))
                
                data['units'] = [{"id": u.id, "name": u.name, "year": u.year} for u in units.all()]
            
            session.close()
            return data
            
        except Exception as e:
            logger.error(f"Error getting hierarchy data: {e}")
            return {}
    
    def validate_user_selection(self, user_id: int) -> Dict[str, Any]:
        """Validate if user has complete selection for quiz"""
        try:
            user_state = self.get_user_state(user_id)
            if not user_state:
                return {"valid": False, "missing": "complete_selection"}
            
            missing = []
            if not user_state.university:
                missing.append("university")
            if not user_state.course:
                missing.append("course")
            if not user_state.year:
                missing.append("year")
            if not user_state.unit:
                missing.append("unit")
            if not user_state.topic:
                missing.append("topic")
            
            return {
                "valid": len(missing) == 0,
                "missing": missing,
                "state": user_state
            }
            
        except Exception as e:
            logger.error(f"Error validating user selection: {e}")
            return {"valid": False, "missing": "error"}
    
    def get_quiz_continuation_options(self, user_id: int) -> Dict[str, Any]:
        """Get options for quiz continuation after completion"""
        try:
            user_state = self.get_user_state(user_id)
            if not user_state:
                return {"options": []}
            
            options = [
                {"text": "▶️ Take another quiz (same topic)", "callback": "retake_same_topic"},
                {"text": "🔁 Change topic", "callback": "change_topic"},
                {"text": "⚙️ Change university/course", "callback": "change_university"},
                {"text": "🏠 Main menu", "callback": "main_menu"}
            ]
            
            return {"options": options}
            
        except Exception as e:
            logger.error(f"Error getting quiz continuation options: {e}")
            return {"options": []}
    
    def handle_exit_confirmation(self, user_id: int) -> str:
        """Generate exit confirmation message"""
        return "You are about to exit your current selection. Are you sure?"
    
    def get_user_context(self, user_id: int) -> Dict[str, Any]:
        """Get complete user context for UI rendering"""
        try:
            user_state = self.get_user_state(user_id)
            if not user_state:
                return {}
            
            session = self.db_session()
            user = session.query(User).filter(User.user_id == user_id).first()
            session.close()
            
            return {
                "user_id": user_id,
                "role": user_state.role,
                "university": user_state.university,
                "course": user_state.course,
                "year": user_state.year,
                "unit": user_state.unit,
                "topic": user_state.topic,
                "last_action": user_state.last_action,
                "updated_at": user_state.updated_at,
                "user_info": {
                    "first_name": user.first_name if user else None,
                    "username": user.username if user else None
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting user context: {e}")
            return {}
