from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import ContextTypes
from database.db import get_async_db
from database.models import Admin, User, Question, QuizSession, University, Course, Unit, Topic, Paper, ErrorLog, EventLog
from sqlalchemy import select, func, and_
import logging
from services.ocr import extract_text_from_file
from services.ai_parser import parse_mcqs_with_ai
from services.moderation import moderate_question_with_ai
from services.analytics_service import AnalyticsService
import json
import os
from services.cache import memory_cache
import csv
import io
from services.backup_export_service import BackupExportService
from services.role_management_service import RoleManagementService
from database.models import EventLog
from datetime import datetime
from config.auth import DEFAULT_SUPER_ADMIN_ID
from services.security_service import SecurityService
from database.models import UploadBatch, UploadItem
from services.ocr import extract_text_from_file
from services.ai_parser import parse_mcqs_with_ai
import time
from database.models import SystemLog

logger = logging.getLogger(__name__)

async def is_admin(user_id: int) -> bool:
    """Check if user is an admin"""
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user_id))
        admin = result.scalar_one_or_none()
        return admin is not None

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command"""
    user = update.effective_user
    
    if not await is_admin(user.id):
        await update.message.reply_text("❌ You don't have admin privileges.")
        return
    
    admin_text = """
🔧 **Admin Panel**

Welcome to the admin panel! Choose an option below:

**Content Management:**
• Manage universities, courses, and units
• Add/edit questions and topics
• Manage papers

**User Management:**
• View user statistics
• Manage admin users

**System:**
• View system statistics
• Database management
"""
    
    keyboard = [
        [InlineKeyboardButton("🏫 Manage Universities", callback_data="admin_universities")],
        [InlineKeyboardButton("📚 Manage Courses", callback_data="admin_courses")],
        [InlineKeyboardButton("📝 Manage Questions", callback_data="admin_questions")],
        [InlineKeyboardButton("📤 Upload Questions", callback_data="admin_upload_questions")],
        [InlineKeyboardButton("👥 User Statistics", callback_data="admin_user_stats")],
        [InlineKeyboardButton("📊 System Statistics", callback_data="admin_system_stats")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_universities_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage universities"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    
    # Get database session
    async for db in get_async_db():
        result = await db.execute(select(University).order_by(University.name))
        universities = result.scalars().all()
    
    if not universities:
        text = "No universities found."
        keyboard = [[InlineKeyboardButton("➕ Add University", callback_data="admin_add_university")]]
    else:
        text = "🏫 **Universities:**\n\n"
        keyboard = []
        
        for university in universities:
            status = "✅" if university.is_active else "❌"
            text += f"{status} {university.name}\n"
            keyboard.append([InlineKeyboardButton(
                f"{status} {university.name}",
                callback_data=f"admin_edit_university_{university.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Add University", callback_data="admin_add_university")])
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_courses_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage courses"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    
    # Get database session
    async for db in get_async_db():
        result = await db.execute(select(Course).join(University).order_by(University.name, Course.name))
        courses = result.scalars().all()
    
    if not courses:
        text = "No courses found."
        keyboard = [[InlineKeyboardButton("➕ Add Course", callback_data="admin_add_course")]]
    else:
        text = "📚 **Courses:**\n\n"
        keyboard = []
        
        for course in courses:
            status = "✅" if course.is_active else "❌"
            text += f"{status} {course.name} ({course.university.name})\n"
            keyboard.append([InlineKeyboardButton(
                f"{status} {course.name}",
                callback_data=f"admin_edit_course_{course.id}"
            )])
        
        keyboard.append([InlineKeyboardButton("➕ Add Course", callback_data="admin_add_course")])
    
    keyboard.append([InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_questions_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage questions"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    
    # Get database session
    async for db in get_async_db():
        # Get question statistics
        result = await db.execute(select(func.count(Question.id)))
        total_questions = result.scalar()
        
        result = await db.execute(select(func.count(Question.id)).where(Question.is_active == True))
        active_questions = result.scalar()
        
        # Get questions by topic
        result = await db.execute(
            select(Topic.name, func.count(Question.id))
            .join(Question)
            .group_by(Topic.id, Topic.name)
            .order_by(func.count(Question.id).desc())
        )
        questions_by_topic = result.all()
    
    text = f"""
📝 **Questions Management**

**Statistics:**
• Total Questions: {total_questions}
• Active Questions: {active_questions}

**Questions by Topic:**
"""
    
    for topic_name, count in questions_by_topic[:10]:  # Show top 10
        text += f"• {topic_name}: {count} questions\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Add Question", callback_data="admin_add_question")],
        [InlineKeyboardButton("📊 View All Questions", callback_data="admin_view_questions")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_user_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View user statistics"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    
    # Get database session
    async for db in get_async_db():
        # Get user statistics
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar()
        
        result = await db.execute(select(func.count(QuizSession.id)))
        total_quizzes = result.scalar()
        
        result = await db.execute(select(func.count(QuizSession.id)).where(QuizSession.is_completed == True))
        completed_quizzes = result.scalar()
        
        # Get recent users
        result = await db.execute(select(User).order_by(User.created_at.desc()).limit(5))
        recent_users = result.scalars().all()
    
    text = f"""
👥 **User Statistics**

**Overview:**
• Total Users: {total_users}
• Total Quizzes Started: {total_quizzes}
• Completed Quizzes: {completed_quizzes}

**Recent Users:**
"""
    
    for user in recent_users:
        text += f"• {user.first_name} (@{user.username or 'N/A'}) - {user.created_at.strftime('%Y-%m-%d')}\n"
    
    keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_system_stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View system statistics"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    
    # Get database session
    async for db in get_async_db():
        # Get comprehensive statistics
        result = await db.execute(select(func.count(University.id)))
        universities = result.scalar()
        
        result = await db.execute(select(func.count(Course.id)))
        courses = result.scalar()
        
        result = await db.execute(select(func.count(Unit.id)))
        units = result.scalar()
        
        result = await db.execute(select(func.count(Topic.id)))
        topics = result.scalar()
        
        result = await db.execute(select(func.count(Question.id)))
        questions = result.scalar()
        
        result = await db.execute(select(func.count(Paper.id)))
        papers = result.scalar()
        
        result = await db.execute(select(func.count(Admin.id)))
        admins = result.scalar()
    
    text = f"""
📊 **System Statistics**

**Content:**
• Universities: {universities}
• Courses: {courses}
• Units: {units}
• Topics: {topics}
• Questions: {questions}
• Papers: {papers}

**Users:**
• Admins: {admins}

