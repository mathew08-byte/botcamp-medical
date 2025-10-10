from telegram import Update
from telegram.ext import ContextTypes
from functools import wraps
from database.db_v2 import SessionLocal
from models import User, RoleEnum


def requires_role(role: RoleEnum):
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            tg_user = update.effective_user
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == str(tg_user.id)).first()
                if not user or (role == RoleEnum.super_admin and user.role != RoleEnum.super_admin):
                    await update.effective_message.reply_text("❌ Permission denied.")
                    return
            finally:
                db.close()
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tg_user = update.effective_user
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == str(tg_user.id)).first()
        if not user:
            user = User(
                telegram_id=str(tg_user.id),
                username=tg_user.username,
                first_name=tg_user.first_name,
                last_name=tg_user.last_name,
                role=RoleEnum.student,
            )
            db.add(user)
            db.commit()
        await update.message.reply_text("Welcome to BotCamp Medical. Your account is ready.")
    finally:
        db.close()


@requires_role(RoleEnum.super_admin)
async def grant_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /grant_admin <telegram_id>")
        return
    target_id = context.args[0]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == target_id).first()
        if not user:
            await update.message.reply_text("User not found.")
            return
        user.role = RoleEnum.admin
        db.commit()
        await update.message.reply_text(f"✅ Granted admin to {user.username or user.telegram_id}")
    finally:
        db.close()


@requires_role(RoleEnum.super_admin)
async def revoke_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) != 1:
        await update.message.reply_text("Usage: /revoke_admin <telegram_id>")
        return
    target_id = context.args[0]
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == target_id).first()
        if not user:
            await update.message.reply_text("User not found.")
            return
        user.role = RoleEnum.student
        db.commit()
        await update.message.reply_text(f"✅ Revoked admin from {user.username or user.telegram_id}")
    finally:
        db.close()


@requires_role(RoleEnum.super_admin)
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.created_at.desc()).limit(50).all()
        if not users:
            await update.message.reply_text("No users found.")
            return
        lines = [f"{u.first_name or ''} @{u.username or ''} ({u.telegram_id}) - {u.role}" for u in users]
        await update.message.reply_text("\n".join(lines))
    finally:
        db.close()


