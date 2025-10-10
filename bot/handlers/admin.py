from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.role_check import requires_role


@requires_role("admin")
async def upload_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🗂 Upload Questions (coming soon in Step 4)")


@requires_role("admin")
async def review_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📝 Review Drafts (coming soon)")


@requires_role("admin")
async def stats_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("📈 Upload Stats (coming soon)")


