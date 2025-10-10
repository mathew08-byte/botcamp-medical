from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def super_admin_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Manage Admins", callback_data="sup_manage_admins")],
        [InlineKeyboardButton("🧩 View All Uploads", callback_data="sup_uploads")],
        [InlineKeyboardButton("⚙️ System Stats", callback_data="sup_stats")],
    ])


