"""
Student Handlers for BotCamp Medical
Implements Part 4 - Student role functionality
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User, Question, QuizSession
from database.db_v2 import SessionLocal
from services.session_service import SessionService
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

class StudentHandlers:
    def __init__(self):
        self.session_service = SessionService()
        self.analytics_service = AnalyticsService()
    
    async def start_quiz_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start_quiz command - Student only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is student
            user_role = self.session_service.get_user_state(user_id)
            if not user_role or user_role.role != "student":
                await update.message.reply_text("❌ Student access required.")
                return
            
            # Validate user selection
            validation = self.session_service.validate_user_selection(user_id)
            
            if not validation['valid']:
                missing = ", ".join(validation['missing'])
                await update.message.reply_text(
                    f"❌ Please complete your selection first. Missing: {missing}\n\n"
                    f"Use the menu to select University → Course → Year → Unit → Topic"
                )
                return
            
            # Get available topics for the selected unit
            session = SessionLocal()
            try:
                # Find questions for the selected topic
                questions = session.query(Question).filter(
                    Question.topic_id == validation['state'].topic_id,
                    Question.is_active == True
                ).limit(10).all()
                
                if not questions:
                    await update.message.reply_text(
                        "❌ No questions available for this topic yet.\n\n"
                        "Please check back later or contact an admin to upload questions."
                    )
                    return
                
                # Create quiz session
                quiz_session = QuizSession(
                    user_id=user_id,
                    topic_id=validation['state'].topic_id,
                    total_questions=len(questions),
                    started_at=datetime.utcnow()
                )
                
                session.add(quiz_session)
                session.commit()
                session.refresh(quiz_session)
                
                # Start first question
                await self._show_question(update, quiz_session, questions[0], 1)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in start_quiz_command: {e}")
            await update.message.reply_text("❌ Error starting quiz.")
    
    async def view_my_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_my_stats command - Student only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is student
            user_role = self.session_service.get_user_state(user_id)
            if not user_role or user_role.role != "student":
                await update.message.reply_text("❌ Student access required.")
                return
            
            # Get student analytics
            analytics = self.analytics_service.get_quiz_analytics(user_id=user_id)
            
            if not analytics:
                await update.message.reply_text(
                    "📊 **Your Statistics**\n\n"
                    "No quiz data available yet.\n"
                    "Take some quizzes to see your performance statistics!"
                )
                return
            
            message = f"""📊 **Your Statistics**

**🎯 Overall Performance:**
• Total Quizzes: {analytics.get('total_quizzes', 0)}
• Total Questions: {analytics.get('total_questions', 0)}
• Correct Answers: {analytics.get('correct_answers', 0)}
• Accuracy Rate: {analytics.get('accuracy_rate', 0):.1f}%

**⏱️ Timing:**
• Average Time per Question: {analytics.get('avg_time_per_question', 0):.1f}s
• Total Study Time: {analytics.get('total_study_time', 0):.1f} minutes