**Database Status:** ✅ Healthy
"""
    
    keyboard = [[InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to admin panel"""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    
    admin_text = """
🔧 **Admin Panel**

Welcome to the admin panel! Choose an option below:

**Content Management:**
• Manage universities, courses, and units
• Add/edit questions and topics
• Manage papers

**User Management:**
• View user statistics
• Manage admin users

**System:**
• View system statistics
• Database management
"""
    
    keyboard = [
        [InlineKeyboardButton("🏫 Manage Universities", callback_data="admin_universities")],
        [InlineKeyboardButton("📚 Manage Courses", callback_data="admin_courses")],
        [InlineKeyboardButton("📝 Manage Questions", callback_data="admin_questions")],
        [InlineKeyboardButton("👥 User Statistics", callback_data="admin_user_stats")],
        [InlineKeyboardButton("📊 System Statistics", callback_data="admin_system_stats")],
        [InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        admin_text,
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def admin_upload_questions_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry point to upload questions (text/PDF/image)"""
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    keyboard = [
        [InlineKeyboardButton("1️⃣ Paste text manually", callback_data="admin_upload_text")],
        [InlineKeyboardButton("2️⃣ Upload PDF file", callback_data="admin_upload_pdf")],
        [InlineKeyboardButton("3️⃣ Upload image/screenshot", callback_data="admin_upload_image")],
        [InlineKeyboardButton("🔙 Admin Panel", callback_data="admin_panel")],
    ]
    await query.edit_message_text(
        "📤 How do you want to upload?\n1️⃣ Paste text manually\n2️⃣ Upload PDF file\n3️⃣ Upload image/screenshot",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def admin_upload_text_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["upload_mode"] = "text"
    await query.edit_message_text("✍️ Send the MCQ text now. When done, send /done.")

async def admin_upload_pdf_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["upload_mode"] = "pdf"
    await query.edit_message_text("📄 Please upload a PDF document now.")

async def admin_upload_image_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["upload_mode"] = "image"
    await query.edit_message_text("🖼️ Please upload one or more images/screenshots now. When done, send /done.")

async def upload_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Collect incoming messages during upload mode (text/images/documents)."""
    mode = context.user_data.get("upload_mode")
    if not mode:
        return
    bucket = context.user_data.setdefault("upload_bucket", [])
    if update.message.text and mode == "text":
        bucket.append(update.message.text)
    elif update.message.document:
        file = await update.message.document.get_file()
        content = await file.download_as_bytearray()
        bucket.append({"bytes": bytes(content), "mime": update.message.document.mime_type})
    elif update.message.photo:
        photo = update.message.photo[-1]
        file = await photo.get_file()
        content = await file.download_as_bytearray()
        bucket.append({"bytes": bytes(content), "mime": "image/jpeg"})

async def admin_upload_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Finalize collection and run OCR/AI parsing, then show review UI."""
    user = update.effective_user
    if not await is_admin(user.id):
        await update.message.reply_text("❌ You don't have admin privileges.")
        return
    mode = context.user_data.get("upload_mode")
    bucket = context.user_data.get("upload_bucket", [])
    raw_text = ""
    if mode == "text":
        raw_text = "\n\n".join(bucket)
    else:
        texts = []
        for item in bucket:
            texts.append(extract_text_from_file(item["bytes"], item.get("mime")))
        raw_text = "\n\n".join([t for t in texts if t])
    parsed = parse_mcqs_with_ai(raw_text)
    context.user_data["parsed_mcqs"] = parsed
    context.user_data["review_index"] = 0
    # Invalidate curriculum/analytics caches since content will change soon
    try:
        memory_cache.delete("curriculum_universities")
        # broader invalidation keys
        for k in list(memory_cache._store.keys()):
            if isinstance(k, str) and (k.startswith("curriculum_") or k.startswith("analytics_")):
                memory_cache.delete(k)
    except Exception:
        pass
    # Log upload action
    async for db in get_async_db():
        db.add(EventLog(user_id=user.id, event_type="upload_batch", context={"mode": mode, "items": len(bucket)}))
        await db.commit()
    await _show_review_card(update, context)

async def _show_review_card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parsed = context.user_data.get("parsed_mcqs") or {"questions": []}
    idx = context.user_data.get("review_index", 0)
    questions = parsed.get("questions", [])
    if idx >= len(questions):
        await update.message.reply_text("✅ Review done. No more questions.")
        context.user_data.pop("upload_mode", None)
        context.user_data.pop("upload_bucket", None)
        return
    q = questions[idx]
    text = (
        f"Q{idx+1}: {q.get('question','')}\n"
        f"A) {q.get('options',[None,None,None,None])[0]}\n"
        f"B) {q.get('options',[None,None,None,None])[1]}\n"
        f"C) {q.get('options',[None,None,None,None])[2]}\n"
        f"D) {q.get('options',[None,None,None,None])[3]}\n"
        f"\nDetected answer: {q.get('correct_answer') or 'N/A'}"
    )
    keyboard = [
        [InlineKeyboardButton("✅ Confirm", callback_data="admin_review_confirm")],
        [InlineKeyboardButton("✏️ Edit", callback_data="admin_review_edit")],
        [InlineKeyboardButton("❌ Reject", callback_data="admin_review_reject")],
    ]
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        query = update.callback_query
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_review_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    parsed = context.user_data.get("parsed_mcqs") or {"questions": []}
    idx = context.user_data.get("review_index", 0)
    questions = parsed.get("questions", [])
    if idx >= len(questions):
        await query.edit_message_text("No more questions.")
        return
    q = questions[idx]
    try:
        await _insert_question_with_moderation(update, context, q, user)
        async for db in get_async_db():
            log = SystemLog(user_id=user.id, action="moderation_confirm", details=q.get("question")[:120])
            db.add(log)
            await db.commit()
    except Exception as e:
        async for db in get_async_db():
            log = SystemLog(user_id=user.id, action="moderation_confirm_error", details=str(e), error_message=str(e))
            db.add(log)
            await db.commit()
        await update.effective_message.reply_text("⚠️ Something went wrong while saving this question.")
    context.user_data["review_index"] = idx + 1
    await query.edit_message_text("✅ Uploaded. Moving to next…")
    await _show_review_card(update, context)

async def admin_review_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = update.effective_user
    if not await is_admin(user.id):
        await query.edit_message_text("❌ You don't have admin privileges.")
        return
    idx = context.user_data.get("review_index", 0)
    context.user_data["review_index"] = idx + 1
    await query.edit_message_text("⏭️ Rejected. Moving to next…")
    await _show_review_card(update, context)

async def admin_review_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["editing"] = True
    await query.edit_message_text("Send corrected JSON for this question only. We'll parse and use it.")

async def admin_edit_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("editing"):
        return
    try:
        data = update.message.text
        obj = json.loads(data)
    except Exception:
        await update.message.reply_text("Invalid JSON. Try again.")
        return
    parsed = context.user_data.get("parsed_mcqs") or {"questions": []}
    idx = context.user_data.get("review_index", 0)
    if idx < len(parsed.get("questions", [])):
        parsed["questions"][idx] = obj
    context.user_data["editing"] = False
    await update.message.reply_text("✔️ Updated. Now confirm or reject.")

async def _insert_question(update: Update, context: ContextTypes.DEFAULT_TYPE, q: dict, tg_user):
    async for db in get_async_db():
        # Ensure topic exists or choose default mapping (simplified: requires manual topic selection later)
        result = await db.execute(select(Topic).order_by(Topic.id))
        topic = result.scalars().first()
        if not topic:
            await update.effective_message.reply_text("No topics found. Please create a topic first.")
            return
        question = Question(
            topic_id=topic.id,
            question_text=q.get("question") or "",
            option_a=(q.get("options") or [None,None,None,None])[0] or "",
            option_b=(q.get("options") or [None,None,None,None])[1] or "",
            option_c=(q.get("options") or [None,None,None,None])[2] or "",
            option_d=(q.get("options") or [None,None,None,None])[3] or "",
            correct_answer=_map_correct_option(q.get("correct_answer"), q.get("options") or []),
            explanation=q.get("explanation"),
            source=q.get("source"),
            uploader_user_id=None,
            uploader_username=(getattr(tg_user, 'username', None) or None),
            is_active=True,
        )
        db.add(question)
        await db.commit()

async def _insert_question_with_moderation(update: Update, context: ContextTypes.DEFAULT_TYPE, q: dict, tg_user):
    async for db in get_async_db():
        # pick first topic (TODO: prompt metadata selection in UI)
        result = await db.execute(select(Topic).order_by(Topic.id))
        topic = result.scalars().first()
        if not topic:
            await update.effective_message.reply_text("No topics found. Please create a topic first.")
            return

        # Run AI moderation
        moderation = moderate_question_with_ai({
            "question": q.get("question"),
            "options": q.get("options"),
            "correct_answer": q.get("correct_answer"),
            "explanation": q.get("explanation"),
            "topic": getattr(topic, 'name', None),
        })
        mscore = moderation.get("moderation_score")
        mcomments = moderation.get("moderation_comments")
        action = (moderation.get("action") or "flag").lower()

        needs_review = (action == "flag")
        is_reject = (action == "reject")

        # Update contributor counters
        result = await db.execute(select(User).where(User.username == (tg_user.username or None)))
        uploader_user = result.scalar_one_or_none()
        if uploader_user:
            uploader_user.upload_count = (uploader_user.upload_count or 0) + 1
            if is_reject:
                uploader_user.rejected_count = (uploader_user.rejected_count or 0) + 1
            elif needs_review:
                uploader_user.flagged_count = (uploader_user.flagged_count or 0) + 1
            else:
                uploader_user.approved_count = (uploader_user.approved_count or 0) + 1
                # update avg moderation score
                if mscore is not None:
                    prev_avg = uploader_user.average_moderation_score or 0
                    prev_n = (uploader_user.approved_count - 1) if uploader_user.approved_count and uploader_user.approved_count > 0 else 0
                    new_avg = int(round(((prev_avg * prev_n) + int(mscore)) / (prev_n + 1)))
                    uploader_user.average_moderation_score = new_avg

        if is_reject:
            await db.commit()
            await update.effective_message.reply_text("❌ Rejected by AI moderation.")
            return

        question = Question(
            topic_id=topic.id,
            question_text=q.get("question") or "",
            option_a=(q.get("options") or [None,None,None,None])[0] or "",
            option_b=(q.get("options") or [None,None,None,None])[1] or "",
            option_c=(q.get("options") or [None,None,None,None])[2] or "",
            option_d=(q.get("options") or [None,None,None,None])[3] or "",
            correct_answer=_map_correct_option(q.get("correct_answer"), q.get("options") or []),
            explanation=q.get("explanation"),
            source=q.get("source"),
            uploader_user_id=None,
            uploader_username=(getattr(tg_user, 'username', None) or None),
            is_active=(not needs_review),
            moderation_score=(int(mscore) if mscore is not None else None),
            moderation_comments=mcomments,
            moderated_by_ai=True,
            needs_review=needs_review,
        )
        db.add(question)
        await db.commit()

        if needs_review:
            await update.effective_message.reply_text("⚠️ Added to moderation queue for super admin review.")
        else:
            await update.effective_message.reply_text("✅ Question published.")

async def moderation_queue_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show moderation queue for super admins"""
    try:
        user = update.effective_user
        if _rate_limited(user.id):
            await update.message.reply_text("⏳ Slow down, please.")
            return
        
        # Check if user is super admin
        async for db in get_async_db():
            result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
            super_admin = result.scalar_one_or_none()
            if not super_admin:
                await update.message.reply_text("❌ Super admin only.")
                return
        
        # Use analytics service to get moderation queue
        analytics_service = AnalyticsService()
        pending_questions = analytics_service.get_moderation_queue()
        
        if not pending_questions:
            await update.message.reply_text("✅ No questions pending moderation review.")
            return
        
        # Create message with inline keyboard
        message = "🔍 **Moderation Queue**\n\n"
        keyboard = []
        
        for i, q in enumerate(pending_questions[:10]):  # Show first 10
            message += f"**{i+1}.** {q['question_text']}\n"
            message += f"📊 Score: {q['moderation_score']}/100 | 👤 {q['uploader']}\n"
            message += f"📅 {q['created_at']} | 🏷️ {q['topic']}\n\n"
            
            # Add action buttons for each question
            keyboard.append([
                InlineKeyboardButton(f"✅ Approve {i+1}", callback_data=f"mod_approve_{q['question_id']}"),
                InlineKeyboardButton(f"❌ Reject {i+1}", callback_data=f"mod_reject_{q['question_id']}"),
                InlineKeyboardButton(f"✏️ Review {i+1}", callback_data=f"mod_review_{q['question_id']}")
            ])
        
        if len(pending_questions) > 10:
            message += f"... and {len(pending_questions) - 10} more questions pending review."
        
        keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="moderation_queue")])
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in moderation_queue_command: {e}")
        await update.message.reply_text("❌ Error loading moderation queue.")

