from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def admin_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 Upload Questions", callback_data="adm_upload")],
        [InlineKeyboardButton("📝 Review Drafts", callback_data="adm_review")],
        [InlineKeyboardButton("📈 Upload Stats", callback_data="adm_stats")],
        [InlineKeyboardButton("📊 Analytics", callback_data="analytics_quizzes")],
        [InlineKeyboardButton("👤 My Contributions", callback_data="my_contributions")],
        [InlineKeyboardButton("📋 Admin Dashboard", callback_data="admin_dashboard")],
    ])


def super_admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗂 Upload Questions", callback_data="adm_upload")],
        [InlineKeyboardButton("📝 Review Drafts", callback_data="adm_review")],
        [InlineKeyboardButton("📈 Upload Stats", callback_data="adm_stats")],
        [InlineKeyboardButton("📊 Analytics", callback_data="analytics_quizzes")],
        [InlineKeyboardButton("👤 My Contributions", callback_data="my_contributions")],
        [InlineKeyboardButton("📋 Admin Dashboard", callback_data="admin_dashboard")],
        [InlineKeyboardButton("🔍 Moderation Queue", callback_data="moderation_queue")],
        [InlineKeyboardButton("⚙️ System Status", callback_data="system_status")],
    ])


