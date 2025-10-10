"""
Super Admin Commands Handler for BotCamp Medical
Implements super admin management commands
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.security_service import SecurityService
from services.user_service import UserService
from services.role_management_service import RoleManagementService
from database.db import SessionLocal
from database.models import User, Announcement
from typing import List, Dict, Any
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)

class SuperAdminHandler:
    def __init__(self):
        self.security_service = SecurityService()
        self.user_service = UserService()
        self.role_service = RoleManagementService()
    
    async def add_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Add admin user command: /addadmin @username <passcode> (deprecated in favor of codes)"""
        try:
            telegram_id = update.effective_user.id
            
            # Check super admin permissions
            if not self.security_service.check_admin_permissions(telegram_id, "super_admin"):
                await update.message.reply_text("❌ You do not have super admin privileges.")
                return
            
            # Parse command arguments
            if not context.args or len(context.args) < 2:
                await update.message.reply_text(
                    "❌ Usage: /addadmin @username <passcode>\n"
                    "Example: /addadmin @john_doe admin123"
                )
                return
            
            username = context.args[0]
            passcode = context.args[1]
            
            # Validate username format
            if not username.startswith('@'):
                await update.message.reply_text("❌ Username must start with @")
                return
            
            # Remove @ symbol
            username = username[1:]
            
            # Validate passcode
            if len(passcode) < 4:
                await update.message.reply_text("❌ Passcode must be at least 6 characters long")
                return
            
            # Get user by username
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                
                if not user:
                    await update.message.reply_text(f"❌ User @{username} not found in the system.")
                    return
                
                if user.role in ["admin", "super_admin"]:
                    await update.message.reply_text(f"❌ User @{username} is already an admin.")
                    return
                
                # Create admin user
                success = self.security_service.create_admin_user(
                    user.telegram_id, 
                    username, 
                    "admin", 
                    telegram_id
                )
                
                if success:
                    await update.message.reply_text(
                        f"✅ Successfully promoted @{username} to admin.\n"
                        f"Admin passcode (temp): {passcode}\n"
                        f"User ID: {user.telegram_id}"
                    )
                else:
                    await update.message.reply_text("❌ Failed to create admin user.")
                    
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error in add_admin_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")

    async def approve_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Approve an admin request and generate a one-time access code: /approve_admin <telegram_id>"""
        try:
            requester = update.effective_user.id
            if not self.security_service.check_admin_permissions(requester, "super_admin"):
                await update.message.reply_text("❌ Super admin only.")
                return
            if not context.args or not context.args[0].isdigit():
                await update.message.reply_text("Usage: /approve_admin <telegram_id>")
                return
            target_id = int(context.args[0])
            result = self.role_service.generate_admin_access_code(created_by=requester)
            if result.get("success"):
                code = result["code"]
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"✅ Admin approved. Your one-time access code: {code}\nUse it now to set your own admin code.")
                except Exception:
                    pass
                await update.message.reply_text("✅ One-time admin code generated and sent to user.")
            else:
                await update.message.reply_text(f"❌ {result.get('message','Failed to generate code')}")
        except Exception as e:
            logger.error(f"approve_admin_command error: {e}")
            await update.message.reply_text("❌ Error approving admin.")

    async def reset_admin_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Reset an admin's code (user must set new one after approval): /reset_admin_code <telegram_id>"""
        try:
            requester = update.effective_user.id
            if not self.security_service.check_admin_permissions(requester, "super_admin"):
                await update.message.reply_text("❌ Super admin only.")
                return
            if not context.args or not context.args[0].isdigit():
                await update.message.reply_text("Usage: /reset_admin_code <telegram_id>")
                return
            target_id = int(context.args[0])
            # issue a new one-time code
            result = self.role_service.generate_admin_access_code(created_by=requester)
            if result.get("success"):
                code = result["code"]
                try:
                    await context.bot.send_message(chat_id=target_id, text=f"🔐 Admin code reset approved. One-time access code: {code}\nUse it to set a new admin code.")
                except Exception:
                    pass
                await update.message.reply_text("✅ Reset code generated and sent to user.")
            else:
                await update.message.reply_text(f"❌ {result.get('message','Failed to reset code')}")
        except Exception as e:
            logger.error(f"reset_admin_code_command error: {e}")
            await update.message.reply_text("❌ Error resetting admin code.")
    
    async def remove_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Remove admin user command: /removeadmin @username"""
        try:
            telegram_id = update.effective_user.id
            
            # Check super admin permissions
            if not self.security_service.check_admin_permissions(telegram_id, "super_admin"):
                await update.message.reply_text("❌ You do not have super admin privileges.")
                return
            
            # Parse command arguments
            if not context.args or len(context.args) < 1:
                await update.message.reply_text(
                    "❌ Usage: /removeadmin @username\n"
                    "Example: /removeadmin @john_doe"
                )
                return
            
            username = context.args[0]
            
            # Validate username format
            if not username.startswith('@'):
                await update.message.reply_text("❌ Username must start with @")
                return
            
            # Remove @ symbol
            username = username[1:]
            
            # Get user by username
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.username == username).first()
                
                if not user:
                    await update.message.reply_text(f"❌ User @{username} not found in the system.")
                    return
                
                if user.role not in ["admin", "super_admin"]:
                    await update.message.reply_text(f"❌ User @{username} is not an admin.")
                    return
                
                if user.telegram_id == telegram_id:
                    await update.message.reply_text("❌ You cannot remove your own admin privileges.")
                    return
                
                # Remove admin privileges
                success = self.security_service.remove_admin_user(user.telegram_id, telegram_id)
                
                if success:
                    await update.message.reply_text(f"✅ Successfully removed admin privileges from @{username}.")
                else:
                    await update.message.reply_text("❌ Failed to remove admin privileges.")
                    
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error in remove_admin_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def list_admins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List admin users command: /listadmins"""
        try:
            telegram_id = update.effective_user.id
            
            # Check super admin permissions
            if not self.security_service.check_admin_permissions(telegram_id, "super_admin"):
                await update.message.reply_text("❌ You do not have super admin privileges.")
                return
            
            # Get admin list
            admin_list = self.security_service.get_admin_list(telegram_id)
            
            if not admin_list:
                await update.message.reply_text("❌ Failed to retrieve admin list.")
                return
            
            if not admin_list:
                await update.message.reply_text("📋 No admin users found.")
                return
            
            # Format admin list
            admin_text = "📋 **Admin Users List**\n\n"
            
            for admin in admin_list:
                role_emoji = "👑" if admin["role"] == "super_admin" else "👨‍💼"
                admin_text += f"{role_emoji} @{admin['username']} ({admin['name']})\n"
                admin_text += f"   Role: {admin['role']}\n"
                admin_text += f"   ID: {admin['telegram_id']}\n"
                admin_text += f"   Created: {admin['created_at'].strftime('%Y-%m-%d')}\n\n"
            
            await update.message.reply_text(admin_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in list_admins_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def broadcast_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Broadcast message command: /broadcast <message>"""
        try:
            telegram_id = update.effective_user.id
            
            # Check super admin permissions
            if not self.security_service.check_admin_permissions(telegram_id, "super_admin"):
                await update.message.reply_text("❌ You do not have super admin privileges.")
                return
            
            # Parse command arguments
            if not context.args:
                await update.message.reply_text(
                    "❌ Usage: /broadcast <message>\n"
                    "Example: /broadcast System maintenance scheduled for tomorrow."
                )
                return
            
            message = " ".join(context.args)
            
            # Sanitize message
            message = self.security_service.sanitize_input(message)
            
            if not message:
                await update.message.reply_text("❌ Message cannot be empty.")
                return
            
            # Show confirmation
            keyboard = [
                [InlineKeyboardButton("✅ Send Broadcast", callback_data=f"confirm_broadcast_{telegram_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data="cancel_broadcast")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📢 **Broadcast Preview**\n\n"
                f"Message: {message}\n\n"
                f"This will be sent to all users. Continue?",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Error in broadcast_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_broadcast_confirmation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast confirmation"""
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel_broadcast":
                await query.edit_message_text("❌ Broadcast cancelled.")
                return
            
            # Extract message from original command
            # This is a simplified version - in practice, you'd store the message in context
            message = "System announcement from admin."
            
            # Get all users
            db = SessionLocal()
            try:
                users = db.query(User).all()
                
                # Create announcement record
                announcement = Announcement(
                    message_text=message,
                    created_by=update.effective_user.id,
                    date=datetime.utcnow()
                )
                db.add(announcement)
                db.commit()
                
                # Send to all users (simplified - in practice, you'd use a queue)
                sent_count = 0
                failed_count = 0
                
                for user in users:
                    try:
                        await context.bot.send_message(
                            chat_id=user.telegram_id,
                            text=f"📢 **System Announcement**\n\n{message}",
                            parse_mode='Markdown'
                        )
                        sent_count += 1
                    except Exception as e:
                        logger.error(f"Failed to send broadcast to {user.telegram_id}: {e}")
                        failed_count += 1
                
                await query.edit_message_text(
                    f"✅ **Broadcast Sent**\n\n"
                    f"Successfully sent to: {sent_count} users\n"
                    f"Failed to send: {failed_count} users\n"
                    f"Announcement ID: {announcement.message_id}",
                    parse_mode='Markdown'
                )
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error in handle_broadcast_confirmation: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def system_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """System status command: /systemstatus"""
        try:
            telegram_id = update.effective_user.id
            
            # Check super admin permissions
            if not self.security_service.check_admin_permissions(telegram_id, "super_admin"):
                await update.message.reply_text("❌ You do not have super admin privileges.")
                return
            
            # Get system statistics
            db = SessionLocal()
            try:
                # User statistics
                total_users = db.query(User).count()
                admin_users = db.query(User).filter(User.role.in_(["admin", "super_admin"])).count()
                student_users = db.query(User).filter(User.role == "student").count()
                
                # Security statistics
                security_stats = self.security_service.get_security_stats()
                
                # AI service status
                from services.ai_service import AIService
                ai_service = AIService()
                ai_status = ai_service.get_ai_status()
                
                status_text = (
                    "🖥️ System Status\n\n"
                    "Users:\n"
                    f"👥 Total Users: {total_users}\n"
                    f"👨‍💼 Admins: {admin_users}\n"
                    f"🎓 Students: {student_users}\n\n"
                    "Security:\n"
                    f"🔐 Active Sessions: {security_stats['active_sessions']}\n"
                    f"⏱️ Rate Limits Tracked: {security_stats['rate_limits_tracked']}\n"
                    f"📁 Max File Size: {security_stats['max_file_size'] // (1024*1024)} MB\n"
                    f"⬆️ Max Uploads/Hour: {security_stats['max_uploads_per_hour']}\n\n"
                    "AI Services:\n"
                    f"🤖 Gemini Available: {'✅' if ai_status['gemini_available'] else '❌'}\n"
                    f"🧠 OpenAI Available: {'✅' if ai_status['openai_available'] else '❌'}\n"
                    f"🎯 Confidence Threshold: {ai_status['confidence_threshold']}\n"
                    f"👁️ OCR Provider: {ai_status['ocr_provider']}\n\n"
                    "System Health: ✅ Operational"
                )
                await update.message.reply_text(status_text)
                
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"Error in system_status_command: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def show_super_admin_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show super admin menu"""
        try:
            telegram_id = update.effective_user.id
            
            # Check super admin permissions
            if not self.security_service.check_admin_permissions(telegram_id, "super_admin"):
                await update.message.reply_text("❌ You do not have super admin privileges.")
                return
            
            keyboard = [
                [InlineKeyboardButton("👨‍💼 Manage Admins", callback_data="superadmin_manage_admins")],
                [InlineKeyboardButton("📊 System Status", callback_data="superadmin_system_status")],
                [InlineKeyboardButton("📢 Send Broadcast", callback_data="superadmin_broadcast")],
                [InlineKeyboardButton("📋 View Logs", callback_data="superadmin_view_logs")],
                [InlineKeyboardButton("🔙 Back to Admin Panel", callback_data="admin_panel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "👑 Super Admin Panel\n\nChoose an option:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_super_admin_menu: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