async def moderation_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed question for review"""
    try:
        query = update.callback_query
        await query.answer()
        
        question_id = int(query.data.split('_')[-1])
        
        async for db in get_async_db():
            result = await db.execute(select(Question).where(Question.question_id == question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                await query.edit_message_text("❌ Question not found.")
                return
            
            # Get uploader info
            uploader_result = await db.execute(select(User).where(User.user_id == question.uploader_id))
            uploader = uploader_result.scalar_one_or_none()
            
            message = f"🔍 **Question Review**\n\n"
            message += f"**Question:** {question.question_text}\n\n"
            message += f"**A)** {question.option_a}\n"
            message += f"**B)** {question.option_b}\n"
            message += f"**C)** {question.option_c}\n"
            message += f"**D)** {question.option_d}\n\n"
            message += f"**Correct Answer:** {question.correct_option}\n"
            message += f"**Explanation:** {question.explanation or 'None'}\n\n"
            message += f"**Topic:** {question.topic}\n"
            message += f"**Unit:** {question.unit}\n"
            message += f"**Uploader:** {uploader.username or uploader.first_name if uploader else 'Unknown'}\n"
            message += f"**AI Score:** {question.moderation_score or 0}/100\n"
            message += f"**AI Comments:** {question.moderation_comments or 'None'}\n"
            message += f"**Created:** {question.created_at.strftime('%Y-%m-%d %H:%M') if question.created_at else 'Unknown'}"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"mod_approve_{question_id}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"mod_reject_{question_id}")
                ],
                [InlineKeyboardButton("🔙 Back to Queue", callback_data="moderation_queue")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in moderation_review_callback: {e}")
        await query.edit_message_text("❌ Error loading question details.")

async def moderation_approve_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve a question"""
    try:
        query = update.callback_query
        await query.answer()
        
        question_id = int(query.data.split('_')[-1])
        
        async for db in get_async_db():
            result = await db.execute(select(Question).where(Question.question_id == question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                await query.edit_message_text("❌ Question not found.")
                return
            
            # Approve the question
            question.needs_review = False
            question.is_active = True
            question.reviewed_by_admin_id = update.effective_user.id
            
            # Update contributor stats
            analytics_service = AnalyticsService()
            if question.uploader_id:
                analytics_service.update_contributor_stats(question.uploader_id, question_id, "approved")
            
            # Log the event
            db.add(EventLog(user_id=update.effective_user.id, event_type="moderation_approve", context={"question_id": question_id}))
            await db.commit()
        
        await query.edit_message_text("✅ Question approved and published!")
        
    except Exception as e:
        logger.error(f"Error in moderation_approve_callback: {e}")
        await query.edit_message_text("❌ Error approving question.")

async def moderation_reject_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reject a question"""
    try:
        query = update.callback_query
        await query.answer()
        
        question_id = int(query.data.split('_')[-1])
        
        async for db in get_async_db():
            result = await db.execute(select(Question).where(Question.question_id == question_id))
            question = result.scalar_one_or_none()
            
            if not question:
                await query.edit_message_text("❌ Question not found.")
                return
            
            # Reject the question
            question.needs_review = False
            question.is_active = False
            question.reviewed_by_admin_id = update.effective_user.id
            
            # Update contributor stats
            analytics_service = AnalyticsService()
            if question.uploader_id:
                analytics_service.update_contributor_stats(question.uploader_id, question_id, "rejected")
            
            # Log the event
            db.add(EventLog(user_id=update.effective_user.id, event_type="moderation_reject", context={"question_id": question_id}))
            await db.commit()
        
        await query.edit_message_text("❌ Question rejected and unpublished.")
        
    except Exception as e:
        logger.error(f"Error in moderation_reject_callback: {e}")
        await query.edit_message_text("❌ Error rejecting question.")

async def analytics_quizzes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show quiz analytics"""
    try:
        user = update.effective_user
        if _rate_limited(user.id):
            await update.message.reply_text("⏳ Slow down, please.")
            return
        
        # Check user role
        async for db in get_async_db():
            result = await db.execute(select(User).where(User.telegram_id == user.id))
            user_obj = result.scalar_one_or_none()
            
            if not user_obj:
                await update.message.reply_text("❌ User not found.")
                return
            
            # Get analytics based on user role
            analytics_service = AnalyticsService()
            if user_obj.role == 'student':
                analytics = analytics_service.get_quiz_analytics(user_id=user_obj.user_id)
            else:
                analytics = analytics_service.get_quiz_analytics()
            
            if not analytics:
                await update.message.reply_text("📊 No quiz data available yet.")
                return
            
            # Format message
            message = "📊 **Quiz Analytics**\n\n"
            
            if user_obj.role == 'student':
                message += f"**Your Performance:**\n"
                message += f"📝 Total Quizzes: {analytics['total_quizzes']}\n"
                message += f"✅ Completed: {analytics['completed_quizzes']}\n"
                message += f"🎯 Average Accuracy: {analytics['average_accuracy']}%\n"
                message += f"📚 Questions Attempted: {analytics['total_questions_attempted']}\n"
                message += f"✅ Correct Answers: {analytics['total_correct_answers']}\n\n"
            else:
                message += f"**System Overview:**\n"
                message += f"📝 Total Quizzes: {analytics['total_quizzes']}\n"
                message += f"✅ Completed: {analytics['completed_quizzes']}\n"
                message += f"🎯 Average Accuracy: {analytics['average_accuracy']}%\n"
                message += f"📚 Questions Attempted: {analytics['total_questions_attempted']}\n"
                message += f"✅ Correct Answers: {analytics['total_correct_answers']}\n\n"
            
            # Most attempted topics
            if analytics['most_attempted_topics']:
                message += "🔥 **Most Attempted Topics:**\n"
                for topic in analytics['most_attempted_topics'][:3]:
                    message += f"• {topic['name']}: {topic['count']} quizzes\n"
                message += "\n"
            
            # Lowest performing topics
            if analytics['lowest_performing_topics']:
                message += "⚠️ **Topics Needing Attention:**\n"
                for topic in analytics['lowest_performing_topics'][:3]:
                    message += f"• {topic['name']}: {topic['accuracy']}% accuracy\n"
                message += "\n"
            
            # Top students (only for admins/super_admins)
            if user_obj.role in ['admin', 'super_admin'] and analytics['top_students']:
                message += "🏆 **Top Students:**\n"
                for student in analytics['top_students'][:5]:
                    message += f"• {student['username']}: {student['accuracy']}% ({student['quizzes']} quizzes)\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="analytics_quizzes")],
                [InlineKeyboardButton("📈 My Stats", callback_data="my_stats")] if user_obj.role == 'student' else [],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            # Remove empty lists
            keyboard = [row for row in keyboard if row]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in analytics_quizzes_command: {e}")
        await update.message.reply_text("❌ Error loading quiz analytics.")

async def errors_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # super admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            await update.message.reply_text("❌ Super admin only.")
            return
        # counts by severity
        critical = (await db.execute(select(func.count(ErrorLog.id)).where(ErrorLog.severity == 'critical'))).scalar() or 0
        warnings = (await db.execute(select(func.count(ErrorLog.id)).where(ErrorLog.severity == 'warning'))).scalar() or 0
        infos = (await db.execute(select(func.count(ErrorLog.id)).where(ErrorLog.severity == 'info'))).scalar() or 0
        # most recent critical
        result = await db.execute(select(ErrorLog).where(ErrorLog.severity == 'critical').order_by(ErrorLog.timestamp.desc()))
        recent = result.scalars().first()
    text = (
        "🧯 Error Analytics (last 24h aggregate TBD)\n"
        f"🔴 Critical: {critical}\n"
        f"🟠 Warnings: {warnings}\n"
        f"🟢 Info: {infos}\n"
        f"Most recent critical: {recent.message if recent else '-'}"
    )
    await update.message.reply_text(text)

async def alerts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show active alerts based on recent EventLog entries (last 15 minutes)."""
    user = update.effective_user
    # super admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            await update.message.reply_text("❌ Super admin only.")
            return
        # Time window: last 15 minutes
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(minutes=15)
        # AI error rate: count ai errors vs total ai calls
        total_ai = (await db.execute(select(func.count(EventLog.id)).where(and_(EventLog.timestamp >= since, EventLog.event_type.in_(["ai_call","ai_parse","ai_moderate"]))))).scalar() or 0
        ai_errors = (await db.execute(select(func.count(EventLog.id)).where(and_(EventLog.timestamp >= since, EventLog.event_type.in_(["ai_error","ai_parse_error"]))))).scalar() or 0
        ai_rate = (ai_errors / total_ai * 100) if total_ai > 0 else 0
        # Failed jobs placeholder (use ErrorLog as proxy)
        failed_jobs = (await db.execute(select(func.count(ErrorLog.id)).where(and_(ErrorLog.timestamp >= since, ErrorLog.severity == 'critical')))).scalar() or 0
        # Compose alerts
        lines = ["🚨 **Active Alerts (last 15m)**"]
        if ai_rate > 5:
            lines.append(f"• AI error rate high: {ai_rate:.1f}% (errors: {ai_errors} / total: {total_ai})")
        if failed_jobs > 10:
            lines.append(f"• Failed jobs spike: {failed_jobs}")
        if len(lines) == 1:
            lines.append("No active alerts.")
        # Recent AI errors sample
        result = await db.execute(select(EventLog).where(and_(EventLog.timestamp >= since, EventLog.event_type.in_(["ai_error","ai_parse_error"]))).order_by(EventLog.timestamp.desc()))
        recent = result.scalars().all()
        if recent:
            lines.append("\nLast AI errors:")
            for ev in recent[:5]:
                lines.append(f"- {ev.timestamp.strftime('%H:%M:%S')} {ev.metadata.get('message') if getattr(ev,'metadata',None) else ev.event_type}")
    await update.message.reply_text("\n".join(lines), parse_mode='Markdown')

async def my_contributions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show contributor dashboard"""
    try:
        user = update.effective_user
        if _rate_limited(user.id):
            await update.message.reply_text("⏳ Slow down, please.")
            return
        
        # Get user info
        async for db in get_async_db():
            result = await db.execute(select(User).where(User.telegram_id == user.id))
            user_obj = result.scalar_one_or_none()
            
            if not user_obj:
                await update.message.reply_text("❌ User not found.")
                return
            
            # Get contributor analytics
            analytics_service = AnalyticsService()
            analytics = analytics_service.get_contributor_analytics(user_obj.user_id)
            
            if not analytics:
                await update.message.reply_text("📊 No contribution data available.")
                return
            
            # Format message
            message = f"👤 **{analytics['user_info']['username']}**\n"
            message += f"🎭 Role: {analytics['user_info']['role'].title()}\n\n"
            
            message += "📤 **Upload Statistics:**\n"
            message += f"📝 Total Uploaded: {analytics['upload_stats']['total_uploaded']}\n"
            message += f"✅ Approved: {analytics['upload_stats']['approved']}\n"
            message += f"⚠️ Flagged: {analytics['upload_stats']['flagged']}\n"
            message += f"❌ Rejected: {analytics['upload_stats']['rejected']}\n"
            message += f"📊 Approval Rate: {analytics['upload_stats']['approval_rate']}%\n\n"
            
            message += "🎯 **Quality Metrics:**\n"
            message += f"⭐ Average AI Score: {analytics['quality_metrics']['average_moderation_score']}/100\n"
            message += f"📚 Most Active Unit: {analytics['quality_metrics']['most_active_unit']}\n"
            message += f"🏷️ Most Active Topic: {analytics['quality_metrics']['most_active_topic']}\n\n"
            
            message += "📊 **Quiz Performance:**\n"
            message += f"🎮 Quizzes Taken: {analytics['quiz_performance']['total_quizzes_taken']}\n"
            message += f"🎯 Average Accuracy: {analytics['quiz_performance']['average_accuracy']}%\n\n"
            
            # Add motivational message based on performance
            approval_rate = analytics['upload_stats']['approval_rate']
            if approval_rate >= 90:
                message += "🌟 Excellent work! You're a top contributor!"
            elif approval_rate >= 75:
                message += "👍 Great job! Keep up the good work!"
            elif approval_rate >= 50:
                message += "📈 Good progress! Try to improve question quality."
            else:
                message += "💪 Keep trying! Review the feedback and improve."
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="my_contributions")],
                [InlineKeyboardButton("📤 Upload Questions", callback_data="upload_questions")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in my_contributions_command: {e}")
        await update.message.reply_text("❌ Error loading contribution data.")

async def activity_summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    # admins only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id))
        a = result.scalar_one_or_none()
        if not a:
            await update.message.reply_text("❌ Admins only.")
            return
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        total_questions = (await db.execute(select(func.count(Question.id)))).scalar() or 0
        total_quizzes = (await db.execute(select(func.count(QuizSession.id)))).scalar() or 0
    text = (
        "📈 Activity Summary\n"
        f"Users: {total_users}\n"
        f"Questions: {total_questions}\n"
        f"Quizzes: {total_quizzes}\n"
    )
    await update.message.reply_text(text)

async def my_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show personal stats for students"""
    try:
        user = update.effective_user
        
        # Get user info
        async for db in get_async_db():
            result = await db.execute(select(User).where(User.telegram_id == user.id))
            user_obj = result.scalar_one_or_none()
            
            if not user_obj:
                await update.message.reply_text("❌ User not found.")
                return
            
            # Get personal analytics
            analytics_service = AnalyticsService()
            analytics = analytics_service.get_quiz_analytics(user_id=user_obj.user_id)
            contributor_analytics = analytics_service.get_contributor_analytics(user_obj.user_id)
            
            message = f"👤 **{user_obj.username or user_obj.first_name or 'Student'}**\n\n"
            
            # Quiz performance
            if analytics and analytics['total_quizzes'] > 0:
                message += "📊 **Quiz Performance:**\n"
                message += f"🎮 Total Quizzes: {analytics['total_quizzes']}\n"
                message += f"✅ Completed: {analytics['completed_quizzes']}\n"
                message += f"🎯 Average Accuracy: {analytics['average_accuracy']}%\n"
                message += f"📚 Questions Attempted: {analytics['total_questions_attempted']}\n"
                message += f"✅ Correct Answers: {analytics['total_correct_answers']}\n\n"
            else:
                message += "📊 **Quiz Performance:**\n"
                message += "🎮 No quizzes taken yet. Start taking quizzes to see your stats!\n\n"
            
            # Contribution stats (if any)
            if contributor_analytics and contributor_analytics['upload_stats']['total_uploaded'] > 0:
                message += "📤 **Contributions:**\n"
                message += f"📝 Questions Uploaded: {contributor_analytics['upload_stats']['total_uploaded']}\n"
                message += f"✅ Approved: {contributor_analytics['upload_stats']['approved']}\n"
                message += f"📊 Approval Rate: {contributor_analytics['upload_stats']['approval_rate']}%\n\n"
            
            # Motivational message
            if analytics and analytics['average_accuracy'] >= 80:
                message += "🌟 Excellent performance! Keep it up!"
            elif analytics and analytics['average_accuracy'] >= 60:
                message += "👍 Good work! You're improving!"
            else:
                message += "💪 Keep practicing! Every quiz helps you learn!"
            
            keyboard = [
                [InlineKeyboardButton("🎮 Take Quiz", callback_data="take_quiz")],
                [InlineKeyboardButton("📊 Quiz Analytics", callback_data="analytics_quizzes")],
                [InlineKeyboardButton("🔄 Refresh", callback_data="my_stats")]
            ]
            
            if user_obj.role in ['admin', 'super_admin']:
                keyboard.append([InlineKeyboardButton("📤 My Contributions", callback_data="my_contributions")])
            
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in my_stats_command: {e}")
        await update.message.reply_text("❌ Error loading personal stats.")

async def admin_dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin dashboard"""
    try:
        user = update.effective_user
        if _rate_limited(user.id):
            await update.message.reply_text("⏳ Slow down, please.")
            return
        
        # Check if user is admin or super_admin
        async for db in get_async_db():
            result = await db.execute(select(Admin).where(Admin.telegram_id == user.id))
            is_admin_user = result.scalar_one_or_none()
            
            if not is_admin_user:
                await update.message.reply_text("❌ Access denied. Admin privileges required.")
                return
        
        # Get dashboard data
        analytics_service = AnalyticsService()
        dashboard_data = analytics_service.get_admin_dashboard_data()
        
        if not dashboard_data:
            await update.message.reply_text("📊 No dashboard data available.")
            return
        
        # Format message
        message = "📊 **Admin Dashboard**\n\n"
        
        # System overview
        overview = dashboard_data['system_overview']
        message += "🏢 **System Overview:**\n"
        message += f"👥 Total Users: {overview['total_users']}\n"
        message += f"🎓 Students: {overview['total_students']}\n"
        message += f"👨‍💼 Admins: {overview['total_admins']}\n"
        message += f"🔧 Super Admins: {overview['total_super_admins']}\n\n"
        
        message += "📚 **Content:**\n"
        message += f"❓ Total Questions: {overview['total_questions']}\n"
        message += f"🏷️ Topics: {overview['total_topics']}\n"
        message += f"📖 Units: {overview['total_units']}\n"
        message += f"🎓 Courses: {overview['total_courses']}\n"
        message += f"🏫 Universities: {overview['total_universities']}\n\n"
        
        # Recent activity
        activity = dashboard_data['recent_activity']
        message += "📈 **This Week's Activity:**\n"
        message += f"🎮 Quiz Sessions: {activity['quiz_sessions_this_week']}\n"
        message += f"📤 New Uploads: {activity['uploads_this_week']}\n"
        message += f"🎯 Average Accuracy: {activity['average_quiz_accuracy']}%\n"
        message += f"🔥 Most Active Topic: {activity['most_active_topic']}\n\n"
        
        # Moderation
        moderation = dashboard_data['moderation']
        message += "🔍 **Moderation:**\n"
        message += f"⚠️ Pending Review: {moderation['questions_pending_review']}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔍 Moderation Queue", callback_data="moderation_queue")],
            [InlineKeyboardButton("📊 Quiz Analytics", callback_data="analytics_quizzes")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_dashboard")]
        ]
        
        if is_admin_user.is_super_admin:
            keyboard.append([InlineKeyboardButton("⚙️ System Status", callback_data="system_status")])
        
        keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin_dashboard_command: {e}")
        await update.message.reply_text("❌ Error loading admin dashboard.")

