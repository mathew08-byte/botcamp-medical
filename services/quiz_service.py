"""
Quiz service for managing quiz sessions and results
"""

from database.db import SessionLocal
from database.models import Question, QuizSession, QuizAnswer, QuizResult, User
from sqlalchemy import select, func, desc
from typing import List, Dict, Any, Optional
import logging
import random
from datetime import datetime

logger = logging.getLogger(__name__)

class QuizService:
    def __init__(self):
        self.db = SessionLocal()
    
    def get_questions_for_topic(self, unit: str, topic: str = None, limit: int = 10, difficulty: str = None) -> List[Question]:
        """Get questions for a specific unit/topic with dynamic filtering"""
        try:
            query = self.db.query(Question).filter(
                Question.unit == unit,
                Question.is_active == True
            )
            
            if topic:
                query = query.filter(Question.topic == topic)
            
            if difficulty:
                query = query.filter(Question.difficulty == difficulty)
            
            # Use SQL RANDOM() for better performance
            questions = query.order_by(func.random()).limit(limit).all()
            
            return questions
            
        except Exception as e:
            logger.error(f"Error in get_questions_for_topic: {e}")
            return []
    
    def create_quiz_session(self, user_id: int, unit: str, topic: str = None) -> Optional[QuizSession]:
        """Create a new quiz session"""
        try:
            # Get questions for the quiz
            questions = self.get_questions_for_topic(unit, topic)
            
            if not questions:
                return None
            
            # Create quiz session
            session = QuizSession(
                user_id=user_id,
                topic_id=None,  # We'll use unit/topic strings for now
                total_questions=len(questions),
                correct_answers=0,
                current_question=0,
                is_completed=False,
                started_at=datetime.utcnow()
            )
            
            self.db.add(session)
            self.db.commit()
            self.db.refresh(session)
            
            # Store questions in session data (simplified approach)
            session.questions_data = [q.question_id for q in questions]
            
            return session
            
        except Exception as e:
            logger.error(f"Error in create_quiz_session: {e}")
            self.db.rollback()
            return None
    
    def get_current_question(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get the current question for a quiz session"""
        try:
            session = self.db.query(QuizSession).filter(QuizSession.id == session_id).first()
            if not session or session.is_completed:
                return None
            
            # Get questions for this session
            questions = self.get_questions_for_topic(session.unit or "General")
            
            if session.current_question >= len(questions):
                return None
            
            question = questions[session.current_question]
            
            return {
                "question_id": question.question_id,
                "question_text": question.question_text,
                "option_a": question.option_a,
                "option_b": question.option_b,
                "option_c": question.option_c,
                "option_d": question.option_d,
                "current_question": session.current_question + 1,
                "total_questions": session.total_questions
            }
            
        except Exception as e:
            logger.error(f"Error in get_current_question: {e}")
            return None
    
    def submit_answer(self, session_id: int, question_id: int, user_answer: str) -> Dict[str, Any]:
        """Submit an answer and return result"""
        try:
            session = self.db.query(QuizSession).filter(QuizSession.id == session_id).first()
            if not session or session.is_completed:
                return {"error": "Session not found or completed"}
            
            # Get the question
            question = self.db.query(Question).filter(Question.question_id == question_id).first()
            if not question:
                return {"error": "Question not found"}
            
            # Check if answer is correct
            is_correct = user_answer.upper() == question.correct_option.upper()
            
            # Create quiz answer record
            quiz_answer = QuizAnswer(
                session_id=session_id,
                question_id=question_id,
                user_answer=user_answer,
                is_correct=is_correct,
                answered_at=datetime.utcnow()
            )
            
            self.db.add(quiz_answer)
            
            # Update session
            if is_correct:
                session.correct_answers += 1
            
            session.current_question += 1
            
            # Check if quiz is complete
            if session.current_question >= session.total_questions:
                session.is_completed = True
                session.completed_at = datetime.utcnow()
                session.score_percentage = int((session.correct_answers / session.total_questions) * 100)
                
                # Create quiz result
                quiz_result = QuizResult(
                    user_id=session.user_id,
                    unit=session.unit or "General",
                    topic=session.topic or "General",
                    score=session.score_percentage,
                    total_questions=session.total_questions,
                    correct=session.correct_answers,
                    wrong=session.total_questions - session.correct_answers,
                    date=datetime.utcnow()
                )
                
                self.db.add(quiz_result)
                
                # Update user stats
                user = self.db.query(User).filter(User.user_id == session.user_id).first()
                if user:
                    user.total_quizzes_taken += 1
                    # Update average accuracy
                    if user.average_accuracy is None:
                        user.average_accuracy = session.score_percentage
                    else:
                        user.average_accuracy = int((user.average_accuracy + session.score_percentage) / 2)
            
            self.db.commit()
            
            return {
                "is_correct": is_correct,
                "correct_answer": question.correct_option,
                "explanation": question.explanation,
                "current_score": session.correct_answers,
                "total_questions": session.total_questions,
                "is_complete": session.is_completed,
                "final_score": session.score_percentage if session.is_completed else None
            }
            
        except Exception as e:
            logger.error(f"Error in submit_answer: {e}")
            self.db.rollback()
            return {"error": "Failed to submit answer"}
    
    def get_quiz_results(self, session_id: int) -> Optional[Dict[str, Any]]:
        """Get quiz results for a completed session"""
        try:
            session = self.db.query(QuizSession).filter(QuizSession.id == session_id).first()
            if not session or not session.is_completed:
                return None
            
            return {
                "session_id": session_id,
                "score_percentage": session.score_percentage,
                "correct_answers": session.correct_answers,
                "total_questions": session.total_questions,
                "wrong_answers": session.total_questions - session.correct_answers,
                "completed_at": session.completed_at,
                "grade": self._calculate_grade(session.score_percentage)
            }
            
        except Exception as e:
            logger.error(f"Error in get_quiz_results: {e}")
            return None
    
    def get_user_quiz_history(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's quiz history"""
        try:
            results = self.db.query(QuizResult).filter(
                QuizResult.user_id == user_id
            ).order_by(QuizResult.date.desc()).limit(limit).all()
            
            return [
                {
                    "result_id": result.result_id,
                    "unit": result.unit,
                    "topic": result.topic,
                    "score": result.score,
                    "total_questions": result.total_questions,
                    "correct": result.correct,
                    "wrong": result.wrong,
                    "date": result.date,
                    "grade": self._calculate_grade(result.score)
                }
                for result in results
            ]
            
        except Exception as e:
            logger.error(f"Error in get_user_quiz_history: {e}")
            return []
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user's overall quiz statistics"""
        try:
            user = self.db.query(User).filter(User.user_id == user_id).first()
            if not user:
                return {}
            
            # Get recent quiz results
            recent_results = self.db.query(QuizResult).filter(
                QuizResult.user_id == user_id
            ).order_by(QuizResult.date.desc()).limit(10).all()
            
            if not recent_results:
                return {
                    "total_quizzes": 0,
                    "average_score": 0,
                    "best_score": 0,
                    "recent_performance": []
                }
            
            scores = [result.score for result in recent_results]
            
            return {
                "total_quizzes": user.total_quizzes_taken,
                "average_score": user.average_accuracy or 0,
                "best_score": max(scores),
                "recent_performance": [
                    {
                        "unit": result.unit,
                        "score": result.score,
                        "date": result.date
                    }
                    for result in recent_results[:5]
                ]
            }
            
        except Exception as e:
            logger.error(f"Error in get_user_stats: {e}")
            return {}
    
    def _calculate_grade(self, score_percentage: int) -> str:
        """Calculate grade based on score percentage"""
        if score_percentage >= 90:
            return "A+"
        elif score_percentage >= 80:
            return "A"
        elif score_percentage >= 70:
            return "B+"
        elif score_percentage >= 60:
            return "B"
        elif score_percentage >= 50:
            return "C+"
        elif score_percentage >= 40:
            return "C"
        else:
            return "F"
    
    def get_leaderboard(self, unit: str = None, topic: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Get leaderboard for a specific unit/topic"""
        try:
            query = self.db.query(
                User.name,
                User.username,
                func.avg(QuizResult.score).label('avg_score'),
                func.count(QuizResult.result_id).label('total_quizzes')
            ).join(QuizResult, User.user_id == QuizResult.user_id)
            
            if unit:
                query = query.filter(QuizResult.unit == unit)
            
            if topic:
                query = query.filter(QuizResult.topic == topic)
            
            # Only include users with at least 3 quizzes for fair comparison
            query = query.having(func.count(QuizResult.result_id) >= 3)
            
            leaderboard = query.group_by(User.user_id, User.name, User.username)\
                             .order_by(desc('avg_score'))\
                             .limit(limit)\
                             .all()
            
            return [
                {
                    "rank": idx + 1,
                    "name": user.name,
                    "username": user.username,
                    "avg_score": round(user.avg_score, 1),
                    "total_quizzes": user.total_quizzes
                }
                for idx, user in enumerate(leaderboard)
            ]
            
        except Exception as e:
            logger.error(f"Error in get_leaderboard: {e}")
            return []
    
    def get_quiz_statistics(self, unit: str = None, topic: str = None) -> Dict[str, Any]:
        """Get quiz statistics for a unit/topic"""
        try:
            query = self.db.query(QuizResult)
            
            if unit:
                query = query.filter(QuizResult.unit == unit)
            
            if topic:
                query = query.filter(QuizResult.topic == topic)
            
            results = query.all()
            
            if not results:
                return {
                    "total_quizzes": 0,
                    "avg_score": 0,
                    "total_participants": 0,
                    "score_distribution": {}
                }
            
            scores = [result.score for result in results]
            participants = len(set(result.user_id for result in results))
            
            # Score distribution
            score_ranges = {
                "90-100": len([s for s in scores if 90 <= s <= 100]),
                "80-89": len([s for s in scores if 80 <= s <= 89]),
                "70-79": len([s for s in scores if 70 <= s <= 79]),
                "60-69": len([s for s in scores if 60 <= s <= 69]),
                "0-59": len([s for s in scores if 0 <= s <= 59])
            }
            
            return {
                "total_quizzes": len(results),
                "avg_score": round(sum(scores) / len(scores), 1),
                "total_participants": participants,
                "score_distribution": score_ranges,
                "highest_score": max(scores),
                "lowest_score": min(scores)
            }
            
        except Exception as e:
            logger.error(f"Error in get_quiz_statistics: {e}")
            return {}
    
    def get_user_rank(self, user_id: int, unit: str = None, topic: str = None) -> Dict[str, Any]:
        """Get user's rank in leaderboard"""
        try:
            # Get user's average score
            user_query = self.db.query(
                func.avg(QuizResult.score).label('avg_score'),
                func.count(QuizResult.result_id).label('total_quizzes')
            ).filter(QuizResult.user_id == user_id)
            
            if unit:
                user_query = user_query.filter(QuizResult.unit == unit)
            
            if topic:
                user_query = user_query.filter(QuizResult.topic == topic)
            
            user_stats = user_query.first()
            
            if not user_stats or user_stats.total_quizzes < 3:
                return {"rank": None, "message": "Not enough quizzes for ranking"}
            
            # Count users with higher average scores
            rank_query = self.db.query(User.user_id)\
                               .join(QuizResult, User.user_id == QuizResult.user_id)
            
            if unit:
                rank_query = rank_query.filter(QuizResult.unit == unit)
            
            if topic:
                rank_query = rank_query.filter(QuizResult.topic == topic)
            
            higher_scores = rank_query.group_by(User.user_id)\
                                    .having(func.avg(QuizResult.score) > user_stats.avg_score)\
                                    .count()
            
            rank = higher_scores + 1
            
            return {
                "rank": rank,
                "avg_score": round(user_stats.avg_score, 1),
                "total_quizzes": user_stats.total_quizzes
            }
            
        except Exception as e:
            logger.error(f"Error in get_user_rank: {e}")
            return {"rank": None, "message": "Error calculating rank"}
    
    def close(self):
        """Close database session"""
        self.db.close()
