from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.role_check import get_user_role
from bot.keyboards.student_menu import student_main_menu
from bot.keyboards.admin_menu import admin_main_menu
from bot.keyboards.super_admin_menu import super_admin_main_menu


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    role = get_user_role(user.id)
    header = f"🧠 Welcome, {user.first_name}!\nRole: "
    if role == "super_admin":
        await update.message.reply_text(header + "👑 Super Admin\nChoose an option below:", reply_markup=super_admin_main_menu())
    elif role == "admin":
        await update.message.reply_text(header + "🛠️ Admin\nChoose an option below:", reply_markup=admin_main_menu())
    else:
        await update.message.reply_text(header + "👨‍🎓 Student\nChoose an option below:", reply_markup=student_main_menu())