async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for super admin dashboard with condensed summary and quick actions."""
    user = update.effective_user
    # super admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            await update.message.reply_text("❌ Super admin only.")
            return
        # Quick aggregates (last 24h)
        result = await db.execute(select(func.count(QuizSession.id)))
        total_quizzes = result.scalar() or 0
        result = await db.execute(select(func.count(User.id)))
        total_users = result.scalar() or 0
        result = await db.execute(select(func.count(Question.id)))
        total_questions = result.scalar() or 0
    text = (
        "📊 BotCamp Medical — System Dashboard\n\n"
        "🩺 Health\n"
        "• Avg response: -\n"
        "• Cache hit: -\n"
        "• Pending jobs: -\n\n"
        "📈 Usage (overall)\n"
        f"• Quizzes: {total_quizzes}\n"
        f"• Users: {total_users}\n"
        f"• Questions: {total_questions}\n\n"
        "⚠️ Alerts\n"
        "• Use /alerts for active alerts\n"
    )
    keyboard = [
        [InlineKeyboardButton("View Health", callback_data="system_status")],
        [InlineKeyboardButton("Usage", callback_data="admin_system_stats")],
        [InlineKeyboardButton("Content Quality", callback_data="moderation_queue")],
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def export_questions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export questions CSV with optional filters: unit=..., topic=..., from=YYYY-MM-DD, to=YYYY-MM-DD"""
    user = update.effective_user
    # super admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            await update.message.reply_text("❌ Super admin only.")
            return
        # Parse simple filters
        args = (context.args or [])
        filters = {k: v for k,v in (a.split("=",1) for a in args if "=" in a)}
        query = select(Question)
        if filters.get("unit"):
            query = query.where(Question.unit == filters["unit"])
        if filters.get("topic"):
            query = query.where(Question.topic == filters["topic"])
        # date range on created_at
        from datetime import datetime
        fmt = "%Y-%m-%d"
        if filters.get("from"):
            try:
                dt_from = datetime.strptime(filters["from"], fmt)
                query = query.where(Question.created_at >= dt_from)
            except Exception:
                pass
        if filters.get("to"):
            try:
                dt_to = datetime.strptime(filters["to"], fmt)
                query = query.where(Question.created_at <= dt_to)
            except Exception:
                pass
        result = await db.execute(query)
        rows = result.scalars().all()
    # Build CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["question_id","university","course","year","unit","topic","question_text","option_a","option_b","option_c","option_d","correct_option","explanation","uploader_username","ai_confidence","created_at"])
    for q in rows:
        writer.writerow([
            q.question_id, getattr(q, 'university', None), getattr(q, 'course', None), getattr(q, 'year', None),
            q.unit, q.topic, q.question_text, q.option_a, q.option_b, q.option_c, q.option_d,
            getattr(q, 'correct_answer', getattr(q, 'correct_option', None)), q.explanation,
            getattr(q, 'uploader_username', None), getattr(q, 'moderation_score', None),
            getattr(q, 'created_at', None)
        ])
    output.seek(0)
    await update.message.reply_document(document=InputFile(io.BytesIO(output.getvalue().encode("utf-8")), filename="questions_export.csv"))

