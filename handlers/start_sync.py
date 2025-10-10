from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db import get_db
from database.models import User, University, Course, Unit, Topic, Paper
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

def get_db_session():
    """Get database session"""
    db = next(get_db())
    return db

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Get database session
    db = get_db_session()
    try:
        # Check if user exists
        existing_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not existing_user:
            # Create new user
            new_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            db.add(new_user)
            db.commit()
            logger.info(f"Created new user: {user.id}")
        else:
            logger.info(f"Existing user: {user.id}")
    finally:
        db.close()
    
    welcome_message = f"""
🏥 **Welcome to BotCamp Medical!** 🏥

Hello {user.first_name}! 👋

I'm your medical quiz companion. I'll help you practice and improve your medical knowledge through interactive quizzes.

**What would you like to do?**

Choose from the options below to get started:
"""
    
    keyboard = [
        [InlineKeyboardButton("🎓 Select University & Course", callback_data="select_university")],
        [InlineKeyboardButton("📚 Take a Quiz", callback_data="take_quiz")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def select_university_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle university selection"""
    query = update.callback_query
    await query.answer()
    
    # Get database session
    db = get_db_session()
    try:
        # Get all active universities
        universities = db.query(University).filter(University.is_active == True).all()
    finally:
        db.close()
    
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
    db = get_db_session()
    try:
        # Get university
        university = db.query(University).filter(University.id == university_id).first()
        
        if not university:
            await query.edit_message_text("University not found.")
            return
        
        # Get courses for this university
        courses = db.query(Course).filter(
            Course.university_id == university_id,
            Course.is_active == True
        ).all()
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
    db = get_db_session()
    try:
        # Get course
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not course:
            await query.edit_message_text("Course not found.")
            return
        
        # Get units for this course
        units = db.query(Unit).filter(
            Unit.course_id == course_id,
            Unit.is_active == True
        ).all()
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
    db = get_db_session()
    try:
        # Get course
        course = db.query(Course).filter(Course.id == course_id).first()
        
        if not course:
            await query.edit_message_text("Course not found.")
            return
        
        # Get units for this course and year
        units = db.query(Unit).filter(
            Unit.course_id == course_id,
            Unit.year == year,
            Unit.is_active == True
        ).all()
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
    db = get_db_session()
    try:
        # Get unit
        unit = db.query(Unit).filter(Unit.id == unit_id).first()
        
        if not unit:
            await query.edit_message_text("Unit not found.")
            return
        
        # Get topics for this unit
        topics = db.query(Topic).filter(
            Topic.unit_id == unit_id,
            Topic.is_active == True
        ).all()
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
    db = get_db_session()
    try:
        # Get topic
        topic = db.query(Topic).filter(Topic.id == topic_id).first()
        
        if not topic:
            await query.edit_message_text("Topic not found.")
            return
        
        # Get papers for this topic
        papers = db.query(Paper).filter(
            Paper.topic_id == topic_id,
            Paper.is_active == True
        ).all()
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
    
    keyboard = [
        [InlineKeyboardButton("🎓 Select University & Course", callback_data="select_university")],
        [InlineKeyboardButton("📚 Take a Quiz", callback_data="take_quiz")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    
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
