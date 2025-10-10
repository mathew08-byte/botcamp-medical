import random
from datetime import datetime
from typing import List, Tuple, Optional
from sqlalchemy.orm import Session
from models import QuizSession, QuizAnswer, Question
from services.analytics_service import AnalyticsService


class QuizEngine:
    def __init__(self, db: Session):
        self.db = db

    def start_quiz(self, user_id: int, topic_id: int, num_questions: int = 10) -> Tuple[Optional[QuizSession], List[Question]]:
        """
        Start a new quiz session for a user on a specific topic.
        Returns (session, questions) or (None, []) if no questions available.
        """
        # Fetch available questions for the topic
        questions = (
            self.db.query(Question)
            .filter_by(topic_id=topic_id, is_active=True)
            .order_by(Question.created_at.desc())
            .limit(100)  # Get more than needed for randomization
            .all()
        )
        
        if not questions:
            return None, []
        
        # Select random questions
        selected = random.sample(questions, min(num_questions, len(questions)))
        
        # Create quiz session
        session = QuizSession(
            user_id=user_id,
            topic_id=topic_id,
            total_questions=len(selected),
            current_question=0,
            correct_answers=0,
            started_at=datetime.utcnow(),
            is_completed=False,
        )
        
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        
        # Store question IDs in session for reference
        question_ids = [str(q.id) for q in selected]
        session.question_ids = ','.join(question_ids)
        self.db.commit()
        
        return session, selected

    def get_current_question(self, session: QuizSession) -> Optional[Question]:
        """Get the current question for a quiz session."""
        if not session.question_ids:
            return None
            
        question_id_list = [int(qid) for qid in session.question_ids.split(',')]
        
        if session.current_index >= len(question_id_list):
            return None
            
        current_question_id = question_id_list[session.current_index]
        return self.db.query(Question).filter_by(id=current_question_id).first()

    def submit_answer(self, session: QuizSession, answer_index: int) -> Tuple[bool, str, Optional[str]]:
        """
        Submit an answer for the current question.
        Returns (is_correct, correct_answer_text, explanation)
        """
        question = self.get_current_question(session)
        if not question:
            return False, "", None
        
        is_correct = answer_index == question.correct_index
        correct_answer_text = question.options_json[question.correct_index]
        
        # Save the answer
        quiz_answer = QuizAnswer(
            session_id=session.id,
            question_id=question.id,
            user_answer_index=answer_index,
            is_correct=is_correct,
            answered_at=datetime.utcnow()
        )
        
        self.db.add(quiz_answer)
        
        # Update session
        if is_correct:
            session.correct_answers += 1
        session.current_question += 1
        
        self.db.commit()
        
        return is_correct, correct_answer_text, question.explanation

    def complete_quiz(self, session: QuizSession) -> Tuple[float, str]:
        """
        Mark quiz as completed and calculate final score.
        Returns (percentage, grade)
        """
        percentage = (session.correct_answers / session.total_questions) * 100
        
        # Calculate grade
        if percentage >= 80:
            grade = "A"
        elif percentage >= 65:
            grade = "B"
        elif percentage >= 50:
            grade = "C"
        elif percentage >= 35:
            grade = "D"
        else:
            grade = "E"
        
        # Calculate duration
        duration_seconds = None
        if session.started_at:
            duration_seconds = int((datetime.utcnow() - session.started_at).total_seconds())
        
        # Update session with analytics data
        session.is_completed = True
        session.completed_at = datetime.utcnow()
        session.score_percent = percentage
        session.score_percentage = percentage
        session.grade = grade
        session.accuracy = int(percentage)
        session.duration_seconds = duration_seconds
        
        # Create topic accuracy breakdown (simplified for now)
        topic_accuracy_breakdown = {
            "topic_id": session.topic_id,
            "accuracy": int(percentage),
            "questions_attempted": session.total_questions,
            "correct_answers": session.correct_answers
        }
        session.topic_accuracy_breakdown = topic_accuracy_breakdown
        
        self.db.commit()
        
        # Update user analytics
        try:
            analytics_service = AnalyticsService()
            analytics_service.update_user_analytics(session.user_id, session)
        except Exception as e:
            # Log error but don't fail the quiz completion
            print(f"Error updating user analytics: {e}")
        
        return percentage, grade

    def get_quiz_history(self, user_id: int, limit: int = 5) -> List[QuizSession]:
        """Get recent quiz history for a user."""
        return (
            self.db.query(QuizSession)
            .filter_by(user_id=user_id, is_completed=True)
            .order_by(QuizSession.completed_at.desc())
            .limit(limit)
            .all()
        )

    def get_last_quiz_topic(self, user_id: int) -> Optional[int]:
        """Get the topic ID of the user's last completed quiz."""
        last_quiz = (
            self.db.query(QuizSession)
            .filter_by(user_id=user_id, is_completed=True)
            .order_by(QuizSession.completed_at.desc())
            .first()
        )
        return last_quiz.topic_id if last_quiz else None

    def is_quiz_in_progress(self, user_id: int) -> Optional[QuizSession]:
        """Check if user has an active quiz session."""
        return (
            self.db.query(QuizSession)
            .filter_by(user_id=user_id, is_completed=False)
            .first()
        )

    def quit_quiz(self, session: QuizSession):
        """Quit an active quiz session."""
        session.is_completed = True
        session.completed_at = datetime.utcnow()
        session.score_percent = (session.correct_answers / session.current_question) * 100 if session.current_question > 0 else 0
        session.score_percentage = session.score_percent
        session.grade = "Incomplete"
        self.db.commit()