async def export_quiz_results_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export quiz results CSV with filters: topic_id=..., from=YYYY-MM-DD, to=YYYY-MM-DD"""
    user = update.effective_user
    # super admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            await update.message.reply_text("❌ Super admin only.")
            return
        # Filters
        args = (context.args or [])
        filters = {k: v for k,v in (a.split("=",1) for a in args if "=" in a)}
        query = select(QuizSession)
        if filters.get("topic_id") and filters["topic_id"].isdigit():
            query = query.where(QuizSession.topic_id == int(filters["topic_id"]))
        from datetime import datetime
        fmt = "%Y-%m-%d"
        if filters.get("from"):
            try:
                dt_from = datetime.strptime(filters["from"], fmt)
                query = query.where(QuizSession.started_at >= dt_from)
            except Exception:
                pass
        if filters.get("to"):
            try:
                dt_to = datetime.strptime(filters["to"], fmt)
                query = query.where(QuizSession.completed_at <= dt_to)
            except Exception:
                pass
        result = await db.execute(query)
        sessions = result.scalars().all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["session_id","user_id","topic_id","score_percentage","total_questions","correct_answers","started_at","completed_at"])
    for s in sessions:
        writer.writerow([s.id, s.user_id, s.topic_id, s.score_percentage, s.total_questions, s.correct_answers, s.started_at, s.completed_at])
    output.seek(0)
    await update.message.reply_document(document=InputFile(io.BytesIO(output.getvalue().encode("utf-8")), filename="quiz_results_export.csv"))

async def backup_now_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Trigger an immediate backup (super admin)."""
    user = update.effective_user
    # super admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id, Admin.is_super_admin == True))
        super_admin = result.scalar_one_or_none()
        if not super_admin:
            await update.message.reply_text("❌ Super admin only.")
            return
    svc = BackupExportService()
    res = svc.create_daily_backup()
    if res.get("success"):
        await update.message.reply_text(f"✅ {res.get('message')}")
    else:
        await update.message.reply_text(f"❌ Backup failed: {res.get('message')}")

async def request_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Allow a user to request admin access; notifies super admin for approval."""
    user = update.effective_user
    # Log request
    async for db in get_async_db():
        db.add(EventLog(user_id=user.id, event_type="admin_request", context={"username": user.username, "ts": datetime.utcnow().isoformat()}))
        await db.commit()
    # Notify super admin
    try:
        await context.bot.send_message(chat_id=DEFAULT_SUPER_ADMIN_ID, text=f"🔔 Admin access requested by @{user.username or user.id} (id: {user.id}). Use /approve_admin {user.id} or /reset_admin_code {user.id}.")
    except Exception:
        pass
    await update.message.reply_text("✅ Request sent to super admin. You'll receive a code once approved.")

async def set_admin_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """After approval via one-time code, an admin sets their permanent code: /set_admin_code <newcode>"""
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /set_admin_code <newcode>")
        return
    new_code = context.args[0].strip()
    if len(new_code) < 4:
        await update.message.reply_text("❌ Code too short. Use at least 4 characters.")
        return
    # Hash (do not store raw); notify super admin for audit
    hasher = SecurityService()
    hashed = hasher.hash_password(new_code)
    async for db in get_async_db():
        db.add(EventLog(user_id=user.id, event_type="admin_code_set", context={"hash": hashed, "ts": datetime.utcnow().isoformat()}))
        await db.commit()
    try:
        await context.bot.send_message(chat_id=DEFAULT_SUPER_ADMIN_ID, text=f"🔐 @{user.username or user.id} set a new admin code (hashed).")
    except Exception:
        pass
    await update.message.reply_text("✅ Admin code set. Keep it private. If forgotten, request a reset from super admin.")

async def redeem_admin_code_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User redeems a one-time admin access code: /redeem_admin_code <code>"""
    user = update.effective_user
    if not context.args:
        await update.message.reply_text("Usage: /redeem_admin_code <code>")
        return
    code = context.args[0].strip()
    role_service = RoleManagementService()
    result = role_service.verify_admin_access_code(code, user.id)
    if result.get("success"):
        await update.message.reply_text("✅ Admin privileges granted. Now set your permanent code using /set_admin_code <newcode>.")
    else:
        await update.message.reply_text(f"❌ {result.get('message','Invalid or expired code')}")

