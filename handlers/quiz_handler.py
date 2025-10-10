"""
Quiz handler for BotCamp Medical
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.quiz_service import QuizService
from services.user_service import UserService
import logging

logger = logging.getLogger(__name__)

class QuizHandler:
    def __init__(self):
        self.quiz_service = QuizService()
        self.user_service = UserService()
        self.active_sessions = {}  # Store active quiz sessions
    
    async def start_quiz(self, update: Update, context: ContextTypes.DEFAULT_TYPE, unit: str, topic: str = None):
        """Start a new quiz"""
        try:
            telegram_id = update.effective_user.id
            user_prefs = self.user_service.get_user_preferences(telegram_id)
            
            if not user_prefs.get("university") or not user_prefs.get("course"):
                await update.callback_query.edit_message_text(
                    "❌ Please complete your profile setup first with /start"
                )
                return
            
            # Create quiz session
            session = self.quiz_service.create_quiz_session(telegram_id, unit, topic)
            
            if not session:
                await update.callback_query.edit_message_text(
                    f"❌ No questions available for {unit}" + (f" - {topic}" if topic else "")
                )
                return
            
            # Store session in context
            self.active_sessions[telegram_id] = session.id
            
            # Get first question
            question_data = self.quiz_service.get_current_question(session.id)
            
            if not question_data:
                await update.callback_query.edit_message_text(
                    "❌ Failed to load quiz questions"
                )
                return
            
            await self.show_question(update, context, question_data)
            
        except Exception as e:
            logger.error(f"Error in start_quiz: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE, question_data: dict):
        """Show a quiz question"""
        try:
            keyboard = [
                [InlineKeyboardButton(f"A) {question_data['option_a']}", callback_data=f"answer_{question_data['question_id']}_A")],
                [InlineKeyboardButton(f"B) {question_data['option_b']}", callback_data=f"answer_{question_data['question_id']}_B")],
                [InlineKeyboardButton(f"C) {question_data['option_c']}", callback_data=f"answer_{question_data['question_id']}_C")],
                [InlineKeyboardButton(f"D) {question_data['option_d']}", callback_data=f"answer_{question_data['question_id']}_D")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            question_text = f"""📝 **Question {question_data['current_question']} of {question_data['total_questions']}**

{question_data['question_text']}

Choose your answer:"""
            
            await update.callback_query.edit_message_text(
                question_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in show_question: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_answer(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle quiz answer submission"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            
            # Get session
            if telegram_id not in self.active_sessions:
                await query.edit_message_text("❌ No active quiz session found")
                return
            
            session_id = self.active_sessions[telegram_id]
            
            # Parse callback data
            parts = query.data.split("_")
            question_id = int(parts[1])
            user_answer = parts[2]
            
            # Submit answer
            result = self.quiz_service.submit_answer(session_id, question_id, user_answer)
            
            if "error" in result:
                await query.edit_message_text(f"❌ {result['error']}")
                return
            
            # Show result
            result_text = f"""✅ **Answer Submitted!**

Your answer: **{user_answer}**
Correct answer: **{result['correct_answer']}**

{'🎉 Correct!' if result['is_correct'] else '❌ Incorrect'}

**Score: {result['current_score']}/{result['total_questions']}**"""
            
            if result['explanation']:
                result_text += f"\n\n**Explanation:**\n{result['explanation']}"
            
            if result['is_complete']:
                # Quiz completed
                result_text += f"""

🎯 **Quiz Completed!**

**Final Score: {result['final_score']}%**
**Grade: {self._calculate_grade(result['final_score'])}**

Great job! You can start another quiz anytime."""
                
                # Clean up session
                del self.active_sessions[telegram_id]
                
                keyboard = [
                    [InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")],
                    [InlineKeyboardButton("🔄 Take Another Quiz", callback_data="take_quiz")],
                    [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
                ]
            else:
                # Continue to next question
                keyboard = [
                    [InlineKeyboardButton("➡️ Next Question", callback_data="next_question")]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                result_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in handle_answer: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def next_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show next question"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            
            if telegram_id not in self.active_sessions:
                await query.edit_message_text("❌ No active quiz session found")
                return
            
            session_id = self.active_sessions[telegram_id]
            
            # Get next question
            question_data = self.quiz_service.get_current_question(session_id)
            
            if not question_data:
                await query.edit_message_text("❌ No more questions available")
                return
            
            await self.show_question(update, context, question_data)
            
        except Exception as e:
            logger.error(f"Error in next_question: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user statistics"""
        try:
            telegram_id = update.effective_user.id
            user_prefs = self.user_service.get_user_preferences(telegram_id)
            stats = self.quiz_service.get_user_stats(telegram_id)
            
            stats_text = f"""📊 **Your Statistics**

**Profile:**
🏛️ University: {user_prefs.get('university', 'Not set')}
🎓 Course: {user_prefs.get('course', 'Not set')}
📅 Year: {user_prefs.get('year', 'Not set')}

**Quiz Performance:**
📝 Total Quizzes: {stats.get('total_quizzes', 0)}
📈 Average Score: {stats.get('average_score', 0)}%
🏆 Best Score: {stats.get('best_score', 0)}%

**Recent Performance:**"""
            
            recent_performance = stats.get('recent_performance', [])
            if recent_performance:
                for perf in recent_performance:
                    stats_text += f"\n• {perf['unit']}: {perf['score']}% ({perf['date'].strftime('%Y-%m-%d')})"
            else:
                stats_text += "\n• No recent quizzes taken"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Take Quiz", callback_data="take_quiz")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                stats_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in show_stats: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
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
