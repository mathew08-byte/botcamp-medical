from telegram import Update
from telegram.ext import ContextTypes
from bot.utils.role_check import requires_role
from database.db_v2 import SessionLocal
from models import User, RoleEnum


@requires_role("super_admin")
async def setrole(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /setrole <telegram_id> <student|admin|super_admin>")
        return
    target_id, role = context.args
    if role not in [e.value for e in RoleEnum]:
        await update.message.reply_text("Invalid role.")
        return
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == target_id).first()
        if not user:
            await update.message.reply_text("User not found.")
            return
        user.role = RoleEnum(role)
        db.commit()
        await update.message.reply_text(f"✅ Set role of {user.username or user.telegram_id} to {role}")
    finally:
        db.close()


@requires_role("super_admin")
async def roles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        users = db.query(User).all()
        if not users:
            await update.message.reply_text("No users.")
            return
        header = "telegram_id | username | role\n" + "-"*40
        rows = [f"{u.telegram_id} | @{u.username or ''} | {u.role}" for u in users]
        await update.message.reply_text("\n".join([header, *rows]))
    finally:
        db.close()


