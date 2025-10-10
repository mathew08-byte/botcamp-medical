from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_async_db
from database.models import User, Question, QuizSession, QuizAnswer, Topic, Paper, EventLog
from sqlalchemy import select, func
import random
import logging
from datetime import datetime
import os
from services.cache import memory_cache

logger = logging.getLogger(__name__)

def _compute_grade(percentage: int) -> str:
    if percentage >= 80:
        return 'A'
    if percentage >= 65:
        return 'B'
    if percentage >= 50:
        return 'C'
    if percentage >= 35:
        return 'D'
    return 'E'

async def take_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle take quiz callback"""
    query = update.callback_query
    await query.answer()
    
    # Check for unfinished session first
    user = update.effective_user
    unfinished_session = None
    async for db in get_async_db():
        # Find user by telegram_id
        result = await db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        if db_user:
            result = await db.execute(select(QuizSession).where(QuizSession.user_id == db_user.id, QuizSession.is_completed == False))
            unfinished_session = result.scalars().first()
    if unfinished_session:
        remaining = max(unfinished_session.total_questions - (unfinished_session.current_question or 0), 0)
        keyboard = [
            [InlineKeyboardButton("✅ Continue", callback_data=f"resume_quiz_{unfinished_session.id}")],
            [InlineKeyboardButton("❌ Start New", callback_data=f"start_new_quiz_{unfinished_session.id}")]
        ]
        await query.edit_message_text(
            f"You have an unfinished quiz with {remaining} question(s) left. Continue?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    # Get database session (list topics)
    async for db in get_async_db():
        # Get all active topics
        result = await db.execute(select(Topic).where(Topic.is_active == True))
        topics = result.scalars().all()
    
    if not topics:
        await query.edit_message_text(
            "No topics available for quizzes at the moment. Please contact an administrator.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]])
        )
        return
    
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(
            topic.name,
            callback_data=f"quiz_topic_{topic.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📚 **Select a Topic for Quiz:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def quiz_topic_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz topic selection"""
    query = update.callback_query
    await query.answer()
    
    topic_id = int(query.data.split("_")[2])
    
    # Get database session
    async for db in get_async_db():
        # Get topic
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            await query.edit_message_text("Topic not found.")
            return
        
        # Get available questions for this topic
        result = await db.execute(select(Question).where(
            Question.topic_id == topic_id,
            Question.is_active == True
        ))
        questions = result.scalars().all()
    
    if not questions:
        await query.edit_message_text(
            f"No questions available for {topic.name} at the moment.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Quiz Topics", callback_data="take_quiz")
            ]])
        )
        return
    
    # Show quiz options
    keyboard = [
        [InlineKeyboardButton("🎯 Quick Quiz (5 questions)", callback_data=f"start_quiz_{topic_id}_5")],
        [InlineKeyboardButton("📝 Standard Quiz (10 questions)", callback_data=f"start_quiz_{topic_id}_10")],
        [InlineKeyboardButton("🏆 Full Quiz (20 questions)", callback_data=f"start_quiz_{topic_id}_20")],
        [InlineKeyboardButton("🔙 Back to Quiz Topics", callback_data="take_quiz")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📚 **Quiz Options for {topic.name}:**\n\nAvailable questions: {len(questions)}",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def start_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a quiz session"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    topic_id = int(parts[2])
    num_questions = int(parts[3])
    
    user = update.effective_user
    
    # Get database session
    async for db in get_async_db():
        # Get user
        result = await db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            await query.edit_message_text("User not found. Please use /start first.")
            return
        
        # Get topic
        result = await db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            await query.edit_message_text("Topic not found.")
            return
        
        # Get available questions
        result = await db.execute(select(Question).where(
            Question.topic_id == topic_id,
            Question.is_active == True
        ))
        all_questions = result.scalars().all()
        
        if len(all_questions) < num_questions:
            await query.edit_message_text(
                f"Not enough questions available. Only {len(all_questions)} questions found.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back to Quiz Options", callback_data=f"quiz_topic_{topic_id}")
                ]])
            )
            return
        
        # Cache question ids for this user/topic session to avoid repeated DB hits
        qkey = f"quiz_qids_{db_user.id}_{topic_id}_{num_questions}"
        qids = memory_cache.get(qkey)
        if not qids:
            qids = [q.id for q in all_questions]
            random.shuffle(qids)
            qids = qids[:num_questions]
            ttl = 600
            memory_cache.set(qkey, qids, ttl)
        selected_questions = []
        for qid in qids:
            result = await db.execute(select(Question).where(Question.id == qid))
            qobj = result.scalar_one_or_none()
            if qobj:
                selected_questions.append(qobj)
        
        # Create quiz session
        quiz_session = QuizSession(
            user_id=db_user.id,
            topic_id=topic_id,
            total_questions=num_questions,
            current_question=0
        )
        db.add(quiz_session)
        # Persist question id order on the session for resume
        try:
            quiz_session.question_ids = ",".join(str(qid) for qid in qids)
        except Exception:
            pass
        await db.commit()
        # Event log: quiz started
        async for db in get_async_db():
            db.add(EventLog(user_id=db_user.id, event_type="quiz_start", context={"topic_id": topic_id, "num_questions": num_questions}))
            await db.commit()
        await db.refresh(quiz_session)
        
        # Store questions in context for this session
        context.user_data[f"quiz_{quiz_session.id}_questions"] = [q.id for q in selected_questions]
        context.user_data[f"quiz_{quiz_session.id}_session_id"] = quiz_session.id
        
        # Start with first question
        await show_question(update, context, quiz_session.id, selected_questions[0], 1, num_questions)

