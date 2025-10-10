import asyncio
import logging
import os
from dotenv import load_dotenv
from pathlib import Path
from logging.handlers import RotatingFileHandler
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Import handlers
from handlers.start import (
    start_command, select_university_callback, university_selected_callback,
    course_selected_callback, year_selected_callback, unit_selected_callback,
    topic_selected_callback, main_menu_callback, help_callback, weak_topics_command
)
from handlers.role_auth import RoleAuthHandler
from handlers.admin_upload import AdminUploadHandler
from handlers.super_admin import SuperAdminHandler
from services.security_service import SecurityService
from handlers.quiz import (
        take_quiz_callback, quiz_topic_selected_callback, start_quiz_callback,
        answer_question_callback, next_question_callback, show_quiz_results,
        end_quiz_callback, view_stats_callback, quiz_history_command, retry_last_command,
        resume_quiz_callback, start_new_from_resume_callback
    )
from bot.handlers.student import (
    take_quiz_entry, select_course, select_year, select_unit, select_topic, topic_ready
)
from bot.handlers.student_quiz import (
    start_quiz_for_topic, handle_quiz_answer, quit_quiz, retake_quiz,
    show_quiz_history, retry_last_quiz, quiz_history_command as new_quiz_history_command,
    retry_last_command as new_retry_last_command, quit_quiz_command
)
from bot.handlers.upload_handler import UploadHandler
from handlers.admin import (
    admin_command, admin_universities_callback, admin_courses_callback,
    admin_questions_callback, admin_user_stats_callback, admin_system_stats_callback,
    admin_panel_callback, admin_upload_questions_entry, admin_upload_text_prompt,
    admin_upload_pdf_prompt, admin_upload_image_prompt, upload_message_handler,
    admin_upload_done, admin_review_confirm, admin_review_reject, admin_review_edit,
    admin_edit_message_handler, moderation_queue_command, moderation_review_callback,
    moderation_approve_callback, moderation_reject_callback, analytics_quizzes_command,
    my_contributions_command, admin_dashboard_command, errors_command, activity_summary_command,
    my_stats_command, system_status_command, my_uploads_command, topic_stats_command, review_next_command, request_admin_command, set_admin_code_command, redeem_admin_code_command, reprocess_upload_command
)
from handlers.ui_flow_handlers import UIFlowHandlers
from handlers.specification_handlers import SpecificationHandlers

# Import database setup
from database.db import create_tables_sync
from services.telemetry import collector

# Load environment variables from project root explicitly
_dotenv_path = Path(__file__).parent / ".env"
# Use utf-8-sig to handle potential BOM
load_dotenv(dotenv_path=_dotenv_path, override=True, encoding="utf-8-sig")

# Debug/logging to verify env load in various environments
try:
    logging.getLogger(__name__).info(
        "dotenv_path=%s exists=%s cwd=%s",
        str(_dotenv_path), _dotenv_path.exists(), os.getcwd()
    )
except Exception:
    pass

# Configure logging: console + rotating file
logger = logging.getLogger()
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

console_handler = logging.StreamHandler()
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

try:
    file_handler = RotatingFileHandler('logs/bot.log', maxBytes=5_000_000, backupCount=3)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
except Exception:
    # If logs dir missing or unwritable, continue with console logging only
    pass

# Bot token from environment (with fallback manual parse if needed)
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN and _dotenv_path.exists():
    try:
        for _line in _dotenv_path.read_text(encoding="utf-8-sig", errors="ignore").splitlines():
            _line = _line.lstrip("\ufeff")
            if _line.strip().startswith("BOT_TOKEN="):
                BOT_TOKEN = _line.split("=", 1)[1].strip().strip('"').strip("'")
                if BOT_TOKEN:
                    os.environ["BOT_TOKEN"] = BOT_TOKEN
                break
    except Exception:
        pass

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                f"❌ An error occurred. Please try again.\n{context.error}"
            )
        except Exception:
            pass

