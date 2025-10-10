import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_v2 import SessionLocal
from models import User, Topic, QuizSession
from bot.services.quiz_engine import QuizEngine
from bot.utils.formatters import (
    format_question, 
    format_quiz_result, 
    format_quiz_history,
    format_answer_feedback
)


async def start_quiz_for_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a quiz when a topic is selected."""
    query = update.callback_query
    await query.answer()
    
    _, _, topic_id = query.data.partition("stu_topic_")
    topic_id = int(topic_id)
    
    db = SessionLocal()
    try:
        # Get user from database
        user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await query.edit_message_text("❌ User not found. Please use /start first.")
            return
        
        # Check if user already has an active quiz
        quiz_engine = QuizEngine(db)
        active_session = quiz_engine.is_quiz_in_progress(user.id)
        if active_session:
            await query.edit_message_text(
                "⚠️ You already have an active quiz in progress. Please complete it first or use /quit_quiz to cancel."
            )
            return
        
        # Get topic info
        topic = db.query(Topic).filter_by(id=topic_id).first()
        if not topic:
            await query.edit_message_text("❌ Topic not found.")
            return
        
        # Start new quiz
        session, questions = quiz_engine.start_quiz(user.id, topic_id)
        
        if not session or not questions:
            await query.edit_message_text(
                f"❌ No questions available for '{topic.name}'. Please try another topic."
            )
            return
        
        # Store session in context for later use
        context.user_data['current_quiz_session'] = session.id
        context.user_data['current_quiz_engine'] = quiz_engine
        
        # Show first question
        await show_question(update, context, session, questions[0], 1, len(questions))
        
    finally:
        db.close()


async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                       session, question, question_num: int, total_questions: int):
    """Display a question with answer options."""
    # Format question text
    question_text = format_question(question, question_num, total_questions)
    
    # Create answer buttons
    keyboard = []
    for i, option in enumerate(question.options_json):
        keyboard.append([InlineKeyboardButton(
            f"{chr(65+i)}) {option}",
            callback_data=f"quiz_answer_{session.id}_{i}"
        )])
    
    # Add quit button
    keyboard.append([InlineKeyboardButton("🚪 Quit Quiz", callback_data=f"quit_quiz_{session.id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(
            question_text, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=question_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


async def handle_quiz_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user selects an answer."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: quiz_answer_{session_id}_{answer_index}
    _, _, rest = query.data.partition("quiz_answer_")
    session_id, _, answer_index = rest.partition("_")
    session_id = int(session_id)
    answer_index = int(answer_index)
    
    db = SessionLocal()
    try:
        # Get session and quiz engine
        session = db.query(QuizSession).filter_by(id=session_id).first()
        if not session:
            await query.edit_message_text("❌ Quiz session not found.")
            return
        
        quiz_engine = QuizEngine(db)
        
        # Submit answer
        is_correct, correct_answer, explanation = quiz_engine.submit_answer(session, answer_index)
        
        # Show feedback
        feedback = format_answer_feedback(is_correct, correct_answer, explanation)
        
        # Disable buttons and show feedback
        keyboard = [[InlineKeyboardButton("✅ Answer Recorded", callback_data="noop")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            feedback,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        # Check if quiz is complete
        if session.current_question >= session.total_questions:
            # Quiz completed
            quiz_engine.complete_quiz(session)
            
            # Get topic name
            topic = db.query(Topic).filter_by(id=session.topic_id).first()
            topic_name = topic.name if topic else "Unknown Topic"
            
            # Show results
            result_text = format_quiz_result(session, topic_name)
            
            # Create result buttons
            keyboard = [
                [InlineKeyboardButton("🔄 Retake Quiz", callback_data=f"retake_quiz_{session.topic_id}")],
                [InlineKeyboardButton("📚 Quiz History", callback_data="quiz_history")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await asyncio.sleep(2)  # Brief delay before showing results
            await query.edit_message_text(
                result_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            # Clear context
            if 'current_quiz_session' in context.user_data:
                del context.user_data['current_quiz_session']
            if 'current_quiz_engine' in context.user_data:
                del context.user_data['current_quiz_engine']
        else:
            # Show next question after delay
            await asyncio.sleep(2)
            next_question = quiz_engine.get_current_question(session)
            if next_question:
                await show_question(
                    update, context, session, next_question, 
                    session.current_question + 1, session.total_questions
                )
        
    finally:
        db.close()


async def quit_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz quit request."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: quit_quiz_{session_id}
    _, _, session_id = query.data.partition("quit_quiz_")
    session_id = int(session_id)
    
    db = SessionLocal()
    try:
        session = db.query(QuizSession).filter_by(id=session_id).first()
        if not session:
            await query.edit_message_text("❌ Quiz session not found.")
            return
        
        quiz_engine = QuizEngine(db)
        quiz_engine.quit_quiz(session)
        
        await query.edit_message_text(
            "⏸️ Quiz cancelled. Your progress has been saved.\n\nUse /start to return to the main menu."
        )
        
        # Clear context
        if 'current_quiz_session' in context.user_data:
            del context.user_data['current_quiz_session']
        if 'current_quiz_engine' in context.user_data:
            del context.user_data['current_quiz_engine']
        
    finally:
        db.close()


async def retake_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retake a quiz for the same topic."""
    query = update.callback_query
    await query.answer()
    
    # Parse callback data: retake_quiz_{topic_id}
    _, _, topic_id = query.data.partition("retake_quiz_")
    topic_id = int(topic_id)
    
    # Simulate the topic selection to start a new quiz
    query.data = f"stu_topic_{topic_id}"
    await start_quiz_for_topic(update, context)


