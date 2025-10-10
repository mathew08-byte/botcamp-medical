import asyncio
import logging
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Import handlers
from handlers.start_sync import (
    start_command, select_university_callback, university_selected_callback,
    course_selected_callback, year_selected_callback, unit_selected_callback,
    topic_selected_callback, main_menu_callback, help_callback
)

# Import database setup
from database.db import create_tables

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot token - hardcoded for now
BOT_TOKEN = "8426722737:AAFhuYdUhqn-D3CJdkEMD8mA16JoIk8T9JI"

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not found in environment variables")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors"""
    logger.error(f"Update {update} caused error {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again or contact support."
        )

def setup_handlers(application: Application):
    """Setup all bot handlers"""
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    
    # Callback query handlers for start flow
    application.add_handler(CallbackQueryHandler(select_university_callback, pattern=r"^select_university$"))
    application.add_handler(CallbackQueryHandler(university_selected_callback, pattern=r"^university_\d+$"))
    application.add_handler(CallbackQueryHandler(course_selected_callback, pattern=r"^course_\d+$"))
    application.add_handler(CallbackQueryHandler(year_selected_callback, pattern=r"^year_\d+_.+$"))
    application.add_handler(CallbackQueryHandler(unit_selected_callback, pattern=r"^unit_\d+$"))
    application.add_handler(CallbackQueryHandler(topic_selected_callback, pattern=r"^topic_\d+$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^main_menu$"))
    application.add_handler(CallbackQueryHandler(help_callback, pattern=r"^help$"))
    
    # Add error handler
    application.add_error_handler(error_handler)

async def main():
    """Main function to run the bot"""
    logger.info("Starting BotCamp Medical Bot...")
    
    # Create database tables
    logger.info("Creating database tables...")
    create_tables()
    logger.info("Database tables created successfully")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Setup handlers
    setup_handlers(application)
    
    # Start the bot
    logger.info("Bot is starting...")
    await application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise
