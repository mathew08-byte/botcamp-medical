"""
Admin Upload Handler for BotCamp Medical
Implements three-stage upload and review pipeline
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.ai_service import AIService
from services.user_service import UserService
from database.db import SessionLocal
from database.models import Question, AdminUpload, User
from typing import List, Dict, Any
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class AdminUploadHandler:
    def __init__(self):
        self.ai_service = AIService()
        self.user_service = UserService()
        self.upload_sessions = {}  # Store active upload sessions
    
    async def show_upload_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show upload type selection menu"""
        try:
            telegram_id = update.effective_user.id
            
            # Check if user is admin
            if not self.user_service.is_admin(telegram_id):
                await update.message.reply_text("❌ You do not have admin privileges.")
                return
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Text (paste questions)", callback_data="upload_text")],
                [InlineKeyboardButton("2️⃣ PDF File", callback_data="upload_pdf")],
                [InlineKeyboardButton("3️⃣ Image/Screenshot", callback_data="upload_image")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "📤 **Upload Questions**\n\n"
                "Please choose upload type:\n"
                "1️⃣ Text - Paste questions directly\n"
                "2️⃣ PDF - Upload PDF file for OCR\n"
                "3️⃣ Image - Upload screenshot/image for OCR",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in show_upload_menu: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_upload_type_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle upload type selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            upload_type = query.data.replace("upload_", "")
            
            # Initialize upload session
            self.upload_sessions[telegram_id] = {
                "type": upload_type,
                "stage": "waiting_for_file",
                "questions": [],
                "current_question": 0,
                "approved_questions": [],
                "upload_id": None
            }
            
            if upload_type == "text":
                await query.edit_message_text(
                    "📝 **Text Upload**\n\n"
                    "Please paste your questions in the following format:\n\n"
                    "1. Which of the following is a beta-lactam antibiotic?\n"
                    "A. Erythromycin\n"
                    "B. Amoxicillin\n"
                    "C. Ciprofloxacin\n"
                    "D. Gentamicin\n"
                    "Answer: B\n\n"
                    "You can paste multiple questions. When done, type /done",
                    parse_mode='Markdown'
                )
            elif upload_type == "pdf":
                await query.edit_message_text(
                    "📄 **PDF Upload**\n\n"
                    "Please upload a PDF file containing medical questions.\n"
                    "The bot will extract text using OCR and parse the questions automatically.",
                    parse_mode='Markdown'
                )
            elif upload_type == "image":
                await query.edit_message_text(
                    "🖼️ **Image Upload**\n\n"
                    "Please upload an image or screenshot containing medical questions.\n"
                    "The bot will extract text using OCR and parse the questions automatically.",
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error in handle_upload_type_selection: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_file_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle file uploads (PDF, images)"""
        try:
            telegram_id = update.effective_user.id
            
            if telegram_id not in self.upload_sessions:
                await update.message.reply_text("❌ No active upload session. Please start over.")
                return
            
            session = self.upload_sessions[telegram_id]
            
            if session["stage"] != "waiting_for_file":
                await update.message.reply_text("❌ Upload session not in correct state.")
                return
            
            # Get file
            if update.message.document:
                file = await context.bot.get_file(update.message.document.file_id)
            elif update.message.photo:
                # Get highest resolution photo
                file = await context.bot.get_file(update.message.photo[-1].file_id)
            else:
                await update.message.reply_text("❌ Please upload a valid file.")
                return
            
            # Download file
            file_data = await file.download_as_bytearray()
            
            # Show processing message
            processing_msg = await update.message.reply_text("🔄 Processing file... This may take a moment.")
            
            try:
                # Extract text using OCR
                if session["type"] in ["pdf", "image"]:
                    extracted_text = await self.ai_service.extract_text_from_image(file_data)
                    
                    if not extracted_text or "OCR service not available" in extracted_text:
                        await processing_msg.edit_text(
                            "❌ OCR service is not available. Please provide text input instead."
                        )
                        return
                    
                    # Parse questions from extracted text
                    questions = await self.ai_service.parse_questions_from_text(extracted_text)
                    
                    if not questions:
                        await processing_msg.edit_text(
                            "❌ No valid questions found in the uploaded file. Please try again with a clearer image or different format."
                        )
                        return
                    
                    session["questions"] = questions
                    session["stage"] = "review_questions"
                    
                    await processing_msg.edit_text(
                        f"✅ Successfully extracted {len(questions)} questions from the file.\n\n"
                        "Starting review process..."
                    )
                    
                    # Start question review
                    await self.start_question_review(update, context)
                    
                else:
                    await processing_msg.edit_text("❌ Invalid file type for this upload method.")
                    
            except Exception as e:
                logger.error(f"Error processing file: {e}")
                await processing_msg.edit_text(
                    "❌ Error processing file. Please try again or contact support."
                )
            
        except Exception as e:
            logger.error(f"Error in handle_file_upload: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_text_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle text upload"""
        try:
            telegram_id = update.effective_user.id
            
            if telegram_id not in self.upload_sessions:
                await update.message.reply_text("❌ No active upload session. Please start over.")
                return
            
            session = self.upload_sessions[telegram_id]
            
            if session["stage"] != "waiting_for_file":
                await update.message.reply_text("❌ Upload session not in correct state.")
                return
            
            text = update.message.text
            
            # Show processing message
            processing_msg = await update.message.reply_text("🔄 Processing text... This may take a moment.")
            
            try:
                # Parse questions from text
                questions = await self.ai_service.parse_questions_from_text(text)
                
                if not questions:
                    await processing_msg.edit_text(
                        "❌ No valid questions found in the text. Please check the format and try again."
                    )
                    return
                
                session["questions"] = questions
                session["stage"] = "review_questions"
                
                await processing_msg.edit_text(
                    f"✅ Successfully parsed {len(questions)} questions from the text.\n\n"
                    "Starting review process..."
                )
                
                # Start question review
                await self.start_question_review(update, context)
                
            except Exception as e:
                logger.error(f"Error processing text: {e}")
                await processing_msg.edit_text(
                    "❌ Error processing text. Please try again or contact support."
                )
            
        except Exception as e:
            logger.error(f"Error in handle_text_upload: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def start_question_review(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start the question review process"""
        try:
            telegram_id = update.effective_user.id
            session = self.upload_sessions[telegram_id]
            
            if not session["questions"]:
                await update.message.reply_text("❌ No questions to review.")
                return
            
            # Show first question
            await self.show_current_question(update, context)
            
        except Exception as e:
            logger.error(f"Error in start_question_review: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def show_current_question(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show current question for review"""
        try:
            telegram_id = update.effective_user.id
            session = self.upload_sessions[telegram_id]
            
            current_idx = session["current_question"]
            questions = session["questions"]
            
            if current_idx >= len(questions):
                # All questions reviewed, show summary
                await self.show_upload_summary(update, context)
                return
            
            question = questions[current_idx]
            
            question_text = f"""📝 **Question {current_idx + 1} of {len(questions)}**

**Question:**
{question['question_text']}

**Options:**
A. {question['options']['A']}
B. {question['options']['B']}
C. {question['options']['C']}
D. {question['options']['D']}

**AI suggests correct answer:** {question['correct_option']}
**Confidence:** {question.get('confidence', 0.0):.1%}"""

            if question.get('explanation'):
                question_text += f"\n\n**Explanation:**\n{question['explanation']}"
            
            keyboard = [
                [InlineKeyboardButton("✅ Confirm", callback_data="confirm_question")],
                [InlineKeyboardButton("✏️ Edit", callback_data="edit_question")],
                [InlineKeyboardButton("⏭️ Skip", callback_data="skip_question")],
                [InlineKeyboardButton("❌ Cancel Upload", callback_data="cancel_upload")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                question_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in show_current_question: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_question_review_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle question review actions (confirm, edit, skip)"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            session = self.upload_sessions[telegram_id]
            
            action = query.data
            
            if action == "confirm_question":
                # Add to approved questions
                current_question = session["questions"][session["current_question"]]
                session["approved_questions"].append(current_question)
                
                await query.edit_message_text("✅ Question confirmed!")
                
            elif action == "edit_question":
                # Set stage to editing
                session["stage"] = "editing_question"
                await query.edit_message_text(
                    "✏️ **Edit Question**\n\n"
                    "Please send the corrected question in the following format:\n\n"
                    "Question: [Your question text]\n"
                    "A. [Option A]\n"
                    "B. [Option B]\n"
                    "C. [Option C]\n"
                    "D. [Option D]\n"
                    "Answer: [A/B/C/D]\n"
                    "Explanation: [Optional explanation]",
                    parse_mode='Markdown'
                )
                return
                
            elif action == "skip_question":
                await query.edit_message_text("⏭️ Question skipped!")
                
            elif action == "cancel_upload":
                # Cancel upload session
                del self.upload_sessions[telegram_id]
                await query.edit_message_text("❌ Upload cancelled.")
                return
            
            # Move to next question
            session["current_question"] += 1
            
            # Show next question or summary
            if session["current_question"] < len(session["questions"]):
                await self.show_current_question(update, context)
            else:
                await self.show_upload_summary(update, context)
            
        except Exception as e:
            logger.error(f"Error in handle_question_review_action: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_upload_summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show upload summary and ask for final confirmation"""
        try:
            telegram_id = update.effective_user.id
            session = self.upload_sessions[telegram_id]
            
            approved_count = len(session["approved_questions"])
            total_count = len(session["questions"])
            
            summary_text = f"""📊 **Upload Summary**

**Total questions parsed:** {total_count}
**Questions approved:** {approved_count}
**Questions skipped:** {total_count - approved_count}

Ready to submit {approved_count} questions to the database?"""
            
            keyboard = [
                [InlineKeyboardButton("✅ Submit to Database", callback_data="submit_questions")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_upload")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                summary_text,
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in show_upload_summary: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def submit_questions_to_database(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Submit approved questions to database"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            session = self.upload_sessions[telegram_id]
            
            if not session["approved_questions"]:
                await query.edit_message_text("❌ No approved questions to submit.")
                return
            
            # Create admin upload record
            db = SessionLocal()
            try:
                admin_upload = AdminUpload(
                    uploader_id=telegram_id,
                    upload_type=session["type"],
                    status="approved",
                    ai_model="gemini",  # or detect from AI service
                    questions_detected=len(session["questions"]),
                    approved_questions=len(session["approved_questions"]),
                    created_at=datetime.utcnow()
                )
                db.add(admin_upload)
                db.commit()
                db.refresh(admin_upload)
                
                # Add questions to database
                questions_added = 0
                for question_data in session["approved_questions"]:
                    question = Question(
                        unit="General",  # Will be set by admin later
                        topic="General",
                        question_text=question_data["question_text"],
                        option_a=question_data["options"]["A"],
                        option_b=question_data["options"]["B"],
                        option_c=question_data["options"]["C"],
                        option_d=question_data["options"]["D"],
                        correct_option=question_data["correct_option"],
                        explanation=question_data.get("explanation", ""),
                        uploader_id=telegram_id,
                        is_active=True,
                        created_at=datetime.utcnow()
                    )
                    db.add(question)
                    questions_added += 1
                
                db.commit()
                
                # Update user stats
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    user.upload_count += questions_added
                    user.approved_count += questions_added
                    db.commit()
                
                # Clean up session
                del self.upload_sessions[telegram_id]
                
                await query.edit_message_text(
                    f"✅ **Upload Complete!**\n\n"
                    f"Successfully added {questions_added} questions to the database.\n"
                    f"Credit recorded under your account.\n\n"
                    f"Upload ID: {admin_upload.upload_id}",
                    parse_mode='Markdown'
                )
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error in submit_questions_to_database: {e}")
            await query.edit_message_text("❌ Error submitting questions. Please try again.")
    
    def cleanup_session(self, telegram_id: int):
        """Clean up upload session for a user"""
        if telegram_id in self.upload_sessions:
            del self.upload_sessions[telegram_id]
