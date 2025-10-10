from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import SessionLocal
from database.models import User, University, Course, Unit, Topic, Paper, QuizSession
from sqlalchemy import select
import os
from services.cache import memory_cache
from services.user_service import UserService
from handlers.role_auth import RoleAuthHandler
import logging

logger = logging.getLogger(__name__)

# Initialize handlers
user_service = UserService()
role_auth_handler = RoleAuthHandler()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command with role-based authentication"""
    try:
        telegram_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name
        last_name = update.effective_user.last_name
        
        # Get or create user
        user = user_service.get_or_create_user(telegram_id, username, first_name, last_name)
        
        # Show role selection
        await role_auth_handler.show_role_selection(update, context)
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again or contact support.")

async def select_university_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle university selection"""
    query = update.callback_query
    await query.answer()
    
    cache_key = "curriculum_universities"
    universities = memory_cache.get(cache_key)
    if universities is None:
        # Get database session
        db = SessionLocal()
        try:
            # Get all active universities
            result = db.execute(select(University).where(University.is_active == True))
            universities = result.scalars().all()
        finally:
            db.close()
        ttl = int(os.getenv("CACHE_TTL_CURRICULUM", "43200"))
        memory_cache.set(cache_key, universities, ttl)
    
    if not universities:
        await query.edit_message_text(
            "No universities available at the moment. Please contact an administrator.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")
            ]])
        )
        return
    
    keyboard = []
    for university in universities:
        keyboard.append([InlineKeyboardButton(
            university.name,
            callback_data=f"university_{university.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🏫 **Select your University:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def university_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle university selection and show courses"""
    query = update.callback_query
    await query.answer()
    
    university_id = int(query.data.split("_")[1])
    
    # Get database session
    db = SessionLocal()
    try:
        # Get university
        result = db.execute(select(University).where(University.id == university_id))
        university = result.scalar_one_or_none()
        
        if not university:
            await query.edit_message_text("University not found.")
            return
        
        cache_key = f"curriculum_courses_{university_id}"
        courses = memory_cache.get(cache_key)
        if courses is None:
            # Get courses for this university
            result = db.execute(select(Course).where(
                Course.university_id == university_id,
                Course.is_active == True
            ))
            courses = result.scalars().all()
            ttl = int(os.getenv("CACHE_TTL_CURRICULUM", "43200"))
            memory_cache.set(cache_key, courses, ttl)
    finally:
        db.close()
    
    if not courses:
        await query.edit_message_text(
            f"No courses available for {university.name} at the moment.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Universities", callback_data="select_university")
            ]])
        )
        return
    
    keyboard = []
    for course in courses:
        keyboard.append([InlineKeyboardButton(
            course.name,
            callback_data=f"course_{course.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Universities", callback_data="select_university")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📚 **Select your Course at {university.name}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def course_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle course selection and show years/units"""
    query = update.callback_query
    await query.answer()
    
    course_id = int(query.data.split("_")[1])
    
    # Get database session
    db = SessionLocal()
    try:
        # Get course
        result = db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        
        if not course:
            await query.edit_message_text("Course not found.")
            return
        
        cache_key = f"curriculum_units_{course_id}"
        units = memory_cache.get(cache_key)
        if units is None:
            # Get units for this course
            result = db.execute(select(Unit).where(
                Unit.course_id == course_id,
                Unit.is_active == True
            ))
            units = result.scalars().all()
            ttl = int(os.getenv("CACHE_TTL_CURRICULUM", "43200"))
            memory_cache.set(cache_key, units, ttl)
    finally:
        db.close()
    
    if not units:
        await query.edit_message_text(
            f"No units available for {course.name} at the moment.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Courses", callback_data=f"university_{course.university_id}")
            ]])
        )
        return
    
    # Group units by year
    units_by_year = {}
    for unit in units:
        year = unit.year or "General"
        if year not in units_by_year:
            units_by_year[year] = []
        units_by_year[year].append(unit)
    
    keyboard = []
    for year, year_units in units_by_year.items():
        keyboard.append([InlineKeyboardButton(
            f"📅 Year {year}",
            callback_data=f"year_{course_id}_{year}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Courses", callback_data=f"university_{course.university_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📅 **Select Year for {course.name}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def year_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle year selection and show units"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    course_id = int(parts[1])
    year = parts[2]
    
    # Get database session
    db = SessionLocal()
    try:
        # Get course
        result = db.execute(select(Course).where(Course.id == course_id))
        course = result.scalar_one_or_none()
        
        if not course:
            await query.edit_message_text("Course not found.")
            return
        
        # Get units for this course and year
        result = db.execute(select(Unit).where(
            Unit.course_id == course_id,
            Unit.year == year,
            Unit.is_active == True
        ))
        units = result.scalars().all()
    finally:
        db.close()
    
    if not units:
        await query.edit_message_text(
            f"No units available for Year {year} of {course.name} at the moment.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Years", callback_data=f"course_{course_id}")
            ]])
        )
        return
    
    keyboard = []
    for unit in units:
        keyboard.append([InlineKeyboardButton(
            unit.name,
            callback_data=f"unit_{unit.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Years", callback_data=f"course_{course_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📖 **Select Unit for Year {year} of {course.name}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def unit_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unit selection and show topics"""
    query = update.callback_query
    await query.answer()
    
    unit_id = int(query.data.split("_")[1])
    
    # Get database session
    db = SessionLocal()
    try:
        # Get unit
        result = db.execute(select(Unit).where(Unit.id == unit_id))
        unit = result.scalar_one_or_none()
        
        if not unit:
            await query.edit_message_text("Unit not found.")
            return
        
        cache_key = f"curriculum_topics_{unit_id}"
        topics = memory_cache.get(cache_key)
        if topics is None:
            # Get topics for this unit
            result = db.execute(select(Topic).where(
                Topic.unit_id == unit_id,
                Topic.is_active == True
            ))
            topics = result.scalars().all()
            ttl = int(os.getenv("CACHE_TTL_CURRICULUM", "43200"))
            memory_cache.set(cache_key, topics, ttl)
    finally:
        db.close()
    
    if not topics:
        await query.edit_message_text(
            f"No topics available for {unit.name} at the moment.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back to Units", callback_data=f"year_{unit.course_id}_{unit.year}")
            ]])
        )
        return
    
    keyboard = []
    for topic in topics:
        keyboard.append([InlineKeyboardButton(
            topic.name,
            callback_data=f"topic_{topic.id}"
        )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Units", callback_data=f"year_{unit.course_id}_{unit.year}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📝 **Select Topic for {unit.name}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def topic_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle topic selection and show papers"""
    query = update.callback_query
    await query.answer()
    
    topic_id = int(query.data.split("_")[1])
    
    # Get database session
    db = SessionLocal()
    try:
        # Get topic
        result = db.execute(select(Topic).where(Topic.id == topic_id))
        topic = result.scalar_one_or_none()
        
        if not topic:
            await query.edit_message_text("Topic not found.")
            return
        
        # Get papers for this topic
        result = db.execute(select(Paper).where(
            Paper.topic_id == topic_id,
            Paper.is_active == True
        ))
        papers = result.scalars().all()
    finally:
        db.close()
    
    keyboard = []
    
    # Add papers if available
    if papers:
        for paper in papers:
            paper_name = f"{paper.name} ({paper.year})" if paper.year else paper.name
            keyboard.append([InlineKeyboardButton(
                f"📄 {paper_name}",
                callback_data=f"paper_{paper.id}"
            )])
    
    # Add option to take quiz on all topics
    keyboard.append([InlineKeyboardButton(
        "🎯 Take Quiz on All Topics",
        callback_data=f"quiz_all_{topic_id}"
    )])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Topics", callback_data=f"unit_{topic.unit_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    paper_text = f"📄 **Available Papers for {topic.name}:**" if papers else f"📝 **No specific papers for {topic.name}**"
    
    await query.edit_message_text(
        paper_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    
    welcome_message = f"""
🏥 **BotCamp Medical** 🏥

Hello {user.first_name}! 👋

**What would you like to do?**

Choose from the options below:
"""
    
    # Check if user is admin
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        is_admin = db_user and db_user.role in ['admin', 'super_admin'] if db_user else False
    finally:
        db.close()
    
    keyboard = [
        [InlineKeyboardButton("🎓 Select University & Course", callback_data="select_university")],
        [InlineKeyboardButton("📚 Take a Quiz", callback_data="take_quiz")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")],
    ]
    
    # Add admin-only options
    if is_admin:
        keyboard.append([InlineKeyboardButton("📤 Upload Questions", callback_data="upload_questions")])
    
    keyboard.append([InlineKeyboardButton("ℹ️ Help", callback_data="help")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show help information"""
    query = update.callback_query
    await query.answer()
    
    help_text = """
ℹ️ **Help & Instructions**

**How to use BotCamp Medical:**

1. **🎓 Select University & Course**
   - Choose your university
   - Select your medical course
   - Pick your year and unit
   - Choose a topic

2. **📚 Take a Quiz**
   - Start a quiz on any topic
   - Answer multiple choice questions
   - Get instant feedback
   - Track your progress

3. **📊 View Statistics**
   - See your quiz performance
   - Track improvement over time
   - Identify weak areas

**Commands:**
- `/start` - Start the bot
- `/help` - Show this help message
- `/stats` - View your statistics

**Need more help?**
Contact the administrator or use the feedback feature.
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def weak_topics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show student's weakest topics and offer remedial quiz buttons."""
    user = update.effective_user
    # Load user and completed sessions
    db = SessionLocal()
    try:
        result = db.execute(select(User).where(User.telegram_id == user.id))
        db_user = result.scalar_one_or_none()
        if not db_user:
            await update.message.reply_text("Please use /start first.")
            return
        result = db.execute(select(QuizSession).where(QuizSession.user_id == db_user.id, QuizSession.is_completed == True))
        sessions = result.scalars().all()
    finally:
        db.close()
    if not sessions:
        await update.message.reply_text("No quiz history yet. Take some quizzes first.")
        return
    # Aggregate by topic
    from collections import defaultdict
    by_topic = defaultdict(list)
    for s in sessions:
        if s.topic_id is not None and s.score_percentage is not None:
            by_topic[s.topic_id].append(int(s.score_percentage))
    if not by_topic:
        await update.message.reply_text("Not enough data to compute weak topics yet.")
        return
    averages = []
    for tid, scores in by_topic.items():
        if scores:
            averages.append((tid, sum(scores)/len(scores)))
    averages.sort(key=lambda x: x[1])
    weakest = averages[:3]
    # Build message and buttons
    lines = ["🧠 Weak Topics (based on recent completed quizzes):"]
    keyboard = []
    db = SessionLocal()
    try:
        for tid, avg in weakest:
            result = db.execute(select(Topic).where(Topic.id == tid))
            t = result.scalar_one_or_none()
            name = t.name if t else f"Topic {tid}"
            lines.append(f"• {name}: {avg:.0f}% avg")
            keyboard.append([InlineKeyboardButton(f"Remedial: {name}", callback_data=f"quiz_topic_{tid}")])
    finally:
        db.close()
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)
