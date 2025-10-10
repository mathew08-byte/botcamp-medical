from functools import wraps
from database.db_v2 import SessionLocal
from models import User, RoleEnum


def get_user_role(telegram_id: int) -> str:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == str(telegram_id)).first()
        return (user.role if user else RoleEnum.student).__str__()
    finally:
        db.close()


def requires_role(required_role: str):
    def wrapper(handler):
        @wraps(handler)
        async def inner(update, context, *args, **kwargs):
            tg_id = update.effective_user.id
            role = get_user_role(tg_id)
            if role not in [required_role, RoleEnum.super_admin.value]:
                await update.effective_message.reply_text("⛔ You are not authorized for this command.")
                return
            return await handler(update, context, *args, **kwargs)
        return inner
    return wrapper


