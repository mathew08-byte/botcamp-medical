"""
Multi-University Scaling Service for BotCamp Medical
Implements Master Specification Section 15 - Scaling to Multiple Universities and Courses
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import University, Course, Unit, Topic, Paper, Question, AdminScope, User
from database.db_v2 import SessionLocal

logger = logging.getLogger(__name__)

class MultiUniversityService:
    def __init__(self):
        self.db_session = SessionLocal
    
    def add_university(self, name: str, created_by: int) -> Dict[str, Any]:
        """Add a new university per Section 15.2"""
        try:
            session = self.db_session()
            
            # Check if university already exists
            existing = session.query(University).filter(University.name == name).first()
            if existing:
                session.close()
                return {"success": False, "message": "University already exists"}
            
            university = University(
                name=name,
                is_active=True
            )
            
            session.add(university)
            session.commit()
            session.refresh(university)
            
            session.close()
            
            return {
                "success": True,
                "message": f"University '{name}' added successfully",
                "university_id": university.id
            }
            
        except Exception as e:
            logger.error(f"Error adding university: {e}")
            return {"success": False, "message": f"Error adding university: {str(e)}"}
    
    def add_course(self, university_name: str, course_name: str, created_by: int) -> Dict[str, Any]:
        """Add a new course to a university per Section 15.2"""
        try:
            session = self.db_session()
            
            # Find university
            university = session.query(University).filter(University.name == university_name).first()
            if not university:
                session.close()
                return {"success": False, "message": "University not found"}
            
            # Check if course already exists
            existing = session.query(Course).filter(
                Course.name == course_name,
                Course.university_id == university.id
            ).first()
            if existing:
                session.close()
                return {"success": False, "message": "Course already exists for this university"}
            
            course = Course(
                name=course_name,
                university_id=university.id,
                is_active=True
            )
            
            session.add(course)
            session.commit()
            session.refresh(course)
            
            session.close()
            
            return {
                "success": True,
                "message": f"Course '{course_name}' added to '{university_name}' successfully",
                "course_id": course.id
            }
            
        except Exception as e:
            logger.error(f"Error adding course: {e}")
            return {"success": False, "message": f"Error adding course: {str(e)}"}
    
    def add_unit(self, course_name: str, year: int, unit_name: str, created_by: int) -> Dict[str, Any]:
        """Add a new unit to a course per Section 15.2"""
        try:
            session = self.db_session()
            
            # Find course
            course = session.query(Course).filter(Course.name == course_name).first()
            if not course:
                session.close()
                return {"success": False, "message": "Course not found"}
            
            # Check if unit already exists
            existing = session.query(Unit).filter(
                Unit.name == unit_name,
                Unit.course_id == course.id,
                Unit.year == str(year)
            ).first()
            if existing:
                session.close()
                return {"success": False, "message": "Unit already exists for this course and year"}
            
            unit = Unit(
                name=unit_name,
                course_id=course.id,
                year=str(year),
                is_active=True
            )
            
            session.add(unit)
            session.commit()
            session.refresh(unit)
            
            session.close()
            
            return {
                "success": True,
                "message": f"Unit '{unit_name}' added to '{course_name}' Year {year} successfully",
                "unit_id": unit.id
            }
            
        except Exception as e:
            logger.error(f"Error adding unit: {e}")
            return {"success": False, "message": f"Error adding unit: {str(e)}"}
    
    def add_topic(self, unit_name: str, topic_name: str, created_by: int) -> Dict[str, Any]:
        """Add a new topic to a unit per Section 15.2"""
        try:
            session = self.db_session()
            
            # Find unit
            unit = session.query(Unit).filter(Unit.name == unit_name).first()
            if not unit:
                session.close()
                return {"success": False, "message": "Unit not found"}
            
            # Check if topic already exists
            existing = session.query(Topic).filter(
                Topic.name == topic_name,
                Topic.unit_id == unit.id
            ).first()
            if existing:
                session.close()
                return {"success": False, "message": "Topic already exists for this unit"}
            
            topic = Topic(
                name=topic_name,
                unit_id=unit.id,
                is_active=True
            )
            
            session.add(topic)
            session.commit()
            session.refresh(topic)
            
            session.close()
            
            return {
                "success": True,
                "message": f"Topic '{topic_name}' added to '{unit_name}' successfully",
                "topic_id": topic.id
            }
            
        except Exception as e:
            logger.error(f"Error adding topic: {e}")
            return {"success": False, "message": f"Error adding topic: {str(e)}"}
    
    def set_admin_scope(self, admin_id: int, university_id: int, course_id: int) -> Dict[str, Any]:
        """Set admin scope per Section 15.3"""
        try:
            session = self.db_session()
            
            # Check if scope already exists
            existing = session.query(AdminScope).filter(
                AdminScope.admin_id == admin_id,
                AdminScope.university_id == university_id,
                AdminScope.course_id == course_id
            ).first()
            
            if existing:
                session.close()
                return {"success": False, "message": "Admin scope already exists"}
            
            scope = AdminScope(
                admin_id=admin_id,
                university_id=university_id,
                course_id=course_id
            )
            
            session.add(scope)
            session.commit()
            session.refresh(scope)
            
            session.close()
            
            return {
                "success": True,
                "message": "Admin scope set successfully",
                "scope_id": scope.id
            }
            
        except Exception as e:
            logger.error(f"Error setting admin scope: {e}")
            return {"success": False, "message": f"Error setting admin scope: {str(e)}"}
    
    def get_admin_scopes(self, admin_id: int) -> List[Dict[str, Any]]:
        """Get all scopes for an admin"""
        try:
            session = self.db_session()
            
            scopes = session.query(AdminScope).filter(AdminScope.admin_id == admin_id).all()
            
            result = []
            for scope in scopes:
                result.append({
                    "scope_id": scope.id,
                    "university_id": scope.university_id,
                    "course_id": scope.course_id,
                    "university": scope.university.name if scope.university else None,
                    "course": scope.course.name if scope.course else None,
                    "created_at": scope.created_at
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting admin scopes: {e}")
            return []
    
    def get_university_hierarchy(self, university_name: str = None) -> Dict[str, Any]:
        """Get complete hierarchy for a university or all universities"""
        try:
            session = self.db_session()
            
            if university_name:
                # Get specific university hierarchy
                university = session.query(University).filter(University.name == university_name).first()
                if not university:
                    session.close()
                    return {"error": "University not found"}
                
                courses = session.query(Course).filter(
                    Course.university_id == university.id,
                    Course.is_active == True
                ).all()
                
                result = {
                    "university": {
                        "id": university.id,
                        "name": university.name
                    },
                    "courses": []
                }
                
                for course in courses:
                    units = session.query(Unit).filter(
                        Unit.course_id == course.id,
                        Unit.is_active == True
                    ).all()
                    
                    course_data = {
                        "id": course.id,
                        "name": course.name,
                        "units": []
                    }
                    
                    for unit in units:
                        topics = session.query(Topic).filter(
                            Topic.unit_id == unit.id,
                            Topic.is_active == True
                        ).all()
                        
                        unit_data = {
                            "id": unit.id,
                            "name": unit.name,
                            "year": unit.year,
                            "topics": [{"id": t.id, "name": t.name} for t in topics]
                        }
                        
                        course_data["units"].append(unit_data)
                    
                    result["courses"].append(course_data)
                
            else:
                # Get all universities
                universities = session.query(University).filter(University.is_active == True).all()
                result = {
                    "universities": [
                        {
                            "id": u.id,
                            "name": u.name,
                            "courses_count": session.query(Course).filter(
                                Course.university_id == u.id,
                                Course.is_active == True
                            ).count()
                        }
                        for u in universities
                    ]
                }
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting university hierarchy: {e}")
            return {"error": str(e)}
    
    def get_questions_by_scope(self, university_id: int = None, course_id: int = None, 
                              unit_id: int = None, topic_id: int = None) -> List[Dict[str, Any]]:
        """Get questions filtered by scope per Section 15.1"""
        try:
            session = self.db_session()
            
            query = session.query(Question)
            
            if topic_id:
                query = query.filter(Question.topic_id == topic_id)
            elif unit_id:
                query = query.join(Topic).filter(Topic.unit_id == unit_id)
            elif course_id:
                query = query.join(Topic).join(Unit).filter(Unit.course_id == course_id)
            elif university_id:
                query = query.join(Topic).join(Unit).join(Course).filter(Course.university_id == university_id)
            
            questions = query.filter(Question.is_active == True).all()
            
            result = []
            for question in questions:
                uploader = session.query(User).filter(User.user_id == question.uploader_id).first()
                topic = session.query(Topic).filter(Topic.id == question.topic_id).first()
                unit = session.query(Unit).filter(Unit.id == topic.unit_id).first() if topic else None
                course = session.query(Course).filter(Course.id == unit.course_id).first() if unit else None
                university = session.query(University).filter(University.id == course.university_id).first() if course else None
                
                result.append({
                    "question_id": question.question_id,
                    "question_text": question.question_text,
                    "options": {
                        "A": question.option_a,
                        "B": question.option_b,
                        "C": question.option_c,
                        "D": question.option_d
                    },
                    "correct_option": question.correct_option,
                    "explanation": question.explanation,
                    "uploader": uploader.username or uploader.first_name if uploader else "Unknown",
                    "topic": topic.name if topic else None,
                    "unit": unit.name if unit else None,
                    "course": course.name if course else None,
                    "university": university.name if university else None,
                    "created_at": question.created_at,
                    "moderation_score": question.moderation_score
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting questions by scope: {e}")
            return []
    
    def get_statistics_by_scope(self, university_id: int = None, course_id: int = None) -> Dict[str, Any]:
        """Get statistics for a specific scope"""
        try:
            session = self.db_session()
            
            # Base queries
            questions_query = session.query(Question)
            users_query = session.query(User)
            
            if course_id:
                questions_query = questions_query.join(Topic).join(Unit).filter(Unit.course_id == course_id)
            elif university_id:
                questions_query = questions_query.join(Topic).join(Unit).join(Course).filter(Course.university_id == university_id)
            
            total_questions = questions_query.filter(Question.is_active == True).count()
            total_topics = session.query(Topic).join(Unit).join(Course).filter(
                Course.university_id == university_id if university_id else True,
                Course.id == course_id if course_id else True
            ).count()
            
            total_units = session.query(Unit).join(Course).filter(
                Course.university_id == university_id if university_id else True,
                Course.id == course_id if course_id else True
            ).count()
            
            total_courses = session.query(Course).filter(
                Course.university_id == university_id if university_id else True
            ).count()
            
            session.close()
            
            return {
                "total_questions": total_questions,
                "total_topics": total_topics,
                "total_units": total_units,
                "total_courses": total_courses,
                "scope": {
                    "university_id": university_id,
                    "course_id": course_id
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting statistics by scope: {e}")
            return {"error": str(e)}
    
    def validate_admin_access(self, admin_id: int, university_id: int, course_id: int) -> bool:
        """Validate if admin has access to specific university/course"""
        try:
            session = self.db_session()
            
            scope = session.query(AdminScope).filter(
                AdminScope.admin_id == admin_id,
                AdminScope.university_id == university_id,
                AdminScope.course_id == course_id
            ).first()
            
            session.close()
            return scope is not None
            
        except Exception as e:
            logger.error(f"Error validating admin access: {e}")
            return False