async def reprocess_upload_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/reprocess_upload <upload_id> — lock batch, rerun OCR/AI with fallback, store as draft items."""
    user = update.effective_user
    # only admins/super_admins
    if not await is_admin(user.id):
        await update.message.reply_text("❌ Admins only.")
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("Usage: /reprocess_upload <upload_id>")
        return
    upload_id = int(context.args[0])
    async for db in get_async_db():
        batch = await db.get(UploadBatch, upload_id)
        if not batch:
            await update.message.reply_text("❌ Upload batch not found.")
            return
        # Locking is simplified; set status to draft for reprocess
        new_items = 0
        for item in batch.items:
            raw = item.raw_text or ""
            if not raw:
                continue
            # parse via AI (fallback adapter used within ai_parser by env/flags)
            parsed = parse_mcqs_with_ai(raw)
            draft = UploadItem(batch_id=batch.id, raw_text=raw, parsed_json=parsed, status='draft')
            db.add(draft); new_items += 1
        await db.commit()
    await update.message.reply_text(f"✅ Reprocessed. Draft items added: {new_items}. Review in uploads UI.")

async def my_uploads_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show paginated list of the admin's uploads with basic stats."""
    user = update.effective_user
    # admins only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id))
        a = result.scalar_one_or_none()
        if not a:
            await update.message.reply_text("❌ Admins only.")
            return
        # Map telegram->user row
        result = await db.execute(select(User).where(User.telegram_id == user.id))
        u = result.scalar_one_or_none()
        if not u:
            await update.message.reply_text("❌ User record not found.")
            return
        # Stats
        total_uploaded = (await db.execute(select(func.count(Question.id)).where(Question.uploader_id == u.user_id))).scalar() or 0
        approved = (await db.execute(select(func.count(Question.id)).where(Question.uploader_id == u.user_id, Question.needs_review == False, Question.is_active == True))).scalar() or 0
        rejected = (await db.execute(select(func.count(Question.id)).where(Question.uploader_id == u.user_id, Question.is_active == False))).scalar() or 0
        flagged = (await db.execute(select(func.count(Question.id)).where(Question.uploader_id == u.user_id, Question.needs_review == True))).scalar() or 0
        # Page
        page = int(context.args[0]) if (context.args and context.args[0].isdigit()) else 1
        page_size = 10
        offset = (page - 1) * page_size
        result = await db.execute(
            select(Question).where(Question.uploader_id == u.user_id).order_by(Question.created_at.desc()).offset(offset).limit(page_size)
        )
        items = result.scalars().all()
    lines = [
        "📤 My Uploads",
        f"Total: {total_uploaded} | ✅ Approved: {approved} | ⚠️ Flagged: {flagged} | ❌ Rejected: {rejected}",
        "",
    ]
    for q in items:
        status = "✅" if (q.is_active and not q.needs_review) else ("⚠️" if q.needs_review else "❌")
        lines.append(f"{status} {q.unit or '-'} · {q.topic or '-'} · {q.created_at.strftime('%Y-%m-%d') if q.created_at else ''}")
        lines.append(f"— {q.question_text[:120]}" )
    keyboard = []
    if len(items) == page_size:
        keyboard.append([InlineKeyboardButton("Next ▶️", callback_data="admin_panel")])
    await update.message.reply_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard) if keyboard else None)

