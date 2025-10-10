"""
Admin Role Handlers for BotCamp Medical
Implements Part 4 - Admin role functionality with limited permissions
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User, Question, QuestionUpload, UploadBatch
from database.db_v2 import SessionLocal
from services.session_service import SessionService
from services.analytics_service import AnalyticsService
from services.multi_admin_service import MultiAdminService
from services.role_management_service import RoleManagementService

logger = logging.getLogger(__name__)

class AdminRoleHandlers:
    def __init__(self):
        self.session_service = SessionService()
        self.analytics_service = AnalyticsService()
        self.multi_admin_service = MultiAdminService()
        self.role_service = RoleManagementService()
    
    async def upload_question_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /upload_question command - Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                await update.message.reply_text("❌ Admin privileges required.")
                return
            
            message = """📤 **Upload Questions**

Please choose how you'd like to upload questions:"""
            
            keyboard = [
                [InlineKeyboardButton("📄 Text Upload", callback_data="admin_upload_text")],
                [InlineKeyboardButton("🖼️ Image Upload", callback_data="admin_upload_image")],
                [InlineKeyboardButton("📘 PDF Upload", callback_data="admin_upload_pdf")],
                [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_dashboard")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in upload_question_command: {e}")
            await update.message.reply_text("❌ Error accessing upload options.")
    
    async def review_uploads_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /review_uploads command - Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                await update.message.reply_text("❌ Admin privileges required.")
                return
            
            # Get available batches for review
            available_batches = self.multi_admin_service.get_available_batches_for_admin(user_id)
            
            if not available_batches:
                await update.message.reply_text(
                    "📋 **Review Uploads**\n\n"
                    "No uploads available for review at the moment.\n"
                    "Check back later or upload some questions yourself!"
                )
                return
            
            message = "📋 **Available Uploads for Review**\n\n"
            keyboard = []
            
            for i, batch in enumerate(available_batches[:10]):  # Show first 10
                status_emoji = "🔒" if batch['locked_by'] == user_id else "⏳"
                message += f"{status_emoji} **Batch {batch['batch_id']}**\n"
                message += f"• Uploader: {batch['uploader']}\n"
                message += f"• Questions: {batch['questions_count']}\n"
                message += f"• Status: {batch['status']}\n"
                message += f"• Created: {batch['created_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
                
                # Add action buttons
                if batch['locked_by'] == user_id or batch['locked_by'] is None:
                    keyboard.append([
                        InlineKeyboardButton(f"👁️ Review {batch['batch_id']}", callback_data=f"review_batch_{batch['batch_id']}"),
                        InlineKeyboardButton(f"✅ Approve {batch['batch_id']}", callback_data=f"approve_batch_{batch['batch_id']}"),
                        InlineKeyboardButton(f"❌ Reject {batch['batch_id']}", callback_data=f"reject_batch_{batch['batch_id']}")
                    ])
            
            if len(available_batches) > 10:
                message += f"... and {len(available_batches) - 10} more batches available."
            
            keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_review_uploads")])
            keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_dashboard")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in review_uploads_command: {e}")
            await update.message.reply_text("❌ Error retrieving uploads for review.")
    
    async def view_my_uploads_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_my_uploads command - Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                await update.message.reply_text("❌ Admin privileges required.")
                return
            
            # Get admin's own uploads
            admin_batches = self.multi_admin_service.get_admin_own_batches(user_id)
            
            if not admin_batches:
                await update.message.reply_text(
                    "📤 **My Uploads**\n\n"
                    "You haven't uploaded any questions yet.\n"
                    "Use the upload function to add questions to the system!"
                )
                return
            
            message = "📤 **My Uploads**\n\n"
            keyboard = []
            
            for batch in admin_batches[:10]:  # Show first 10
                status_emoji = {
                    "draft": "📝",
                    "review": "👁️",
                    "approved": "✅",
                    "rejected": "❌"
                }.get(batch['status'], "❓")
                
                message += f"{status_emoji} **Batch {batch['batch_id']}**\n"
                message += f"• Questions: {batch['questions_count']}\n"
                message += f"• Status: {batch['status'].title()}\n"
                message += f"• Created: {batch['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                if batch['completed_at']:
                    message += f"• Completed: {batch['completed_at'].strftime('%Y-%m-%d %H:%M')}\n"
                message += "\n"
                
                # Add action buttons for draft/review status
                if batch['status'] in ['draft', 'review']:
                    keyboard.append([
                        InlineKeyboardButton(f"✏️ Edit {batch['batch_id']}", callback_data=f"edit_batch_{batch['batch_id']}"),
                        InlineKeyboardButton(f"🗑️ Delete {batch['batch_id']}", callback_data=f"delete_batch_{batch['batch_id']}")
                    ])
            
            if len(admin_batches) > 10:
                message += f"... and {len(admin_batches) - 10} more uploads."
            
            keyboard.append([InlineKeyboardButton("🔄 Refresh", callback_data="admin_my_uploads")])
            keyboard.append([InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_dashboard")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in view_my_uploads_command: {e}")
            await update.message.reply_text("❌ Error retrieving your uploads.")
    
    async def view_unit_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_unit_stats command - Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                await update.message.reply_text("❌ Admin privileges required.")
                return
            
            # Get admin's scope
            admin_scope = self.multi_admin_service.get_admin_scope(user_id)
            
            if not admin_scope:
                await update.message.reply_text(
                    "📊 **Unit Statistics**\n\n"
                    "No scope assigned. Contact a super admin to set your university/course scope."
                )
                return
            
            # Get analytics for the admin's scope
            analytics = self.analytics_service.get_quiz_analytics(
                topic_id=None,  # Get all topics in scope
                days_back=30
            )
            
            message = f"""📊 **Unit Statistics**

**Scope:** {admin_scope['university']} - {admin_scope['course']}

**📈 Overall Performance:**
• Total Questions: {analytics.get('total_questions', 0)}
• Total Quiz Attempts: {analytics.get('total_quizzes', 0)}
• Average Accuracy: {analytics.get('accuracy_rate', 0):.1f}%
• Active Students: {analytics.get('active_users', 0)}

**📚 Topic Performance:**"""
            
            # Add topic breakdown
            if analytics.get('topic_performance'):
                for topic, performance in list(analytics['topic_performance'].items())[:5]:
                    message += f"\n• **{topic}:** {performance['accuracy']:.1f}% ({performance['questions']} questions)"
            
            # Add most missed questions
            if analytics.get('most_missed_questions'):
                message += "\n\n**❌ Most Missed Questions:**"
                for question in analytics['most_missed_questions'][:3]:
                    message += f"\n• Q{question['question_id']}: {question['miss_rate']:.1f}% miss rate"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="admin_unit_stats")],
                [InlineKeyboardButton("🔙 Back to Dashboard", callback_data="admin_dashboard")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in view_unit_stats_command: {e}")
            await update.message.reply_text("❌ Error retrieving unit statistics.")
    
    async def admin_dashboard_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin dashboard callbacks"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            callback_data = query.data
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                await query.edit_message_text("❌ Admin privileges required.")
                return
            
            if callback_data == "admin_upload":
                await self.upload_question_command(update, context)
            elif callback_data == "admin_review":
                await self.review_uploads_command(update, context)
            elif callback_data == "admin_stats":
                await self.view_unit_stats_command(update, context)
            elif callback_data == "admin_my_uploads":
                await self.view_my_uploads_command(update, context)
            elif callback_data.startswith("review_batch_"):
                await self._handle_batch_review(query, callback_data)
            elif callback_data.startswith("approve_batch_"):
                await self._handle_batch_approval(query, callback_data)
            elif callback_data.startswith("reject_batch_"):
                await self._handle_batch_rejection(query, callback_data)
            elif callback_data.startswith("edit_batch_"):
                await self._handle_batch_edit(query, callback_data)
            elif callback_data.startswith("delete_batch_"):
                await self._handle_batch_deletion(query, callback_data)
                
        except Exception as e:
            logger.error(f"Error in admin_dashboard_handler: {e}")
    
    async def _handle_batch_review(self, query, callback_data: str):
        """Handle batch review action"""
        try:
            batch_id = int(callback_data.split("_")[2])
            user_id = query.from_user.id
            
            # Lock batch for review
            result = self.multi_admin_service.lock_batch_for_review(batch_id, user_id)
            
            if result['success']:
                await query.edit_message_text(
                    f"✅ {result['message']}\n\n"
                    f"Batch {batch_id} is now locked for your review. "
                    f"You can now examine the questions and approve or reject them."
                )
            else:
                await query.edit_message_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error handling batch review: {e}")
    
    async def _handle_batch_approval(self, query, callback_data: str):
        """Handle batch approval"""
        try:
            batch_id = int(callback_data.split("_")[2])
            user_id = query.from_user.id
            
            # Approve batch
            result = self.multi_admin_service.approve_batch(batch_id, user_id)
            
            if result['success']:
                await query.edit_message_text(f"✅ {result['message']}")
            else:
                await query.edit_message_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error handling batch approval: {e}")
    
    async def _handle_batch_rejection(self, query, callback_data: str):
        """Handle batch rejection"""
        try:
            batch_id = int(callback_data.split("_")[2])
            user_id = query.from_user.id
            
            # Reject batch
            result = self.multi_admin_service.reject_batch(batch_id, user_id, "Rejected by admin")
            
            if result['success']:
                await query.edit_message_text(f"✅ {result['message']}")
            else:
                await query.edit_message_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error handling batch rejection: {e}")
    
    async def _handle_batch_edit(self, query, callback_data: str):
        """Handle batch editing"""
        try:
            batch_id = int(callback_data.split("_")[2])
            
            await query.edit_message_text(
                f"✏️ **Edit Batch {batch_id}**\n\n"
                f"Batch editing functionality will be implemented in the next version.\n"
                f"For now, you can delete and re-upload the batch."
            )
            
        except Exception as e:
            logger.error(f"Error handling batch edit: {e}")
    
    async def _handle_batch_deletion(self, query, callback_data: str):
        """Handle batch deletion"""
        try:
            batch_id = int(callback_data.split("_")[2])
            user_id = query.from_user.id
            
            # Confirm deletion
            await query.edit_message_text(
                f"🗑️ **Delete Batch {batch_id}**\n\n"
                f"Are you sure you want to delete this batch?\n"
                f"This action cannot be undone.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Yes, Delete", callback_data=f"confirm_delete_{batch_id}")],
                    [InlineKeyboardButton("❌ Cancel", callback_data="admin_my_uploads")]
                ])
            )
            
        except Exception as e:
            logger.error(f"Error handling batch deletion: {e}")
    
    async def handle_upload_type_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle upload type selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            callback_data = query.data
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                await query.edit_message_text("❌ Admin privileges required.")
                return
            
            if callback_data == "admin_upload_text":
                await query.edit_message_text(
                    "📄 **Text Upload**\n\n"
                    "Please send your questions in the following format:\n\n"
                    "**Question:** [Your question here]\n"
                    "**A)** [Option A]\n"
                    "**B)** [Option B]\n"
                    "**C)** [Option C]\n"
                    "**D)** [Option D]\n"
                    "**Correct:** [A/B/C/D]\n"
                    "**Explanation:** [Explanation here]\n\n"
                    "Send multiple questions separated by '---'"
                )
                context.user_data['awaiting_text_upload'] = True
                
            elif callback_data == "admin_upload_image":
                await query.edit_message_text(
                    "🖼️ **Image Upload**\n\n"
                    "Please send an image containing questions.\n"
                    "The AI will extract and process the questions automatically.\n\n"
                    "Supported formats: JPG, PNG, PDF"
                )
                context.user_data['awaiting_image_upload'] = True
                
            elif callback_data == "admin_upload_pdf":
                await query.edit_message_text(
                    "📘 **PDF Upload**\n\n"
                    "Please send a PDF file containing questions.\n"
                    "The AI will extract and process the questions automatically.\n\n"
                    "Make sure the PDF is clear and readable."
                )
                context.user_data['awaiting_pdf_upload'] = True
                
        except Exception as e:
            logger.error(f"Error handling upload type selection: {e}")
    
    async def handle_upload_content(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle uploaded content (text, image, PDF)"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin
            if self.role_service.get_user_role(user_id) != "admin":
                return
            
            # Handle text upload
            if context.user_data.get('awaiting_text_upload'):
                await self._process_text_upload(update, context)
                context.user_data.pop('awaiting_text_upload', None)
                
            # Handle image upload
            elif context.user_data.get('awaiting_image_upload'):
                await self._process_image_upload(update, context)
                context.user_data.pop('awaiting_image_upload', None)
                
            # Handle PDF upload
            elif context.user_data.get('awaiting_pdf_upload'):
                await self._process_pdf_upload(update, context)
                context.user_data.pop('awaiting_pdf_upload', None)
                
        except Exception as e:
            logger.error(f"Error handling upload content: {e}")
    
    async def _process_text_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process text upload"""
        try:
            text = update.message.text
            user_id = update.effective_user.id
            
            # Create upload batch
            batch_id = self.multi_admin_service.create_upload_batch(user_id, 0)
            
            if not batch_id:
                await update.message.reply_text("❌ Error creating upload batch.")
                return
            
            # Process the text (simplified for now)
            questions = self._parse_text_questions(text)
            
            if not questions:
                await update.message.reply_text(
                    "❌ No valid questions found in the text.\n"
                    "Please check the format and try again."
                )
                return
            
            # Update batch with question count
            session = SessionLocal()
            try:
                batch = session.query(UploadBatch).filter(UploadBatch.batch_id == batch_id).first()
                if batch:
                    batch.questions_count = len(questions)
                    session.commit()
            finally:
                session.close()
            
            await update.message.reply_text(
                f"✅ **Text Upload Processed**\n\n"
                f"**Batch ID:** {batch_id}\n"
                f"**Questions Found:** {len(questions)}\n"
                f"**Status:** Pending Review\n\n"
                f"The questions have been queued for review. "
                f"You can check their status in 'My Uploads'."
            )
            
        except Exception as e:
            logger.error(f"Error processing text upload: {e}")
            await update.message.reply_text("❌ Error processing text upload.")
    
    async def _process_image_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process image upload"""
        try:
            # This would integrate with OCR/AI processing
            await update.message.reply_text(
                "🖼️ **Image Upload Received**\n\n"
                "Image processing with AI/OCR will be implemented in the next version.\n"
                "For now, please use text upload format."
            )
            
        except Exception as e:
            logger.error(f"Error processing image upload: {e}")
    
    async def _process_pdf_upload(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Process PDF upload"""
        try:
            # This would integrate with PDF processing
            await update.message.reply_text(
                "📘 **PDF Upload Received**\n\n"
                "PDF processing with AI will be implemented in the next version.\n"
                "For now, please use text upload format."
            )
            
        except Exception as e:
            logger.error(f"Error processing PDF upload: {e}")
    
    def _parse_text_questions(self, text: str) -> list:
        """Parse text to extract questions (simplified implementation)"""
        try:
            # This is a simplified parser - in production, you'd want more robust parsing
            questions = []
            question_blocks = text.split('---')
            
            for block in question_blocks:
                block = block.strip()
                if not block:
                    continue
                
                lines = [line.strip() for line in block.split('\n') if line.strip()]
                
                if len(lines) >= 6:  # Minimum required lines
                    question_data = {
                        'question': lines[0].replace('**Question:**', '').strip(),
                        'options': [
                            lines[1].replace('**A)**', '').strip(),
                            lines[2].replace('**B)**', '').strip(),
                            lines[3].replace('**C)**', '').strip(),
                            lines[4].replace('**D)**', '').strip()
                        ],
                        'correct_answer': lines[5].replace('**Correct:**', '').strip(),
                        'explanation': lines[6].replace('**Explanation:**', '').strip() if len(lines) > 6 else ''
                    }
                    
                    # Validate question data
                    if (question_data['question'] and 
                        len(question_data['options']) == 4 and
                        question_data['correct_answer'] in ['A', 'B', 'C', 'D']):
                        questions.append(question_data)
            
            return questions
            
        except Exception as e:
            logger.error(f"Error parsing text questions: {e}")
            return []