**📈 Recent Performance:**
• Last 7 Days: {analytics.get('recent_accuracy', 0):.1f}% accuracy
• Best Score: {analytics.get('best_score', 0):.1f}%
• Average Score: {analytics.get('avg_score', 0):.1f}%"""
            
            # Add topic breakdown if available
            if analytics.get('topic_performance'):
                message += "\n\n**📚 Topic Performance:**\n"
                for topic, performance in list(analytics['topic_performance'].items())[:5]:
                    message += f"• {topic}: {performance['accuracy']:.1f}% ({performance['questions']} questions)\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in view_my_stats_command: {e}")
            await update.message.reply_text("❌ Error retrieving statistics.")
    
    async def report_error_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /report_error command - Student only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is student
            user_role = self.session_service.get_user_state(user_id)
            if not user_role or user_role.role != "student":
                await update.message.reply_text("❌ Student access required.")
                return
            
            if not context.args:
                await update.message.reply_text(
                    "Usage: /report_error <question_id> <description>\n\n"
                    "Example: /report_error 123 This question has incorrect answer"
                )
                return
            
            try:
                question_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Question ID must be a number.")
                return
            
            description = " ".join(context.args[1:]) if len(context.args) > 1 else "No description provided"
            
            # Log the error report
            session = SessionLocal()
            try:
                # Check if question exists
                question = session.query(Question).filter(Question.question_id == question_id).first()
                
                if not question:
                    await update.message.reply_text("❌ Question not found.")
                    return
                
                # Create error report (you can create a separate table for this)
                # For now, we'll log it in the system logs
                from database.models import SystemLog
                
                error_log = SystemLog(
                    action="question_error_report",
                    details=f"Question {question_id} reported by user {user_id}: {description}",
                    timestamp=datetime.utcnow()
                )
                
                session.add(error_log)
                session.commit()
                
                await update.message.reply_text(
                    f"✅ **Error Report Submitted**\n\n"
                    f"**Question ID:** {question_id}\n"
                    f"**Description:** {description}\n\n"
                    f"Thank you for helping improve the quality of our questions! "
                    f"Our admins will review your report."
                )
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in report_error_command: {e}")
            await update.message.reply_text("❌ Error submitting report.")
    
    async def student_dashboard_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle student dashboard callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            callback_data = query.data
            
            if callback_data == "student_take_quiz":
                await self.start_quiz_command(update, context)
            elif callback_data == "student_view_stats":
                await self.view_my_stats_command(update, context)
            elif callback_data == "student_report_error":
                await query.edit_message_text(
                    "📝 **Report Question Error**\n\n"
                    "To report an error in a question, use:\n"
                    "`/report_error <question_id> <description>`\n\n"
                    "Example:\n"
                    "`/report_error 123 This question has incorrect answer`",
                    parse_mode='Markdown'
                )
            elif callback_data == "student_about":
                await self._show_about_info(query)
            elif callback_data == "student_select_university":
                await self._show_university_selection(query)
                
        except Exception as e:
            logger.error(f"Error in student_dashboard_handler: {e}")
    
    async def _show_question(self, update: Update, quiz_session: QuizSession, question: Question, question_num: int):
        """Show quiz question to student"""
        try:
            message = f"""🎯 **Question {question_num}/{quiz_session.total_questions}**

{question.question_text}

**Options:**
A) {question.option_a}
B) {question.option_b}
C) {question.option_c}
D) {question.option_d}"""
            
            keyboard = [
                [InlineKeyboardButton("A", callback_data=f"answer_A_{quiz_session.id}")],
                [InlineKeyboardButton("B", callback_data=f"answer_B_{quiz_session.id}")],
                [InlineKeyboardButton("C", callback_data=f"answer_C_{quiz_session.id}")],
                [InlineKeyboardButton("D", callback_data=f"answer_D_{quiz_session.id}")],
                [InlineKeyboardButton("❌ Quit Quiz", callback_data=f"quit_quiz_{quiz_session.id}")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
        except Exception as e:
            logger.error(f"Error showing question: {e}")
    
    async def _show_about_info(self, query):
        """Show about information for students"""
        try:
            message = """ℹ️ **About BotCamp Medical**

**🎯 Mission:**
BotCamp Medical helps medical students prepare for exams through interactive quizzes and practice questions.

**📚 Features:**
• University-specific content
• Topic-based quizzes
• Performance tracking
• Instant feedback
• Quality questions from verified sources

**👥 Contributors:**
Questions are uploaded and reviewed by qualified medical professionals and educators.

**📞 Support:**
Need help? Contact @BotCampSupport

