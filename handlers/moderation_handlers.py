"""
Moderation handlers for Step 5 - AI Moderation, Analytics & Dashboards
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import Question, User
from database.db_v2 import SessionLocal
from services.moderation import moderate_question_with_ai
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

class ModerationHandlers:
    def __init__(self):
        self.analytics_service = AnalyticsService()
    
    async def moderation_queue_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show moderation queue for super admins"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Access denied. Super admin privileges required.")
                session.close()
                return
            
            # Get pending questions
            pending_questions = self.analytics_service.get_moderation_queue()
            
            if not pending_questions:
                await update.message.reply_text("✅ No questions pending moderation review.")
                session.close()
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
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in moderation_queue_command: {e}")
            await update.message.reply_text("❌ Error loading moderation queue.")
    
    async def moderation_review_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed question for review"""
        try:
            query = update.callback_query
            await query.answer()
            
            question_id = int(query.data.split('_')[-1])
            
            session = SessionLocal()
            question = session.query(Question).filter(Question.question_id == question_id).first()
            
            if not question:
                await query.edit_message_text("❌ Question not found.")
                session.close()
                return
            
            # Get uploader info
            uploader = session.query(User).filter(User.user_id == question.uploader_id).first()
            
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
            message += f"**AI Score:** {question.moderation_score}/100\n"
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
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in moderation_review_callback: {e}")
            await query.edit_message_text("❌ Error loading question details.")
    
    async def moderation_approve_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Approve a question"""
        try:
            query = update.callback_query
            await query.answer()
            
            question_id = int(query.data.split('_')[-1])
            
            session = SessionLocal()
            question = session.query(Question).filter(Question.question_id == question_id).first()
            
            if not question:
                await query.edit_message_text("❌ Question not found.")
                session.close()
                return
            
            # Approve the question
            question.needs_review = False
            question.reviewed_by_admin_id = update.effective_user.id
            
            # Update contributor stats
            if question.uploader_id:
                self.analytics_service.update_contributor_stats(question.uploader_id, question_id, "approved")
            
            session.commit()
            session.close()
            
            await query.edit_message_text("✅ Question approved successfully!")
            
        except Exception as e:
            logger.error(f"Error in moderation_approve_callback: {e}")
            await query.edit_message_text("❌ Error approving question.")
    
    async def moderation_reject_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reject a question"""
        try:
            query = update.callback_query
            await query.answer()
            
            question_id = int(query.data.split('_')[-1])
            
            session = SessionLocal()
            question = session.query(Question).filter(Question.question_id == question_id).first()
            
            if not question:
                await query.edit_message_text("❌ Question not found.")
                session.close()
                return
            
            # Reject the question
            question.is_active = False
            question.needs_review = False
            question.reviewed_by_admin_id = update.effective_user.id
            
            # Update contributor stats
            if question.uploader_id:
                self.analytics_service.update_contributor_stats(question.uploader_id, question_id, "rejected")
            
            session.commit()
            session.close()
            
            await query.edit_message_text("❌ Question rejected.")
            
        except Exception as e:
            logger.error(f"Error in moderation_reject_callback: {e}")
            await query.edit_message_text("❌ Error rejecting question.")
    
    async def moderate_question_after_upload(self, question_data: Dict[str, Any], question_id: int):
        """Automatically moderate a question after upload"""
        try:
            # Run AI moderation
            moderation_result = moderate_question_with_ai(question_data)
            
            session = SessionLocal()
            question = session.query(Question).filter(Question.question_id == question_id).first()
            
            if question:
                question.moderation_score = moderation_result.get('moderation_score', 0)
                question.moderation_comments = moderation_result.get('moderation_comments', '')
                question.moderated_by_ai = True
                
                # Set needs_review based on AI decision
                action = moderation_result.get('action', 'flag')
                if action == 'flag':
                    question.needs_review = True
                elif action == 'reject':
                    question.is_active = False
                    question.needs_review = False
                else:  # accept
                    question.needs_review = False
                
                session.commit()
                
                # Update contributor stats
                if question.uploader_id:
                    self.analytics_service.update_contributor_stats(
                        question.uploader_id, 
                        question_id, 
                        action
                    )
            
            session.close()
            return moderation_result
            
        except Exception as e:
            logger.error(f"Error in moderate_question_after_upload: {e}")
            return {"error": str(e)}