def setup_handlers(application: Application):
    """Setup all bot handlers"""
    
    # Initialize handlers
    role_auth_handler = RoleAuthHandler()
    admin_upload_handler = AdminUploadHandler()
    super_admin_handler = SuperAdminHandler()
    security_service = SecurityService()
    upload_handler = UploadHandler()
    ui_flow_handler = UIFlowHandlers()
    spec_handler = SpecificationHandlers()
    
    # Command handlers
    application.add_handler(CommandHandler("start", ui_flow_handler.start_command_handler))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("quiz_history", new_quiz_history_command))
    application.add_handler(CommandHandler("retry_last", new_retry_last_command))
    application.add_handler(CommandHandler("quit_quiz", quit_quiz_command))
    application.add_handler(CommandHandler("upload_question", upload_handler.start_upload_process))
    application.add_handler(CommandHandler("moderation_queue", moderation_queue_command))
    application.add_handler(CommandHandler("analytics_quizzes", analytics_quizzes_command))
    application.add_handler(CommandHandler("my_contributions", my_contributions_command))
    application.add_handler(CommandHandler("admin_dashboard", admin_dashboard_command))
    # Part 7: dashboard + exports
    from handlers.admin import dashboard_command, export_questions_command, export_quiz_results_command, alerts_command, backup_now_command
    application.add_handler(CommandHandler("dashboard", dashboard_command))
    application.add_handler(CommandHandler("export_questions", export_questions_command))
    application.add_handler(CommandHandler("export_quiz_results", export_quiz_results_command))
    application.add_handler(CommandHandler("alerts", alerts_command))
    application.add_handler(CommandHandler("backup_now", backup_now_command))
    application.add_handler(CommandHandler("system_status", system_status_command))
    application.add_handler(CommandHandler("errors", errors_command))
    application.add_handler(CommandHandler("activity_summary", activity_summary_command))
    application.add_handler(CommandHandler("my_stats", my_stats_command))
    # Part 7 admin/student extras
    application.add_handler(CommandHandler("my_uploads", my_uploads_command))
    application.add_handler(CommandHandler("topic_stats", topic_stats_command))
    application.add_handler(CommandHandler("review_next", review_next_command))
    application.add_handler(CommandHandler("weak_topics", weak_topics_command))
    # Admin access request
    application.add_handler(CommandHandler("request_admin", request_admin_command))
    application.add_handler(CommandHandler("set_admin_code", set_admin_code_command))
    application.add_handler(CommandHandler("redeem_admin_code", redeem_admin_code_command))
    application.add_handler(CommandHandler("reprocess_upload", reprocess_upload_command))
    
    # Master Specification Commands (Sections 11-15)
    application.add_handler(CommandHandler("exportdata", spec_handler.exportdata_command))
    application.add_handler(CommandHandler("adduniversity", spec_handler.adduniversity_command))
    application.add_handler(CommandHandler("addcourse", spec_handler.addcourse_command))
    application.add_handler(CommandHandler("addunit", spec_handler.addunit_command))
    application.add_handler(CommandHandler("addtopic", spec_handler.addtopic_command))
    application.add_handler(CommandHandler("healthcheck", spec_handler.healthcheck_command))
    application.add_handler(CommandHandler("backup", spec_handler.backup_command))
    application.add_handler(CommandHandler("restore", spec_handler.restore_command))
    application.add_handler(CommandHandler("listuniversities", spec_handler.listuniversities_command))
    application.add_handler(CommandHandler("setadminscope", spec_handler.setadminscope_command))
    
    # Super Admin Commands
    application.add_handler(CommandHandler("addadmin", super_admin_handler.add_admin_command))
    application.add_handler(CommandHandler("removeadmin", super_admin_handler.remove_admin_command))
    application.add_handler(CommandHandler("listadmins", super_admin_handler.list_admins_command))
    application.add_handler(CommandHandler("broadcast", super_admin_handler.broadcast_command))
    application.add_handler(CommandHandler("systemstatus", super_admin_handler.system_status_command))
    # Open Super Admin panel
    application.add_handler(CommandHandler("superadmin", super_admin_handler.show_super_admin_menu))
    application.add_handler(CommandHandler("approve_admin", super_admin_handler.approve_admin_command))
    application.add_handler(CommandHandler("reset_admin_code", super_admin_handler.reset_admin_code_command))
    
    # Role authentication handlers
    application.add_handler(CallbackQueryHandler(role_auth_handler.handle_role_callback, pattern="^role_"))
    application.add_handler(CallbackQueryHandler(role_auth_handler.handle_navigation_callback, pattern=r"^(university_|course_|year_|unit_|topic_|quiz_)"))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, role_auth_handler.handle_auth_code))
    
    # Callback query handlers for start flow
    application.add_handler(CallbackQueryHandler(select_university_callback, pattern="^select_university$"))
    application.add_handler(CallbackQueryHandler(university_selected_callback, pattern=r"^university_\d+$"))
    application.add_handler(CallbackQueryHandler(course_selected_callback, pattern=r"^course_\d+$"))
    application.add_handler(CallbackQueryHandler(year_selected_callback, pattern=r"^year_\d+_.+$"))
    application.add_handler(CallbackQueryHandler(unit_selected_callback, pattern=r"^unit_\d+$"))
    application.add_handler(CallbackQueryHandler(topic_selected_callback, pattern=r"^topic_\d+$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern="^help$"))
    
    # Student navigation handlers (from bot/handlers/student.py)
    application.add_handler(CallbackQueryHandler(take_quiz_entry, pattern="^take_quiz$"))
    application.add_handler(CallbackQueryHandler(select_course, pattern=r"^stu_u_\d+$"))
    application.add_handler(CallbackQueryHandler(select_year, pattern=r"^stu_c_\d+$"))
    application.add_handler(CallbackQueryHandler(select_unit, pattern=r"^stu_y_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(select_topic, pattern=r"^stu_unit_\d+$"))
    application.add_handler(CallbackQueryHandler(topic_ready, pattern=r"^stu_topic_\d+$"))
    
    # Callback query handlers for quiz flow
    application.add_handler(CallbackQueryHandler(take_quiz_callback, pattern="^take_quiz$"))
    application.add_handler(CallbackQueryHandler(quiz_topic_selected_callback, pattern=r"^quiz_topic_\d+$"))
    application.add_handler(CallbackQueryHandler(start_quiz_callback, pattern=r"^start_quiz_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(answer_question_callback, pattern=r"^answer_\d+_\d+_[ABCD]$"))
    application.add_handler(CallbackQueryHandler(next_question_callback, pattern=r"^next_question_\d+$"))
    application.add_handler(CallbackQueryHandler(end_quiz_callback, pattern=r"^end_quiz_\d+$"))
    application.add_handler(CallbackQueryHandler(resume_quiz_callback, pattern=r"^resume_quiz_\d+$"))
    application.add_handler(CallbackQueryHandler(start_new_from_resume_callback, pattern=r"^start_new_quiz_\d+$"))
    application.add_handler(CallbackQueryHandler(view_stats_callback, pattern="^view_stats$"))
    
    # New quiz engine handlers
    application.add_handler(CallbackQueryHandler(handle_quiz_answer, pattern=r"^quiz_answer_\d+_\d+$"))
    application.add_handler(CallbackQueryHandler(quit_quiz, pattern=r"^quit_quiz_\d+$"))
    application.add_handler(CallbackQueryHandler(retake_quiz, pattern=r"^retake_quiz_\d+$"))
    application.add_handler(CallbackQueryHandler(show_quiz_history, pattern="^quiz_history$"))
    application.add_handler(CallbackQueryHandler(retry_last_quiz, pattern="^retry_last$"))
    
    # Upload handlers
    application.add_handler(CallbackQueryHandler(upload_handler.start_upload_process, pattern="^upload_questions$"))
    application.add_handler(CallbackQueryHandler(upload_handler.handle_upload_type_selection, pattern=r"^upload_(text|pdf|image)$"))
    application.add_handler(CallbackQueryHandler(upload_handler.start_question_review, pattern="^review_questions$"))
    application.add_handler(CallbackQueryHandler(upload_handler.handle_question_review_action, pattern=r"^(approve|edit|reject|skip)_question$"))
    application.add_handler(CallbackQueryHandler(upload_handler.final_upload_questions, pattern="^final_upload$"))
    
    # Callback query handlers for admin flow
    application.add_handler(CallbackQueryHandler(admin_universities_callback, pattern="^admin_universities$"))
    application.add_handler(CallbackQueryHandler(admin_courses_callback, pattern="^admin_courses$"))
    application.add_handler(CallbackQueryHandler(admin_questions_callback, pattern="^admin_questions$"))
    application.add_handler(CallbackQueryHandler(admin_user_stats_callback, pattern="^admin_user_stats$"))
    application.add_handler(CallbackQueryHandler(admin_system_stats_callback, pattern="^admin_system_stats$"))
    application.add_handler(CallbackQueryHandler(admin_panel_callback, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(admin_upload_questions_entry, pattern="^admin_upload_questions$"))
    application.add_handler(CallbackQueryHandler(admin_upload_text_prompt, pattern="^admin_upload_text$"))
    application.add_handler(CallbackQueryHandler(admin_upload_pdf_prompt, pattern="^admin_upload_pdf$"))
    application.add_handler(CallbackQueryHandler(admin_upload_image_prompt, pattern="^admin_upload_image$"))
    application.add_handler(CallbackQueryHandler(admin_review_confirm, pattern="^admin_review_confirm$"))
    application.add_handler(CallbackQueryHandler(admin_review_reject, pattern="^admin_review_reject$"))
    application.add_handler(CallbackQueryHandler(admin_review_edit, pattern="^admin_review_edit$"))
    application.add_handler(CallbackQueryHandler(moderation_review_callback, pattern=r"^mod_review_\d+$"))
    application.add_handler(CallbackQueryHandler(moderation_approve_callback, pattern=r"^mod_approve_\d+$"))
    application.add_handler(CallbackQueryHandler(moderation_reject_callback, pattern=r"^mod_reject_\d+$"))
    
    # Admin upload handlers
    application.add_handler(CallbackQueryHandler(admin_upload_handler.handle_upload_type_selection, pattern="^upload_"))
    application.add_handler(CallbackQueryHandler(admin_upload_handler.handle_question_review_action, pattern="^(confirm_|edit_|skip_|cancel_|submit_)"))
    application.add_handler(MessageHandler((filters.Document.ALL | filters.PHOTO) & ~filters.COMMAND, admin_upload_handler.handle_file_upload))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_upload_handler.handle_text_upload))
    
    # Super admin callback handlers
    application.add_handler(CallbackQueryHandler(super_admin_handler.handle_broadcast_confirmation, pattern="^(confirm_|cancel_)broadcast"))
    
    # Analytics and moderation callback handlers
    application.add_handler(CallbackQueryHandler(analytics_quizzes_command, pattern="^analytics_quizzes$"))
    application.add_handler(CallbackQueryHandler(my_contributions_command, pattern="^my_contributions$"))
    application.add_handler(CallbackQueryHandler(admin_dashboard_command, pattern="^admin_dashboard$"))
    application.add_handler(CallbackQueryHandler(my_stats_command, pattern="^my_stats$"))
    application.add_handler(CallbackQueryHandler(moderation_queue_command, pattern="^moderation_queue$"))
    
    # UI Flow callback handlers (Master Specification Section 11)
    application.add_handler(CallbackQueryHandler(ui_flow_handler.role_selection_handler, pattern="^role_(student|admin|super_admin)$"))
    application.add_handler(CallbackQueryHandler(ui_flow_handler.university_selection_handler, pattern=r"^university_\d+$"))
    application.add_handler(CallbackQueryHandler(ui_flow_handler.course_selection_handler, pattern=r"^course_\d+$"))
    application.add_handler(CallbackQueryHandler(ui_flow_handler.year_selection_handler, pattern=r"^year_\d+$"))
    application.add_handler(CallbackQueryHandler(ui_flow_handler.help_handler, pattern="^help$"))
    
    # Message handlers for upload flows (legacy)
    application.add_handler(CommandHandler("done", admin_upload_done))
    application.add_handler(MessageHandler((filters.Document.ALL | filters.PHOTO | filters.TEXT) & ~filters.COMMAND, upload_message_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_edit_message_handler))
    
    # UI Flow message handlers (Master Specification Section 11)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ui_flow_handler.admin_code_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, ui_flow_handler.super_admin_key_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, spec_handler.restore_confirmation_handler))
    
    # New upload message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, upload_handler.handle_text_upload))
    application.add_handler(MessageHandler((filters.Document.ALL | filters.PHOTO) & ~filters.COMMAND, upload_handler.handle_file_upload))

    # Add error handler
    application.add_error_handler(error_handler)

def main():
    """Main function to run the bot (synchronous for PTB v21)."""
    logger.info("Starting BotCamp Medical Bot...")
    
    # Create database tables
    logger.info("Creating database tables...")
    create_tables_sync()
    logger.info("Database tables created successfully")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    # Start telemetry collector
    collector.start()
    
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