**🔒 Privacy:**
Your progress is tracked anonymously for analytics purposes only."""
            
            keyboard = [
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing about info: {e}")
    
    async def _show_university_selection(self, query):
        """Show university selection for students"""
        try:
            # This would integrate with the existing university selection flow
            # For now, show a simple message
            await query.edit_message_text(
                "🏫 **Select University**\n\n"
                "Please use the main menu to select your university and course.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error showing university selection: {e}")
    
    async def handle_quiz_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quiz answer selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            callback_data = query.data
            
            if not callback_data.startswith("answer_"):
                return
            
            # Parse callback data: answer_A_123
            parts = callback_data.split("_")
            if len(parts) != 3:
                return
            
            selected_option = parts[1]  # A, B, C, or D
            quiz_session_id = int(parts[2])
            
            # Get quiz session and current question
            session = SessionLocal()
            try:
                quiz_session = session.query(QuizSession).filter(
                    QuizSession.id == quiz_session_id,
                    QuizSession.user_id == user_id
                ).first()
                
                if not quiz_session:
                    await query.edit_message_text("❌ Quiz session not found.")
                    return
                
                # Get current question
                questions = session.query(Question).filter(
                    Question.topic_id == quiz_session.topic_id,
                    Question.is_active == True
                ).limit(quiz_session.total_questions).all()
                
                current_question = questions[quiz_session.current_question] if quiz_session.current_question < len(questions) else None
                
                if not current_question:
                    await query.edit_message_text("❌ Question not found.")
                    return
                
                # Check if answer is correct
                is_correct = selected_option == current_question.correct_option
                
                if is_correct:
                    quiz_session.correct_answers += 1
                
                quiz_session.current_question += 1
                session.commit()
                
                # Show result and next question or completion
                if quiz_session.current_question >= quiz_session.total_questions:
                    # Quiz completed
                    await self._show_quiz_completion(query, quiz_session)
                else:
                    # Show next question
                    next_question = questions[quiz_session.current_question]
                    await self._show_question_result(query, is_correct, current_question, next_question, quiz_session.current_question + 1)
                
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error handling quiz answer: {e}")
    
    async def _show_question_result(self, query, is_correct: bool, question: Question, next_question: Question, question_num: int):
        """Show question result and next question"""
        try:
            result_emoji = "✅" if is_correct else "❌"
            result_text = "Correct!" if is_correct else f"Incorrect. The correct answer is {question.correct_option}."
            
            message = f"""{result_emoji} **{result_text}**

**Explanation:**
{question.explanation or 'No explanation available.'}

**Uploaded by:** {question.uploader_username or 'Admin'}

---

🎯 **Question {question_num}**

{next_question.question_text}

**Options:**
A) {next_question.option_a}
B) {next_question.option_b}
C) {next_question.option_c}
D) {next_question.option_d}"""
            
            keyboard = [
                [InlineKeyboardButton("A", callback_data=f"answer_A_{query.data.split('_')[2]}")],
                [InlineKeyboardButton("B", callback_data=f"answer_B_{query.data.split('_')[2]}")],
                [InlineKeyboardButton("C", callback_data=f"answer_C_{query.data.split('_')[2]}")],
                [InlineKeyboardButton("D", callback_data=f"answer_D_{query.data.split('_')[2]}")],
                [InlineKeyboardButton("❌ Quit Quiz", callback_data=f"quit_quiz_{query.data.split('_')[2]}")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing question result: {e}")
    
    async def _show_quiz_completion(self, query, quiz_session: QuizSession):
        """Show quiz completion results"""
        try:
            percentage = (quiz_session.correct_answers / quiz_session.total_questions) * 100
            
            # Calculate grade
            if percentage >= 80:
                grade = "A"
                grade_emoji = "🌟"
            elif percentage >= 65:
                grade = "B"
                grade_emoji = "⭐"
            elif percentage >= 50:
                grade = "C"
                grade_emoji = "👍"
            elif percentage >= 35:
                grade = "D"
                grade_emoji = "📚"
            else:
                grade = "E"
                grade_emoji = "💪"
            
            message = f"""{grade_emoji} **Quiz Completed!**

**Your Score:** {quiz_session.correct_answers}/{quiz_session.total_questions} ({percentage:.1f}%)
**Grade:** {grade}

**Performance:**
{grade_emoji} {'Excellent!' if percentage >= 80 else 'Good job!' if percentage >= 65 else 'Keep practicing!' if percentage >= 50 else 'Study more!' if percentage >= 35 else 'Don\'t give up!'}

**Next Steps:**
• Review the questions you got wrong
• Take another quiz to improve
• Study the topic more thoroughly"""
            
            keyboard = [
                [InlineKeyboardButton("▶️ Take Another Quiz", callback_data="retake_same_topic")],
                [InlineKeyboardButton("🔁 Change Topic", callback_data="change_topic")],
                [InlineKeyboardButton("📊 View My Stats", callback_data="student_view_stats")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error showing quiz completion: {e}")