async def show_question(update: Update, context: ContextTypes.DEFAULT_TYPE, session_id: int, question: Question, question_num: int, total_questions: int):
    """Show a quiz question"""
    query = update.callback_query
    
    uploader_tag = None
    if getattr(question, 'uploader', None) and getattr(question.uploader, 'username', None):
        uploader_tag = f"\n_Uploaded by @{question.uploader.username}_"
    elif getattr(question, 'uploader_user_id', None):
        uploader_tag = ""
    else:
        uploader_tag = ""

    question_text = f"""
📝 **Question {question_num} of {total_questions}**

{question.question_text}

**Options:**
A) {question.option_a}
B) {question.option_b}
C) {question.option_c}
D) {question.option_d}{uploader_tag}
"""
    
    keyboard = [
        [InlineKeyboardButton("A", callback_data=f"answer_{session_id}_{question.id}_A")],
        [InlineKeyboardButton("B", callback_data=f"answer_{session_id}_{question.id}_B")],
        [InlineKeyboardButton("C", callback_data=f"answer_{session_id}_{question.id}_C")],
        [InlineKeyboardButton("D", callback_data=f"answer_{session_id}_{question.id}_D")],
        [InlineKeyboardButton("❌ End Quiz", callback_data=f"end_quiz_{session_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(
            question_text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        # This would be used for sending new messages
        pass

async def answer_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle answer selection"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    session_id = int(parts[1])
    question_id = int(parts[2])
    user_answer = parts[3]
    
    # Get database session
    async for db in get_async_db():
        # Get quiz session
        result = await db.execute(select(QuizSession).where(QuizSession.id == session_id))
        quiz_session = result.scalar_one_or_none()
        
        if not quiz_session:
            await query.edit_message_text("Quiz session not found.")
            return
        
        # Get question
        result = await db.execute(select(Question).where(Question.id == question_id))
        question = result.scalar_one_or_none()
        
        if not question:
            await query.edit_message_text("Question not found.")
            return
        
        # Check if answer is correct
        is_correct = user_answer == question.correct_answer
        
        # Save answer
        quiz_answer = QuizAnswer(
            session_id=session_id,
            question_id=question_id,
            user_answer=user_answer,
            is_correct=is_correct
        )
        db.add(quiz_answer)
        
        # Update session
        quiz_session.current_question += 1
        if is_correct:
            quiz_session.correct_answers += 1
        
        await db.commit()
        
        # Show feedback
        correct_option_map = {
            'A': question.option_a,
            'B': question.option_b,
            'C': question.option_c,
            'D': question.option_d,
        }
        feedback_text = f"""
{'✅ Correct!' if is_correct else '❌ Incorrect.'}

**Your answer:** {user_answer}) {correct_option_map.get(user_answer, '')}
**Correct answer:** {question.correct_answer}) {correct_option_map.get(question.correct_answer, '')}

{('🧠 ' + question.explanation) if question.explanation else ''}
"""
        
        # Check if quiz is complete
        if quiz_session.current_question >= quiz_session.total_questions:
            # Quiz completed
            quiz_session.is_completed = True
            # Calculate score and grade
            percentage = int((quiz_session.correct_answers / quiz_session.total_questions) * 100)
            quiz_session.score_percentage = percentage
            quiz_session.grade = _compute_grade(percentage)
            quiz_session.completed_at = datetime.utcnow()
            if quiz_session.started_at:
                quiz_session.duration_seconds = int((quiz_session.completed_at - quiz_session.started_at).total_seconds())
            quiz_session.accuracy = percentage
            # Update user aggregate stats
            result = await db.execute(select(User).where(User.id == quiz_session.user_id))
            agg_user = result.scalar_one_or_none()
            if agg_user:
                agg_user.total_quizzes_taken = (agg_user.total_quizzes_taken or 0) + 1
                # rolling average
                if agg_user.average_accuracy is None:
                    agg_user.average_accuracy = percentage
                else:
                    prev_total = max((agg_user.total_quizzes_taken - 1), 0)
                    prev_avg = agg_user.average_accuracy or 0
                    new_avg = int(round(((prev_avg * prev_total) + percentage) / (prev_total + 1)))
                    agg_user.average_accuracy = new_avg
            await db.commit()
            
            # Show final results
            await show_quiz_results(update, context, quiz_session)
            # Invalidate analytics cache key(s)
            try:
                from services.cache import memory_cache
                memory_cache.delete("analytics_quizzes")
            except Exception:
                pass
            # Event log: quiz completed
            async for db in get_async_db():
                db.add(EventLog(user_id=quiz_session.user_id, event_type="quiz_complete", context={"topic_id": quiz_session.topic_id, "score": quiz_session.score_percentage}))
                await db.commit()
        else:
            # Show next question
            questions = context.user_data.get(f"quiz_{session_id}_questions", [])
            next_question_id = questions[quiz_session.current_question]
            
            result = await db.execute(select(Question).where(Question.id == next_question_id))
            next_question = result.scalar_one_or_none()
            
            if next_question:
                # Show feedback first, then next question
                keyboard = [[InlineKeyboardButton("➡️ Next Question", callback_data=f"next_question_{session_id}")]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(
                    feedback_text,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                # Disable previous inline keyboard by editing original message's reply markup if available
                try:
                    await query.edit_message_reply_markup(reply_markup=None)
                except Exception:
                    pass
                
                # Store next question for the next callback
                context.user_data[f"next_question_{session_id}"] = next_question
            else:
                await query.edit_message_text("Error loading next question.")

async def next_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the next question"""
    query = update.callback_query
    await query.answer()
    
    session_id = int(query.data.split("_")[2])
    
    # Get the stored next question
    next_question = context.user_data.get(f"next_question_{session_id}")
    if not next_question:
        await query.edit_message_text("Error: Next question not found.")
        return
    
    # Get current session info
    async for db in get_async_db():
        result = await db.execute(select(QuizSession).where(QuizSession.id == session_id))
        quiz_session = result.scalar_one_or_none()
        
        if quiz_session:
            await show_question(update, context, session_id, next_question, 
                              quiz_session.current_question + 1, quiz_session.total_questions)
        else:
            await query.edit_message_text("Quiz session not found.")

async def show_quiz_results(update: Update, context: ContextTypes.DEFAULT_TYPE, quiz_session: QuizSession):
    """Show quiz results"""
    query = update.callback_query
    
    percentage = (quiz_session.correct_answers / quiz_session.total_questions) * 100
    # Grade already stored, but compute if missing
    grade = quiz_session.grade or _compute_grade(int(percentage))
    
    # Determine performance message
    if percentage >= 90:
        performance = "🏆 Excellent!"
        emoji = "🎉"
    elif percentage >= 80:
        performance = "👏 Great job!"
        emoji = "😊"
    elif percentage >= 70:
        performance = "👍 Good work!"
        emoji = "🙂"
    elif percentage >= 60:
        performance = "📚 Keep studying!"
        emoji = "🤔"
    else:
        performance = "💪 Don't give up!"
        emoji = "😅"
    
    results_text = f"""
{emoji} **Quiz Completed!** {emoji}

Topic: {quiz_session.topic.name}
✅ Correct: {quiz_session.correct_answers} / {quiz_session.total_questions}
📊 Score: {percentage:.0f} %
🎓 Grade: {grade}

**What would you like to do next?**
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Take Another Quiz", callback_data="take_quiz")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")],
        [InlineKeyboardButton("🔁 Retry This Topic", callback_data=f"quiz_topic_{quiz_session.topic_id}")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        results_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def resume_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Resume an unfinished quiz session."""
    query = update.callback_query
    await query.answer()
    session_id = int(query.data.split("_")[2])
    # Load session and next question
    async for db in get_async_db():
        result = await db.execute(select(QuizSession).where(QuizSession.id == session_id))
        session = result.scalar_one_or_none()
        if not session or session.is_completed:
            await query.edit_message_text("Session not found or already completed.")
            return
        # Build question id list from stored order or from topic
        qids = []
        if getattr(session, 'question_ids', None):
            try:
                qids = [int(x) for x in (session.question_ids or '').split(',') if x]
            except Exception:
                qids = []
        if not qids:
            # Fallback: fetch all active for topic
            result = await db.execute(select(Question).where(Question.topic_id == session.topic_id, Question.is_active == True))
            qids = [q.id for q in result.scalars().all()]
        # Determine next question id
        idx = session.current_question or 0
        if idx >= len(qids):
            # Nothing left; mark complete
            session.is_completed = True
            await db.commit()
            await query.edit_message_text("This quiz session has no remaining questions.")
            return
        # Load that question and show
        result = await db.execute(select(Question).where(Question.id == qids[idx]))
        next_q = result.scalar_one_or_none()
        if not next_q:
            await query.edit_message_text("Next question not found.")
            return
        # Ensure context carries the ordered ids for next callbacks
        context.user_data[f"quiz_{session.id}_questions"] = qids
        await show_question(update, context, session.id, next_q, idx + 1, session.total_questions)

async def start_new_from_resume_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Discard unfinished session and start a new quiz flow (topic selection)."""
    query = update.callback_query
    await query.answer()
    session_id = int(query.data.split("_")[3])
    async for db in get_async_db():
        result = await db.execute(select(QuizSession).where(QuizSession.id == session_id))
        session = result.scalar_one_or_none()
        if session and not session.is_completed:
            session.is_completed = True
            await db.commit()
    # Redirect to the regular take_quiz topic selection
    await take_quiz_callback(update, context)

async def end_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End quiz early"""
    query = update.callback_query
    await query.answer()
    
    session_id = int(query.data.split("_")[2])
    
    # Get database session
    async for db in get_async_db():
        result = await db.execute(select(QuizSession).where(QuizSession.id == session_id))
        quiz_session = result.scalar_one_or_none()
        
        if quiz_session:
            quiz_session.is_completed = True
            # Persist partial score/grade if any questions answered
            if quiz_session.current_question > 0:
                percentage = int((quiz_session.correct_answers / quiz_session.current_question) * 100)
                quiz_session.score_percentage = percentage
                quiz_session.grade = _compute_grade(percentage)
            quiz_session.completed_at = datetime.utcnow()
            if quiz_session.started_at:
                quiz_session.duration_seconds = int((quiz_session.completed_at - quiz_session.started_at).total_seconds())
            quiz_session.accuracy = quiz_session.score_percentage
            # Update user aggregate stats only if at least one answered
            if quiz_session.current_question > 0:
                result = await db.execute(select(User).where(User.id == quiz_session.user_id))
                agg_user = result.scalar_one_or_none()
                if agg_user:
                    agg_user.total_quizzes_taken = (agg_user.total_quizzes_taken or 0) + 1
                    if agg_user.average_accuracy is None:
                        agg_user.average_accuracy = quiz_session.score_percentage
                    else:
                        prev_total = max((agg_user.total_quizzes_taken - 1), 0)
                        prev_avg = agg_user.average_accuracy or 0
                        new_avg = int(round(((prev_avg * prev_total) + quiz_session.score_percentage) / (prev_total + 1)))
                        agg_user.average_accuracy = new_avg
            await db.commit()
            
            # Show partial results
            if quiz_session.current_question > 0:
                percentage = (quiz_session.correct_answers / quiz_session.current_question) * 100
                
                results_text = f"""
📊 **Quiz Ended Early**

**Partial Results:**
✅ Correct: {quiz_session.correct_answers}/{quiz_session.current_question}
📊 Score: {percentage:.0f} %

**What would you like to do next?**
"""
            else:
                results_text = """
📊 **Quiz Ended**

No questions were answered.

**What would you like to do next?**
"""
            
            keyboard = [
                [InlineKeyboardButton("🔄 Take Another Quiz", callback_data="take_quiz")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                results_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )

async def view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user statistics"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    # Get database session
    async for db in get_async_db():
        # Get user
        result = await db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            await query.edit_message_text("User not found. Please use /start first.")
            return
        
        # Get quiz statistics
        result = await db.execute(select(QuizSession).where(
            QuizSession.user_id == db_user.id,
            QuizSession.is_completed == True
        ))
        completed_sessions = result.scalars().all()
        
        if not completed_sessions:
            stats_text = """
📊 **Your Statistics**

No quizzes completed yet.

Start taking quizzes to see your progress!
"""
        else:
            total_questions = sum(session.total_questions for session in completed_sessions)
            total_correct = sum(session.correct_answers for session in completed_sessions)
            average_score = (total_correct / total_questions) * 100 if total_questions > 0 else 0
            
            stats_text = f"""
📊 **Your Statistics**

**Overall Performance:**
🎯 Quizzes Completed: {len(completed_sessions)}
📝 Total Questions: {total_questions}
✅ Correct Answers: {total_correct}
📊 Average Score: {average_score:.1f}%

**Recent Activity:**
"""
            
            # Show last 5 quizzes
            recent_sessions = completed_sessions[-5:]
            for session in recent_sessions:
                session_score = (session.correct_answers / session.total_questions) * 100
                stats_text += f"• {session.topic.name}: {session_score:.0f} % (Grade: {session.grade or '-'})\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def quiz_history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last few quiz sessions for the user (/quiz_history)"""
    user = update.effective_user
    async for db in get_async_db():
        result = await db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            await update.message.reply_text("Please use /start first.")
            return
        result = await db.execute(select(QuizSession).where(QuizSession.user_id == db_user.id).order_by(QuizSession.started_at.desc()))
        sessions = result.scalars().all()
    if not sessions:
        await update.message.reply_text("No quiz history yet.")
        return
    lines = ["🗂️ Your recent quizzes:"]
    for s in sessions[:10]:
        pct = int((s.correct_answers / s.total_questions) * 100) if s.total_questions else 0
        lines.append(f"• {s.topic.name} — {pct}% (Grade: {s.grade or _compute_grade(pct)})")
    await update.message.reply_text("\n".join(lines))

async def retry_last_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Retry the last topic (/retry_last)"""
    user = update.effective_user
    async for db in get_async_db():
        result = await db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            await update.message.reply_text("Please use /start first.")
            return
        result = await db.execute(select(QuizSession).where(QuizSession.user_id == db_user.id).order_by(QuizSession.started_at.desc()))
        last_session = result.scalars().first()
    if not last_session:
        await update.message.reply_text("No previous quiz found to retry.")
        return
    # Trigger the quiz options for that topic
    # Simulate navigation by sending a button back to the same topic flow
    keyboard = [[InlineKeyboardButton("▶️ Start", callback_data=f"quiz_topic_{last_session.topic_id}")]]
    await update.message.reply_text("Retry last topic:", reply_markup=InlineKeyboardMarkup(keyboard))
