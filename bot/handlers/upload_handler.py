"""
Upload handler for AI-powered question uploading system.
"""
import os
import tempfile
from datetime import datetime
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.db_v2 import SessionLocal
from models import User, University, Course, Unit, Topic, Question
from bot.services.ai_service import AIService
from bot.utils.formatters import format_question_preview
from services.moderation import moderate_question_with_ai
from services.analytics_service import AnalyticsService
import logging

logger = logging.getLogger(__name__)


class UploadHandler:
    def __init__(self):
        self.ai_service = AIService()
        self.analytics_service = AnalyticsService()
    
    async def start_upload_process(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the upload process by asking for upload type."""
        query = update.callback_query
        if query:
            await query.answer()
        
        keyboard = [
            [InlineKeyboardButton("📝 Paste Text Manually", callback_data="upload_text")],
            [InlineKeyboardButton("📄 Upload PDF File", callback_data="upload_pdf")],
            [InlineKeyboardButton("🖼️ Upload Image/Screenshot", callback_data="upload_image")],
            [InlineKeyboardButton("🔙 Back to Main Menu", callback_data="main_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = """📤 **How do you want to upload questions?**

Choose your upload method:

1️⃣ **Paste Text Manually** - Copy and paste MCQs directly
2️⃣ **Upload PDF File** - Upload a PDF document with questions  
3️⃣ **Upload Image/Screenshot** - Upload images of questions

The AI will extract and structure the questions for you!"""
        
        if query:
            await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_upload_type_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle upload type selection."""
        query = update.callback_query
        await query.answer()
        
        upload_type = query.data.replace("upload_", "")
        
        if upload_type == "text":
            await self._request_text_upload(update, context)
        elif upload_type == "pdf":
            await self._request_pdf_upload(update, context)
        elif upload_type == "image":
            await self._request_image_upload(update, context)
    
    async def _request_text_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request text upload from user."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="upload_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = """📝 **Paste Your Questions**

Please paste the multiple choice questions you want to upload. You can include:

• Question text
• Options A, B, C, D
• Correct answers (marked with *, bold, or similar)
• Explanations (optional)
• Source information (optional)

Example:
```
Q1. What is the main neurotransmitter in the sympathetic nervous system?
A) Acetylcholine
B) Noradrenaline *
C) Dopamine  
D) Serotonin
Explanation: Noradrenaline is the primary neurotransmitter...
Source: CAT 1 2022
```

Paste your questions below:"""
        
        query = update.callback_query
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Set context to expect text input
        context.user_data['upload_mode'] = 'text'
        context.user_data['upload_step'] = 'waiting_for_text'
    
    async def _request_pdf_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request PDF upload from user."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="upload_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = """📄 **Upload PDF File**

Please upload a PDF file containing multiple choice questions.

**Supported formats:**
• PDF documents with text-based questions
• Scanned PDFs (OCR will be applied)

**Tips for best results:**
• Ensure text is clear and readable
• Questions should be properly formatted
• Include question numbers and options A-D

Upload your PDF file now:"""
        
        query = update.callback_query
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Set context to expect PDF upload
        context.user_data['upload_mode'] = 'pdf'
        context.user_data['upload_step'] = 'waiting_for_pdf'
    
    async def _request_image_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Request image upload from user."""
        keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="upload_questions")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message_text = """🖼️ **Upload Image/Screenshot**

Please upload one or more images containing multiple choice questions.

**Supported formats:**
• JPG, PNG, JPEG images
• Screenshots of questions
• Photos of printed questions

**Tips for best results:**
• Ensure text is clear and readable
• Good lighting and contrast
• Questions should be properly formatted
• Include question numbers and options A-D

Upload your image(s) now:"""
        
        query = update.callback_query
        await query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        
        # Set context to expect image upload
        context.user_data['upload_mode'] = 'image'
        context.user_data['upload_step'] = 'waiting_for_image'
    
    async def handle_text_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text upload from user."""
        upload_step = context.user_data.get('upload_step')
        if not upload_step:
            return
        
        # Branch: editing a single question during review
        if upload_step == 'editing_question':
            await self._handle_edit_text(update, context)
            return

        # Branch: metadata collection flow
        if upload_step in ('metadata_unit', 'metadata_topic'):
            await self._handle_metadata_text(update, context)
            return

        if upload_step != 'waiting_for_text':
            return

        text = update.message.text
        
        # Show processing message
        processing_msg = await update.message.reply_text("🤖 Processing text with AI... Please wait.")
        
        try:
            # Parse questions using AI
            questions = self.ai_service.parse_mcqs_with_ai(text)
            
            if not questions or any('error' in q for q in questions):
                error_msg = "❌ Failed to extract questions from text. Please check the format and try again."
                if questions and 'error' in questions[0]:
                    error_msg += f"\n\nError: {questions[0]['error']}"
                
                await processing_msg.edit_text(error_msg)
                return
            
            # Store questions in context
            context.user_data['extracted_questions'] = questions
            context.user_data['upload_step'] = 'questions_extracted'
            
            # Show extraction results
            await self._show_extraction_results(update, context, questions)
            
        except Exception as e:
            logger.error(f"Error processing text upload: {e}")
            await processing_msg.edit_text(f"❌ Error processing text: {str(e)}")
        finally:
            await processing_msg.delete()
    
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file upload (PDF or image)."""
        upload_step = context.user_data.get('upload_step')
        if upload_step not in ['waiting_for_pdf', 'waiting_for_image']:
            return
        
        upload_mode = context.user_data.get('upload_mode')
        
        # Show processing message
        processing_msg = await update.message.reply_text("🤖 Processing file with AI... Please wait.")
        
        try:
            # Download file
            file = await context.bot.get_file(update.message.document.file_id)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{upload_mode}") as temp_file:
                await file.download_to_drive(temp_file.name)
                temp_path = temp_file.name
            
            try:
                # Extract text based on file type
                if upload_mode == 'pdf':
                    extracted_text = self.ai_service.extract_text_from_pdf(temp_path)
                elif upload_mode == 'image':
                    extracted_text = self.ai_service.extract_text_from_image(temp_path)
                else:
                    extracted_text = "Unsupported file type"
                
                if extracted_text.startswith("Error"):
                    await processing_msg.edit_text(f"❌ {extracted_text}")
                    return
                
                # Parse questions using AI
                questions = self.ai_service.parse_mcqs_with_ai(extracted_text)
                
                if not questions or any('error' in q for q in questions):
                    error_msg = "❌ Failed to extract questions from file. Please check the file format and try again."
                    if questions and 'error' in questions[0]:
                        error_msg += f"\n\nError: {questions[0]['error']}"
                    
                    await processing_msg.edit_text(error_msg)
                    return
                
                # Store questions in context
                context.user_data['extracted_questions'] = questions
                context.user_data['upload_step'] = 'questions_extracted'
                
                # Show extraction results
                await self._show_extraction_results(update, context, questions)
                
            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
                
        except Exception as e:
            logger.error(f"Error processing file upload: {e}")
            await processing_msg.edit_text(f"❌ Error processing file: {str(e)}")
        finally:
            await processing_msg.delete()
    
    async def _show_extraction_results(self, update: Update, context: ContextTypes.DEFAULT_TYPE, questions: List[Dict]):
        """Show AI extraction results to user."""
        confidence = self.ai_service.get_ai_confidence(questions)
        
        message_text = f"""🤖 **AI Extraction Results**

**Confidence Level:** {confidence}
**Questions Found:** {len(questions)}

Here's what I extracted:"""
        
        # Show first few questions as preview
        for i, question in enumerate(questions[:3]):  # Show first 3 questions
            message_text += f"\n\n**Q{i+1}:** {question['question']}"
            for j, option in enumerate(question['options']):
                letter = chr(65 + j)  # A, B, C, D
                marker = " ✅" if letter == question['correct_answer'] else ""
                message_text += f"\n{letter}) {option}{marker}"
            
            if question.get('explanation'):
                message_text += f"\n💡 {question['explanation'][:100]}..."
        
        if len(questions) > 3:
            message_text += f"\n\n... and {len(questions) - 3} more questions"
        
        keyboard = [
            [InlineKeyboardButton("✅ Review & Upload", callback_data="review_questions")],
            [InlineKeyboardButton("🔙 Start Over", callback_data="upload_questions")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def start_question_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the question review process."""
        query = update.callback_query
        await query.answer()
        
        questions = context.user_data.get('extracted_questions', [])
        if not questions:
            await query.edit_message_text("❌ No questions to review.")
            return
        
        # Initialize review state
        context.user_data['review_index'] = 0
        context.user_data['approved_questions'] = []
        context.user_data['upload_step'] = 'reviewing_questions'
        
        # Show first question for review
        await self._show_question_for_review(update, context)
    
    async def _show_question_for_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show a question for review."""
        questions = context.user_data.get('extracted_questions', [])
        review_index = context.user_data.get('review_index', 0)
        
        if review_index >= len(questions):
            # All questions reviewed, proceed to metadata selection
            await self._start_metadata_selection(update, context)
            return
        
        question = questions[review_index]
        
        # Format question for display
        message_text = f"""📝 **Question {review_index + 1} of {len(questions)}**

**Question:** {question['question']}

**Options:**
A) {question['options'][0]}
B) {question['options'][1]}
C) {question['options'][2]}
D) {question['options'][3]}

**Correct Answer:** {question['correct_answer']}"""
        
        if question.get('explanation'):
            message_text += f"\n\n**Explanation:** {question['explanation']}"
        
        if question.get('source'):
            message_text += f"\n\n**Source:** {question['source']}"
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data="approve_question"),
                InlineKeyboardButton("✏️ Edit", callback_data="edit_question")
            ],
            [
                InlineKeyboardButton("❌ Reject", callback_data="reject_question"),
                InlineKeyboardButton("⏭️ Skip", callback_data="skip_question")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    async def handle_question_review_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle question review actions (approve, edit, reject, skip)."""
        query = update.callback_query
        await query.answer()
        
        action = query.data.replace("_question", "")
        questions = context.user_data.get('extracted_questions', [])
        review_index = context.user_data.get('review_index', 0)
        approved_questions = context.user_data.get('approved_questions', [])
        
        if review_index >= len(questions):
            return
        
        current_question = questions[review_index]
        
        if action == "approve":
            approved_questions.append(current_question)
            context.user_data['approved_questions'] = approved_questions
        elif action == "reject":
            # Question is rejected, don't add to approved list
            pass
        elif action == "skip":
            # Question is skipped, don't add to approved list
            pass
        elif action == "edit":
            # Enter editing mode and prompt for corrected content
            context.user_data['upload_step'] = 'editing_question'
            context.user_data['editing_index'] = review_index
            await query.edit_message_text(
                "✏️ Send the corrected question in this format:\n\n"
                "Question: <text>\n"
                "A. <option A>\nB. <option B>\nC. <option C>\nD. <option D>\n"
                "Answer: <A/B/C/D>\n"
                "Explanation: <optional>"
            )
            return
        
        # Move to next question
        context.user_data['review_index'] = review_index + 1
        await self._show_question_for_review(update, context)
    
    async def _start_metadata_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start metadata selection process (simple text prompts for unit/topic)."""
        approved_questions = context.user_data.get('approved_questions', [])
        
        if not approved_questions:
            await update.callback_query.edit_message_text(
                "❌ No questions were approved for upload.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Start Over", callback_data="upload_questions")]])
            )
            return
        
        context.user_data['metadata'] = {}
        context.user_data['upload_step'] = 'metadata_unit'
        await update.callback_query.edit_message_text(
            "📋 Enter Unit name (e.g., Physiology)")
    
    async def final_upload_questions(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Perform the final upload of approved questions."""
        query = update.callback_query
        await query.answer()
        
        approved_questions = context.user_data.get('approved_questions', [])
        if not approved_questions:
            await query.edit_message_text("❌ No questions to upload.")
            return
        
        # Show uploading message
        await query.edit_message_text("📤 Uploading questions to database... Please wait.")
        
        try:
            # Get user info
            user = await self._get_or_create_user(update.effective_user)
            
            # Upload questions to database with metadata
            metadata = context.user_data.get('metadata', {})
            uploaded_count = await self._upload_questions_to_db(approved_questions, user, metadata)
            
            # Show success message
            success_message = f"""✅ **Upload Complete!**

**Successfully uploaded:** {uploaded_count} questions
**Uploader:** @{update.effective_user.username or update.effective_user.first_name}

🤖 **AI Moderation:** All questions have been automatically reviewed by AI
📊 **Status:** Questions are now available for students to practice! 🎉

💡 **Note:** Some questions may require additional review by super admins."""
            
            keyboard = [
                [InlineKeyboardButton("📤 Upload More", callback_data="upload_questions")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(success_message, reply_markup=reply_markup, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error uploading questions: {e}")
            await query.edit_message_text(f"❌ Error uploading questions: {str(e)}")
        
        # Clear upload context
        self._clear_upload_context(context)
    
    async def _get_or_create_user(self, telegram_user) -> User:
        """Get or create user in database."""
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(telegram_id=telegram_user.id).first()
            if not user:
                user = User(
                    telegram_id=telegram_user.id,
                    username=telegram_user.username,
                    first_name=telegram_user.first_name,
                    last_name=telegram_user.last_name,
                    role="admin"  # Assuming uploader is admin
                )
                db.add(user)
                db.commit()
                db.refresh(user)
            return user
        finally:
            db.close()
    
    async def _upload_questions_to_db(self, questions: List[Dict], user: User, metadata: Optional[Dict] = None) -> int:
        """Upload questions to database with AI moderation."""
        db = SessionLocal()
        uploaded_count = 0
        moderated_count = 0
        
        try:
            for question_data in questions:
                # Run AI moderation on the question
                moderation_result = moderate_question_with_ai(question_data)
                
                # Create question record
                question = Question(
                    question_text=question_data['question'],
                    option_a=question_data['options'][0],
                    option_b=question_data['options'][1],
                    option_c=question_data['options'][2],
                    option_d=question_data['options'][3],
                    correct_option=question_data['correct_answer'],
                    explanation=question_data.get('explanation', ''),
                    uploader_id=user.user_id,
                    uploader_username=user.username,
                    source=question_data.get('source', ''),
                    is_active=True,
                    unit=(metadata or {}).get('unit'),
                    topic=(metadata or {}).get('topic'),
                    created_at=datetime.utcnow(),
                    # AI moderation fields
                    moderation_score=moderation_result.get('moderation_score', 0),
                    moderation_comments=moderation_result.get('moderation_comments', ''),
                    moderated_by_ai=True
                )
                
                # Set moderation status based on AI decision
                action = moderation_result.get('action', 'flag')
                if action == 'accept':
                    question.needs_review = False
                elif action == 'reject':
                    question.is_active = False
                    question.needs_review = False
                else:  # flag
                    question.needs_review = True
                
                db.add(question)
                db.flush()  # Get the question ID
                
                # Update contributor stats
                self.analytics_service.update_contributor_stats(user.user_id, question.question_id, action)
                
                uploaded_count += 1
                if moderation_result.get('moderation_score', 0) > 0:
                    moderated_count += 1
            
            db.commit()
            
            # Update user upload count
            user.upload_count = (user.upload_count or 0) + uploaded_count
            db.commit()
            
            logger.info(f"Uploaded {uploaded_count} questions, {moderated_count} moderated by AI")
            return uploaded_count
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error uploading questions: {e}")
            raise e
        finally:
            db.close()
    
    def _clear_upload_context(self, context: ContextTypes.DEFAULT_TYPE):
        """Clear upload-related context data."""
        keys_to_remove = [
            'upload_mode', 'upload_step', 'extracted_questions', 
            'review_index', 'approved_questions', 'editing_index',
            'metadata', 'selected_unit', 'selected_topic'
        ]
        
        for key in keys_to_remove:
            context.user_data.pop(key, None)

    async def _handle_edit_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Parse edited question text and update the current question."""
        raw = update.message.text or ""
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        question_text = ""
        options = {"A": "", "B": "", "C": "", "D": ""}
        correct = ""
        explanation = ""
        for l in lines:
            if l.lower().startswith("question:"):
                question_text = l.split(":", 1)[1].strip()
            elif l[:2].upper() in ("A.", "B.", "C.", "D."):
                key = l[0].upper()
                options[key] = l[2:].strip()
            elif l.lower().startswith("answer:"):
                val = l.split(":", 1)[1].strip().upper()
                if val in ("A", "B", "C", "D"):
                    correct = val
            elif l.lower().startswith("explanation:"):
                explanation = l.split(":", 1)[1].strip()
        if not (question_text and all(options.values()) and correct in ("A","B","C","D")):
            await update.message.reply_text("❌ Could not parse edit. Please follow the requested format.")
            return
        questions = context.user_data.get('extracted_questions', [])
        idx = context.user_data.get('editing_index', context.user_data.get('review_index', 0))
        if 0 <= idx < len(questions):
            # Normalize to the same schema used earlier (list of simple dicts)
            questions[idx] = {
                'question': question_text,
                'options': [options['A'], options['B'], options['C'], options['D']],
                'correct_answer': correct,
                'explanation': explanation,
            }
            context.user_data['extracted_questions'] = questions
        # Exit editing mode and resume review
        context.user_data['upload_step'] = 'reviewing_questions'
        # Add directly to approved list after edit
        approved = context.user_data.get('approved_questions', [])
        approved.append(questions[idx])
        context.user_data['approved_questions'] = approved
        # Advance index and show next
        context.user_data['review_index'] = idx + 1
        await self._show_question_for_review(update, context)

    async def _handle_metadata_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Collect simple metadata: unit then topic via text prompts."""
        step = context.user_data.get('upload_step')
        md = context.user_data.get('metadata', {})
        if step == 'metadata_unit':
            md['unit'] = (update.message.text or '').strip()
            context.user_data['metadata'] = md
            context.user_data['upload_step'] = 'metadata_topic'
            await update.message.reply_text("📖 Enter Topic name (e.g., Cardiovascular System)")
            return
        if step == 'metadata_topic':
            md['topic'] = (update.message.text or '').strip()
            context.user_data['metadata'] = md
            # Show final confirm button
            keyboard = [[InlineKeyboardButton("✅ Upload Questions", callback_data="final_upload")]]
            await update.message.reply_text(
                f"✅ Metadata set:\nUnit: {md.get('unit','-')}\nTopic: {md.get('topic','-')}",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