async def topic_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show topic stats: attempts, avg score, most-missed questions."""
    user = update.effective_user
    # admins only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id))
        a = result.scalar_one_or_none()
        if not a:
            await update.message.reply_text("❌ Admins only.")
            return
        if not context.args:
            await update.message.reply_text("Usage: /topic_stats <topic name>")
            return
        topic_name = " ".join(context.args)
        # Find topic
        result = await db.execute(select(Topic).where(Topic.name.ilike(topic_name)))
        topic = result.scalar_one_or_none()
        if not topic:
            await update.message.reply_text("Topic not found.")
            return
        # Attempts in last 7 days
        from datetime import datetime, timedelta
        since = datetime.utcnow() - timedelta(days=7)
        # Count attempts via answers on questions of the topic
        result = await db.execute(select(func.count()).select_from(Question).where(Question.topic_id == topic.id))
        total_questions = result.scalar() or 0
        # Approx attempts and most-missed are simplified (do full joins in models variant)
        attempts = "-"
        avg_score = "-"
    msg = (
        f"📊 Topic Stats — {topic_name}\n"
        f"Questions available: {total_questions}\n"
        f"Attempts (7d): {attempts}\n"
        f"Avg score (7d): {avg_score}\n"
        f"Most-missed: use /analytics_quizzes for detail"
    )
    await update.message.reply_text(msg)

async def review_next_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shortcut to open moderation queue for admins/super admins."""
    user = update.effective_user
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id))
        a = result.scalar_one_or_none()
        if not a:
            await update.message.reply_text("❌ Admins only.")
            return
    # Reuse moderation queue UI
    await moderation_queue_command(update, context)

async def system_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if _rate_limited(user.id):
        await update.message.reply_text("⏳ Slow down, please.")
        return
    # Admin only
    async for db in get_async_db():
        result = await db.execute(select(Admin).where(Admin.telegram_id == user.id))
        is_admin_user = result.scalar_one_or_none()
        if not is_admin_user:
            await update.message.reply_text("❌ Admins only.")
            return
    # Cache status
    cache_status = "Active (MemoryCache)"
    # DB connectivity
    db_ok = "OK"
    # Pending jobs placeholder (thread pool doesn't expose queue easily)
    pending_jobs = "-"
    failed_ocr = "-"
    avg_resp = "-"
    text = (
        "🩺 System Health\n"
        f"Cache: {cache_status}\n"
        f"DB Connection: {db_ok}\n"
        f"Pending Upload Jobs: {pending_jobs}\n"
        f"Failed OCR Tasks: {failed_ocr}\n"
        f"Average Response Time: {avg_resp}\n"
    )
    await update.message.reply_text(text)

_rate_limits = {}

def _rate_limited(user_id: int, limit: int = 5, window_s: int = 5) -> bool:
    now = time.time()
    window = _rate_limits.get(user_id) or []
    window = [t for t in window if now - t < window_s]
    if len(window) >= limit:
        _rate_limits[user_id] = window
        return True
    window.append(now)
    _rate_limits[user_id] = window
    return False

def _map_correct_option(correct: str, options: list) -> str:
    if not correct:
        return "A"
    letters = ["A","B","C","D","E"]
    # If letter provided
    if correct.strip().upper() in letters:
        return correct.strip().upper()[0]
    # Try match by text
    try:
        idx = [o.strip().lower() for o in options].index(correct.strip().lower())
        return letters[idx]
    except Exception:
        return "A"
