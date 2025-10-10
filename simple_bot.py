#!/usr/bin/env python3
"""
Simple BotCamp Medical Bot - Working version
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from bot.commands.admin import start as cmd_start, grant_admin, revoke_admin, list_users
from bot.handlers.shared import start as shared_start
from bot.handlers.student import (
    take_quiz_entry, select_course, select_year, select_unit, select_topic, topic_ready
)
from bot.handlers.admin import upload_entry, review_entry, stats_entry
from bot.handlers.super_admin import setrole, roles

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token
BOT_TOKEN = "8426722737:AAFhuYdUhqn-D3CJdkEMD8mA16JoIk8T9JI"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle the /start command"""
    user = update.effective_user
    
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
    
    keyboard = [
        [InlineKeyboardButton("🏫 University of Nairobi", callback_data="university_1")],
        [InlineKeyboardButton("🏫 Kenyatta University", callback_data="university_2")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    
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
    
    university_id = query.data.split("_")[1]
    university_name = "University of Nairobi" if university_id == "1" else "Kenyatta University"
    
    keyboard = [
        [InlineKeyboardButton("📚 MBChB (Bachelor of Medicine)", callback_data=f"course_{university_id}_1")],
        [InlineKeyboardButton("🔙 Back to Universities", callback_data="select_university")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📚 **Select your Course at {university_name}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def course_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle course selection and show years"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    university_id = parts[1]
    course_id = parts[2]
    
    keyboard = [
        [InlineKeyboardButton("📅 Year 1", callback_data=f"year_{university_id}_{course_id}_1")],
        [InlineKeyboardButton("📅 Year 2", callback_data=f"year_{university_id}_{course_id}_2")],
        [InlineKeyboardButton("📅 Year 3", callback_data=f"year_{university_id}_{course_id}_3")],
        [InlineKeyboardButton("🔙 Back to Courses", callback_data=f"university_{university_id}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📅 **Select Year for MBChB:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def year_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle year selection and show units"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    university_id = parts[1]
    course_id = parts[2]
    year = parts[3]
    
    if year == "1":
        units = [
            ("🧬 Anatomy", "unit_anatomy"),
            ("🔬 Physiology", "unit_physiology"),
            ("🧪 Biochemistry", "unit_biochemistry")
        ]
    elif year == "2":
        units = [
            ("🦠 Pathology", "unit_pathology"),
            ("💊 Pharmacology", "unit_pharmacology"),
            ("🩺 Clinical Skills", "unit_clinical")
        ]
    else:
        units = [
            ("🏥 Internal Medicine", "unit_internal"),
            ("👶 Pediatrics", "unit_pediatrics"),
            ("👩‍⚕️ Obstetrics & Gynecology", "unit_obgyn")
        ]
    
    keyboard = []
    for unit_name, unit_id in units:
        keyboard.append([InlineKeyboardButton(unit_name, callback_data=f"{unit_id}_{year}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Years", callback_data=f"course_{university_id}_{course_id}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📖 **Select Unit for Year {year}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def unit_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle unit selection and show topics"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    unit_name = parts[0]
    year = parts[1]
    
    # Sample topics for different units
    topics = {
        "unit_anatomy": [
            ("🦴 General Anatomy", "topic_general_anatomy"),
            ("❤️ Cardiovascular System", "topic_cardiovascular"),
            ("🧠 Nervous System", "topic_nervous")
        ],
        "unit_physiology": [
            ("💓 Cardiovascular Physiology", "topic_cardio_physio"),
            ("🫁 Respiratory Physiology", "topic_respiratory"),
            ("🧠 Neurophysiology", "topic_neuro_physio")
        ],
        "unit_pathology": [
            ("🔬 General Pathology", "topic_general_pathology"),
            ("🦠 Infectious Diseases", "topic_infectious"),
            ("🎯 Oncology", "topic_oncology")
        ]
    }
    
    unit_topics = topics.get(unit_name, [
        ("📝 General Topics", "topic_general"),
        ("📚 Study Materials", "topic_materials")
    ])
    
    keyboard = []
    for topic_name, topic_id in unit_topics:
        keyboard.append([InlineKeyboardButton(topic_name, callback_data=f"{topic_id}_{year}")])
    
    keyboard.append([InlineKeyboardButton("🔙 Back to Units", callback_data=f"year_1_1_{year}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    unit_display_name = unit_name.replace("unit_", "").replace("_", " ").title()
    await query.edit_message_text(
        f"📝 **Select Topic for {unit_display_name}:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def topic_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle topic selection and show quiz options"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    topic_name = "_".join(parts[:-1])
    year = parts[-1]
    
    keyboard = [
        [InlineKeyboardButton("🎯 Quick Quiz (5 questions)", callback_data=f"quiz_{topic_name}_5")],
        [InlineKeyboardButton("📝 Standard Quiz (10 questions)", callback_data=f"quiz_{topic_name}_10")],
        [InlineKeyboardButton("🏆 Full Quiz (20 questions)", callback_data=f"quiz_{topic_name}_20")],
        [InlineKeyboardButton("🔙 Back to Topics", callback_data=f"unit_anatomy_{year}")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    topic_display_name = topic_name.replace("topic_", "").replace("_", " ").title()
    await query.edit_message_text(
        f"📚 **Quiz Options for {topic_display_name}:**\n\nChoose the number of questions for your quiz:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def quiz_selected_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle quiz selection"""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split("_")
    topic_name = "_".join(parts[1:-1])
    num_questions = parts[-1]
    
    # Sample quiz question
    question_text = """
📝 **Question 1 of 5**

Which of the following is the largest bone in the human body?

**Options:**
A) Femur
B) Tibia
C) Humerus
D) Radius
"""
    
    keyboard = [
        [InlineKeyboardButton("A", callback_data="answer_A")],
        [InlineKeyboardButton("B", callback_data="answer_B")],
        [InlineKeyboardButton("C", callback_data="answer_C")],
        [InlineKeyboardButton("D", callback_data="answer_D")],
        [InlineKeyboardButton("❌ End Quiz", callback_data="end_quiz")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        question_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def answer_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle answer selection"""
    query = update.callback_query
    await query.answer()
    
    user_answer = query.data.split("_")[1]
    correct_answer = "A"  # Femur is correct
    
    if user_answer == correct_answer:
        feedback = "✅ **Correct!**\n\nThe femur (thigh bone) is indeed the longest and strongest bone in the human body."
    else:
        feedback = f"❌ **Incorrect!**\n\nYour answer: {user_answer}\nCorrect answer: {correct_answer}\n\nThe femur (thigh bone) is the longest and strongest bone in the human body."
    
    keyboard = [
        [InlineKeyboardButton("➡️ Next Question", callback_data="next_question")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        feedback,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def next_question_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show next question"""
    query = update.callback_query
    await query.answer()
    
    question_text = """
📝 **Question 2 of 5**

The anatomical position is characterized by:

**Options:**
A) Palms facing backward
B) Palms facing forward
C) Arms at sides
D) Both B and C
"""
    
    keyboard = [
        [InlineKeyboardButton("A", callback_data="answer2_A")],
        [InlineKeyboardButton("B", callback_data="answer2_B")],
        [InlineKeyboardButton("C", callback_data="answer2_C")],
        [InlineKeyboardButton("D", callback_data="answer2_D")],
        [InlineKeyboardButton("❌ End Quiz", callback_data="end_quiz")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        question_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def answer2_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle second answer"""
    query = update.callback_query
    await query.answer()
    
    user_answer = query.data.split("_")[1]
    correct_answer = "D"  # Both B and C is correct
    
    if user_answer == correct_answer:
        feedback = "✅ **Correct!**\n\nIn anatomical position, the body is upright with palms facing forward and arms at the sides."
    else:
        feedback = f"❌ **Incorrect!**\n\nYour answer: {user_answer}\nCorrect answer: {correct_answer}\n\nIn anatomical position, the body is upright with palms facing forward and arms at the sides."
    
    keyboard = [
        [InlineKeyboardButton("📊 View Results", callback_data="quiz_results")],
        [InlineKeyboardButton("🔄 Take Another Quiz", callback_data="take_quiz")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        feedback,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def quiz_results_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quiz results"""
    query = update.callback_query
    await query.answer()
    
    results_text = """
🎉 **Quiz Completed!**

**Results:**
✅ Correct: 2/2
📊 Score: 100%
🏆 Performance: Excellent!

**What would you like to do next?**
"""
    
    keyboard = [
        [InlineKeyboardButton("🔄 Take Another Quiz", callback_data="take_quiz")],
        [InlineKeyboardButton("📊 View Statistics", callback_data="view_stats")],
        [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        results_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def take_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle take quiz callback"""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("🧬 General Anatomy", callback_data="quiz_topic_general_anatomy_5")],
        [InlineKeyboardButton("❤️ Cardiovascular System", callback_data="quiz_topic_cardiovascular_5")],
        [InlineKeyboardButton("🧠 Nervous System", callback_data="quiz_topic_nervous_5")],
        [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "📚 **Select a Topic for Quiz:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def view_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user statistics"""
    query = update.callback_query
    await query.answer()
    
    stats_text = """
📊 **Your Statistics**

**Overall Performance:**
🎯 Quizzes Completed: 1
📝 Total Questions: 2
✅ Correct Answers: 2
📊 Average Score: 100%

**Recent Activity:**
• General Anatomy: 100%

**Keep up the great work!** 🎉
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        stats_text,
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

async def end_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """End quiz early"""
    query = update.callback_query
    await query.answer()
    
    results_text = """
📊 **Quiz Ended**

**Partial Results:**
✅ Correct: 1/1
📊 Score: 100%

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

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again or contact support."
        )

def main():
    """Main function to run the bot"""
    logger.info("Starting BotCamp Medical Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    # Public start (kept for demo UI)
    application.add_handler(CommandHandler("start", shared_start))
    # Role management commands (super_admin only)
    application.add_handler(CommandHandler("grant_admin", grant_admin))
    application.add_handler(CommandHandler("revoke_admin", revoke_admin))
    application.add_handler(CommandHandler("list_users", list_users))
    application.add_handler(CommandHandler("setrole", setrole))
    application.add_handler(CommandHandler("roles", roles))

    # Student navigation callbacks
    application.add_handler(CallbackQueryHandler(take_quiz_entry, pattern=r"^stu_take_quiz$"))
    application.add_handler(CallbackQueryHandler(select_course, pattern=r"^stu_u_\d+$"))
    application.add_handler(CallbackQueryHandler(select_year, pattern=r"^stu_c_\d+$"))
    application.add_handler(CallbackQueryHandler(select_unit, pattern=r"^stu_y_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(select_topic, pattern=r"^stu_unit_\d+$"))
    application.add_handler(CallbackQueryHandler(topic_ready, pattern=r"^stu_topic_\d+$"))

    # Admin callbacks placeholders
    application.add_handler(CallbackQueryHandler(upload_entry, pattern=r"^adm_upload$"))
    application.add_handler(CallbackQueryHandler(review_entry, pattern=r"^adm_review$"))
    application.add_handler(CallbackQueryHandler(stats_entry, pattern=r"^adm_stats$"))
    application.add_handler(CallbackQueryHandler(select_university_callback, pattern=r"^select_university$"))
    application.add_handler(CallbackQueryHandler(university_selected_callback, pattern=r"^university_\d+$"))
    application.add_handler(CallbackQueryHandler(course_selected_callback, pattern=r"^course_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(year_selected_callback, pattern=r"^year_\d+_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(unit_selected_callback, pattern=r"^unit_\w+_\d+$"))
    application.add_handler(CallbackQueryHandler(topic_selected_callback, pattern=r"^topic_\w+_\d+$"))
    application.add_handler(CallbackQueryHandler(quiz_selected_callback, pattern=r"^quiz_\w+_\d+$"))
    application.add_handler(CallbackQueryHandler(answer_callback, pattern=r"^answer_A$|^answer_B$|^answer_C$|^answer_D$"))
    application.add_handler(CallbackQueryHandler(answer2_callback, pattern=r"^answer2_A$|^answer2_B$|^answer2_C$|^answer2_D$"))
    application.add_handler(CallbackQueryHandler(next_question_callback, pattern=r"^next_question$"))
    application.add_handler(CallbackQueryHandler(quiz_results_callback, pattern=r"^quiz_results$"))
    application.add_handler(CallbackQueryHandler(take_quiz_callback, pattern=r"^take_quiz$"))
    application.add_handler(CallbackQueryHandler(view_stats_callback, pattern=r"^view_stats$"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^main_menu$"))
    application.add_handler(CallbackQueryHandler(end_quiz_callback, pattern=r"^end_quiz$"))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot is starting...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
