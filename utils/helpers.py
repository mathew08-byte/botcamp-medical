import logging
from typing import Optional
from sqlalchemy import select
from database.db import get_async_db
from database.models import User, Admin

logger = logging.getLogger(__name__)

async def get_or_create_user(telegram_user) -> Optional[User]:
    """Get or create a user from telegram user object"""
    async for db in get_async_db():
        # Check if user exists
        result = await db.execute(select(User).where(User.telegram_id == telegram_user.id))
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            return existing_user
        
        # Create new user
        new_user = User(
            telegram_id=telegram_user.id,
            username=telegram_user.username,
            first_name=telegram_user.first_name,
            last_name=telegram_user.last_name
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"Created new user: {telegram_user.id}")
        return new_user

async def is_admin(telegram_id: int) -> bool:
    """Check if user is an admin"""
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == telegram_id))
        admin = result.scalar_one_or_none()
        return admin is not None

def format_quiz_score(correct: int, total: int) -> str:
    """Format quiz score with emoji"""
    percentage = (correct / total) * 100 if total > 0 else 0
    
    if percentage >= 90:
        return f"🏆 {correct}/{total} ({percentage:.1f}%) - Excellent!"
    elif percentage >= 80:
        return f"👏 {correct}/{total} ({percentage:.1f}%) - Great job!"
    elif percentage >= 70:
        return f"👍 {correct}/{total} ({percentage:.1f}%) - Good work!"
    elif percentage >= 60:
        return f"📚 {correct}/{total} ({percentage:.1f}%) - Keep studying!"
    else:
        return f"💪 {correct}/{total} ({percentage:.1f}%) - Don't give up!"

def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def escape_markdown(text: str) -> str:
    """Escape special characters for Markdown"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
