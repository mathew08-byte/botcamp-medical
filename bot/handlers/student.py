from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.utils.cache import get_cache, set_cache
from database.db_v2 import SessionLocal
from models import University, Course, Unit, Topic


async def take_quiz_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    db = SessionLocal()
    try:
        cache_key = "universities_active"
        data = get_cache(cache_key)
        if not data:
            universities = db.query(University).filter(University.is_active == True).all()
            data = [(u.id, u.name) for u in universities]
            set_cache(cache_key, data)
        keyboard = [[InlineKeyboardButton(name, callback_data=f"stu_u_{uid}")] for uid, name in data]
        await query.edit_message_text("Select University:", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()


async def select_course(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, uid = query.data.partition("stu_u_")
    db = SessionLocal()
    try:
        cache_key = f"courses_{uid}"
        data = get_cache(cache_key)
        if not data:
            courses = db.query(Course).filter(Course.university_id == int(uid), Course.is_active == True).all()
            data = [(c.id, c.name) for c in courses]
            set_cache(cache_key, data)
        keyboard = [[InlineKeyboardButton(name, callback_data=f"stu_c_{cid}")] for cid, name in data]
        await query.edit_message_text("Select Course:", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()


async def select_year(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, cid = query.data.partition("stu_c_")
    # Years 1-6 (seeded 1-3 for now)
    keyboard = [[InlineKeyboardButton(f"Year {y}", callback_data=f"stu_y_{cid}_{y}")] for y in range(1, 7)]
    await query.edit_message_text("Select Year:", reply_markup=InlineKeyboardMarkup(keyboard))


async def select_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, rest = query.data.partition("stu_y_")
    cid, _, year = rest.partition("_")
    db = SessionLocal()
    try:
        cache_key = f"units_{cid}_{year}"
        data = get_cache(cache_key)
        if not data:
            units = db.query(Unit).filter(Unit.course_id == int(cid), Unit.year == int(year), Unit.is_active == True).all()
            data = [(u.id, u.name) for u in units]
            set_cache(cache_key, data)
        keyboard = [[InlineKeyboardButton(name, callback_data=f"stu_unit_{uid}")] for uid, name in data]
        await query.edit_message_text("Select Unit:", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()


async def select_topic(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, _, unit_id = query.data.partition("stu_unit_")
    db = SessionLocal()
    try:
        cache_key = f"topics_{unit_id}"
        data = get_cache(cache_key)
        if not data:
            topics = db.query(Topic).filter(Topic.unit_id == int(unit_id), Topic.is_active == True).all()
            data = [(t.id, t.name) for t in topics]
            set_cache(cache_key, data)
        keyboard = [[InlineKeyboardButton(name, callback_data=f"stu_topic_{tid}")] for tid, name in data]
        await query.edit_message_text("Select Topic:", reply_markup=InlineKeyboardMarkup(keyboard))
    finally:
        db.close()


async def topic_ready(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start quiz when topic is selected - now integrated with quiz engine."""
    from bot.handlers.student_quiz import start_quiz_for_topic
    await start_quiz_for_topic(update, context)


