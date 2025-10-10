"""
Analytics Service for BotCamp Medical
Handles quiz analytics, contributor analytics, and admin dashboards
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_
from database.models import (
    User, Question, QuizSession, QuizAnswer, Topic, Unit, Course, University
)
from database.db_v2 import SessionLocal

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self):
        self.db_session = SessionLocal
    
    def get_quiz_analytics(self, user_id: Optional[int] = None, topic_id: Optional[int] = None, 
                          days_back: int = 30) -> Dict[str, Any]:
        """Get comprehensive quiz analytics"""
        try:
            session = self.db_session()
            
            # Base query for quiz sessions
            query = session.query(QuizSession)
            
            # Apply filters
            if user_id:
                query = query.filter(QuizSession.user_id == user_id)
            if topic_id:
                query = query.filter(QuizSession.topic_id == topic_id)
            
            # Date filter
            date_filter = datetime.utcnow() - timedelta(days=days_back)
            query = query.filter(QuizSession.started_at >= date_filter)
            
            # Get basic stats
            total_quizzes = query.count()
            completed_quizzes = query.filter(QuizSession.is_completed == True).count()
            
            if completed_quizzes == 0:
                return {
                    "total_quizzes": 0,
                    "completed_quizzes": 0,
                    "average_accuracy": 0,
                    "total_questions_attempted": 0,
                    "total_correct_answers": 0,
                    "most_attempted_topics": [],
                    "lowest_performing_topics": [],
                    "top_students": []
                }
            
            # Calculate averages
            avg_accuracy = session.query(func.avg(QuizSession.accuracy)).filter(
                QuizSession.is_completed == True,
                QuizSession.accuracy.isnot(None)
            ).scalar() or 0
            
            total_questions = session.query(func.sum(QuizSession.total_questions)).filter(
                QuizSession.is_completed == True
            ).scalar() or 0
            
            total_correct = session.query(func.sum(QuizSession.correct_answers)).filter(
                QuizSession.is_completed == True
            ).scalar() or 0
            
            # Most attempted topics
            most_attempted = session.query(
                Topic.name,
                func.count(QuizSession.id).label('attempt_count')
            ).join(QuizSession).filter(
                QuizSession.is_completed == True
            ).group_by(Topic.id, Topic.name).order_by(desc('attempt_count')).limit(5).all()
            
            # Lowest performing topics (by average accuracy)
            lowest_performing = session.query(
                Topic.name,
                func.avg(QuizSession.accuracy).label('avg_accuracy')
            ).join(QuizSession).filter(
                QuizSession.is_completed == True,
                QuizSession.accuracy.isnot(None)
            ).group_by(Topic.id, Topic.name).order_by('avg_accuracy').limit(5).all()
            
            # Top students (by average accuracy)
            top_students = session.query(
                User.username,
                User.first_name,
                func.avg(QuizSession.accuracy).label('avg_accuracy'),
                func.count(QuizSession.id).label('quiz_count')
            ).join(QuizSession).filter(
                QuizSession.is_completed == True,
                QuizSession.accuracy.isnot(None),
                User.role == 'student'
            ).group_by(User.user_id, User.username, User.first_name).having(
                func.count(QuizSession.id) >= 3  # At least 3 quizzes
            ).order_by(desc('avg_accuracy')).limit(10).all()
            
            session.close()
            
            return {
                "total_quizzes": total_quizzes,
                "completed_quizzes": completed_quizzes,
                "average_accuracy": round(avg_accuracy, 1),
                "total_questions_attempted": total_questions,
                "total_correct_answers": total_correct,
                "most_attempted_topics": [{"name": name, "count": count} for name, count in most_attempted],
                "lowest_performing_topics": [{"name": name, "accuracy": round(acc, 1)} for name, acc in lowest_performing],
                "top_students": [{"username": username or first_name or "Unknown", "accuracy": round(acc, 1), "quizzes": count} 
                               for username, first_name, acc, count in top_students]
            }
            
        except Exception as e:
            logger.error(f"Error getting quiz analytics: {e}")
            return {}
    
    def get_contributor_analytics(self, user_id: int) -> Dict[str, Any]:
        """Get analytics for a specific contributor"""
        try:
            session = self.db_session()
            
            # Get user info
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {}
            
            # Get upload stats
            total_uploaded = session.query(Question).filter(Question.uploader_id == user_id).count()
            approved_count = session.query(Question).filter(
                Question.uploader_id == user_id,
                Question.needs_review == False
            ).count()
            flagged_count = session.query(Question).filter(
                Question.uploader_id == user_id,
                Question.needs_review == True
            ).count()
            rejected_count = session.query(Question).filter(
                Question.uploader_id == user_id,
                Question.is_active == False
            ).count()
            
            # Average moderation score
            avg_score = session.query(func.avg(Question.moderation_score)).filter(
                Question.uploader_id == user_id,
                Question.moderation_score.isnot(None)
            ).scalar() or 0
            
            # Most active unit
            most_active_unit = session.query(
                Unit.name,
                func.count(Question.question_id).label('question_count')
            ).join(Question, Question.unit == Unit.name).filter(
                Question.uploader_id == user_id
            ).group_by(Unit.name).order_by(desc('question_count')).first()
            
            # Most active topic
            most_active_topic = session.query(
                Topic.name,
                func.count(Question.question_id).label('question_count')
            ).join(Question, Question.topic == Topic.name).filter(
                Question.uploader_id == user_id
            ).group_by(Topic.name).order_by(desc('question_count')).first()
            
            # Quiz performance
            quiz_stats = session.query(
                func.count(QuizSession.id).label('total_quizzes'),
                func.avg(QuizSession.accuracy).label('avg_accuracy')
            ).filter(QuizSession.user_id == user_id).first()
            
            session.close()
            
            return {
                "user_info": {
                    "username": user.username or user.first_name or "Unknown",
                    "role": user.role
                },
                "upload_stats": {
                    "total_uploaded": total_uploaded,
                    "approved": approved_count,
                    "flagged": flagged_count,
                    "rejected": rejected_count,
                    "approval_rate": round((approved_count / total_uploaded * 100) if total_uploaded > 0 else 0, 1)
                },
                "quality_metrics": {
                    "average_moderation_score": round(avg_score, 1),
                    "most_active_unit": most_active_unit[0] if most_active_unit else "None",
                    "most_active_topic": most_active_topic[0] if most_active_topic else "None"
                },
                "quiz_performance": {
                    "total_quizzes_taken": quiz_stats[0] or 0,
                    "average_accuracy": round(quiz_stats[1] or 0, 1)
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting contributor analytics: {e}")
            return {}
    
    def get_admin_dashboard_data(self, admin_user_id: Optional[int] = None) -> Dict[str, Any]:
        """Get comprehensive admin dashboard data"""
        try:
            session = self.db_session()
            
            # System overview
            total_users = session.query(User).count()
            total_students = session.query(User).filter(User.role == 'student').count()
            total_admins = session.query(User).filter(User.role == 'admin').count()
            total_super_admins = session.query(User).filter(User.role == 'super_admin').count()
            
            total_questions = session.query(Question).count()
            total_topics = session.query(Topic).count()
            total_units = session.query(Unit).count()
            total_courses = session.query(Course).count()
            total_universities = session.query(University).count()
            
            # Recent activity (last 7 days)
            week_ago = datetime.utcnow() - timedelta(days=7)
            recent_quizzes = session.query(QuizSession).filter(
                QuizSession.started_at >= week_ago
            ).count()
            
            # Pending moderation
            pending_review = session.query(Question).filter(
                Question.needs_review == True
            ).count()
            
            # Most active topic
            most_active_topic = session.query(
                Topic.name,
                func.count(QuizSession.id).label('quiz_count')
            ).join(QuizSession).filter(
                QuizSession.started_at >= week_ago
            ).group_by(Topic.id, Topic.name).order_by(desc('quiz_count')).first()
            
            # System health metrics
            avg_quiz_accuracy = session.query(func.avg(QuizSession.accuracy)).filter(
                QuizSession.is_completed == True,
                QuizSession.accuracy.isnot(None),
                QuizSession.started_at >= week_ago
            ).scalar() or 0
            
            # Upload activity
            recent_uploads = session.query(Question).filter(
                Question.created_at >= week_ago
            ).count()
            
            session.close()
            
            return {
                "system_overview": {
                    "total_users": total_users,
                    "total_students": total_students,
                    "total_admins": total_admins,
                    "total_super_admins": total_super_admins,
                    "total_questions": total_questions,
                    "total_topics": total_topics,
                    "total_units": total_units,
                    "total_courses": total_courses,
                    "total_universities": total_universities
                },
                "recent_activity": {
                    "quiz_sessions_this_week": recent_quizzes,
                    "uploads_this_week": recent_uploads,
                    "average_quiz_accuracy": round(avg_quiz_accuracy, 1),
                    "most_active_topic": most_active_topic[0] if most_active_topic else "None"
                },
                "moderation": {
                    "questions_pending_review": pending_review
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting admin dashboard data: {e}")
            return {}
    
    def get_moderation_queue(self) -> List[Dict[str, Any]]:
        """Get questions pending moderation review"""
        try:
            session = self.db_session()
            
            pending_questions = session.query(Question).filter(
                Question.needs_review == True
            ).order_by(Question.created_at.desc()).limit(50).all()
            
            result = []
            for q in pending_questions:
                uploader = session.query(User).filter(User.user_id == q.uploader_id).first()
                result.append({
                    "question_id": q.question_id,
                    "question_text": q.question_text[:100] + "..." if len(q.question_text) > 100 else q.question_text,
                    "topic": q.topic,
                    "unit": q.unit,
                    "moderation_score": q.moderation_score,
                    "moderation_comments": q.moderation_comments,
                    "uploader": uploader.username or uploader.first_name or "Unknown" if uploader else "Unknown",
                    "created_at": q.created_at.strftime("%Y-%m-%d %H:%M") if q.created_at else "Unknown"
                })
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Error getting moderation queue: {e}")
            return []
    
    def update_user_analytics(self, user_id: int, quiz_session: QuizSession):
        """Update user analytics after quiz completion"""
        try:
            session = self.db_session()
            
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                return
            
            # Update quiz stats
            user.total_quizzes_taken = (user.total_quizzes_taken or 0) + 1
            
            # Calculate new average accuracy
            all_sessions = session.query(QuizSession).filter(
                QuizSession.user_id == user_id,
                QuizSession.is_completed == True,
                QuizSession.accuracy.isnot(None)
            ).all()
            
            if all_sessions:
                avg_accuracy = sum(s.accuracy for s in all_sessions) / len(all_sessions)
                user.average_accuracy = round(avg_accuracy)
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error updating user analytics: {e}")
    
    def update_contributor_stats(self, user_id: int, question_id: int, action: str):
        """Update contributor stats when question is moderated"""
        try:
            session = self.db_session()
            
            user = session.query(User).filter(User.user_id == user_id).first()
            if not user:
                return
            
            if action == "approved":
                user.approved_count = (user.approved_count or 0) + 1
            elif action == "flagged":
                user.flagged_count = (user.flagged_count or 0) + 1
            elif action == "rejected":
                user.rejected_count = (user.rejected_count or 0) + 1
            
            # Update average moderation score
            question = session.query(Question).filter(Question.question_id == question_id).first()
            if question and question.moderation_score:
                all_questions = session.query(Question).filter(
                    Question.uploader_id == user_id,
                    Question.moderation_score.isnot(None)
                ).all()
                
                if all_questions:
                    avg_score = sum(q.moderation_score for q in all_questions) / len(all_questions)
                    user.average_moderation_score = round(avg_score)
            
            session.commit()
            session.close()
            
        except Exception as e:
            logger.error(f"Error updating contributor stats: {e}")