async def show_quiz_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's quiz history."""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Get quiz history
        quiz_engine = QuizEngine(db)
        history = quiz_engine.get_quiz_history(user.id, limit=5)
        
        # Format and display
        history_text = format_quiz_history(history)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Retake Last Quiz", callback_data="retry_last")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            history_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def retry_last_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retry the last quiz topic."""
    query = update.callback_query
    await query.answer()
    
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await query.edit_message_text("❌ User not found.")
            return
        
        # Get last quiz topic
        quiz_engine = QuizEngine(db)
        last_topic_id = quiz_engine.get_last_quiz_topic(user.id)
        
        if not last_topic_id:
            await query.edit_message_text("❌ No previous quiz found.")
            return
        
        # Start new quiz for the same topic
        query.data = f"stu_topic_{last_topic_id}"
        await start_quiz_for_topic(update, context)
        
    finally:
        db.close()


# Command handlers
async def quiz_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quiz_history command."""
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        # Get quiz history
        quiz_engine = QuizEngine(db)
        history = quiz_engine.get_quiz_history(user.id, limit=5)
        
        # Format and display
        history_text = format_quiz_history(history)
        
        keyboard = [
            [InlineKeyboardButton("🔄 Retake Last Quiz", callback_data="retry_last")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            history_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    finally:
        db.close()


async def retry_last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /retry_last command."""
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        # Get last quiz topic
        quiz_engine = QuizEngine(db)
        last_topic_id = quiz_engine.get_last_quiz_topic(user.id)
        
        if not last_topic_id:
            await update.message.reply_text("❌ No previous quiz found.")
            return
        
        # Start new quiz for the same topic
        update.callback_query = type('obj', (object,), {'data': f'stu_topic_{last_topic_id}', 'answer': lambda: None})()
        await start_quiz_for_topic(update, context)
        
    finally:
        db.close()


async def quit_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /quit_quiz command."""
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter_by(telegram_id=update.effective_user.id).first()
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        # Check for active quiz
        quiz_engine = QuizEngine(db)
        active_session = quiz_engine.is_quiz_in_progress(user.id)
        
        if not active_session:
            await update.message.reply_text("❌ No active quiz found.")
            return
        
        # Quit the quiz
        quiz_engine.quit_quiz(active_session)
        
        await update.message.reply_text(
            "⏸️ Quiz cancelled. Your progress has been saved.\n\nUse /start to return to the main menu."
        )
        
        # Clear context
        if 'current_quiz_session' in context.user_data:
            del context.user_data['current_quiz_session']
        if 'current_quiz_engine' in context.user_data:
            del context.user_data['current_quiz_engine']
        
    finally:
        db.close()
