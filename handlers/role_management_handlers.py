"""
Role Management Handlers for BotCamp Medical
Implements Part 4 - Dynamic Role Management and Access Control
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User, QuestionUpload
from database.db_v2 import SessionLocal
from services.role_management_service import RoleManagementService
from services.session_service import SessionService

logger = logging.getLogger(__name__)

class RoleManagementHandlers:
    def __init__(self):
        self.role_service = RoleManagementService()
        self.session_service = SessionService()
    
    async def promote_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /promote_admin command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /promote_admin <user_id>")
                return
            
            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ User ID must be a number.")
                return
            
            result = self.role_service.promote_to_admin(target_user_id, user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in promote_admin_command: {e}")
            await update.message.reply_text("❌ Error promoting user.")
    
    async def demote_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /demote_admin command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /demote_admin <user_id>")
                return
            
            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ User ID must be a number.")
                return
            
            result = self.role_service.demote_admin(target_user_id, user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in demote_admin_command: {e}")
            await update.message.reply_text("❌ Error demoting admin.")
    
    async def disable_admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /disable_admin command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /disable_admin <user_id>")
                return
            
            try:
                target_user_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ User ID must be a number.")
                return
            
            result = self.role_service.disable_admin(target_user_id, user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in disable_admin_command: {e}")
            await update.message.reply_text("❌ Error disabling admin.")
    
    async def generate_admin_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /generate_admin_code command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            # Parse expiration hours if provided
            expires_hours = 24  # Default
            if context.args:
                try:
                    expires_hours = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Expiration hours must be a number.")
                    return
            
            result = self.role_service.generate_admin_access_code(user_id, expires_hours)
            
            if result['success']:
                message = f"""✅ **Admin Access Code Generated**

**Code:** `{result['code']}`
**Expires:** {result['expires_at'].strftime('%Y-%m-%d %H:%M:%S')}
**ID:** {result['code_id']}

⚠️ **Share this code securely with the intended admin.**"""
                
                await update.message.reply_text(message, parse_mode='Markdown')
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in generate_admin_code_command: {e}")
            await update.message.reply_text("❌ Error generating access code.")
    
    async def view_global_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /view_global_stats command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            session = SessionLocal()
            
            # Get global statistics
            total_users = session.query(User).count()
            total_admins = session.query(User).filter(User.role == "admin").count()
            total_super_admins = session.query(User).filter(User.role == "super_admin").count()
            total_students = session.query(User).filter(User.role == "student").count()
            
            # Get upload statistics
            total_uploads = session.query(QuestionUpload).count()
            pending_uploads = session.query(QuestionUpload).filter(QuestionUpload.status == "pending").count()
            approved_uploads = session.query(QuestionUpload).filter(QuestionUpload.status == "approved").count()
            rejected_uploads = session.query(QuestionUpload).filter(QuestionUpload.status == "rejected").count()
            
            # Get active access codes
            active_codes = len(self.role_service.get_active_access_codes())
            
            session.close()
            
            message = f"""📊 **Global System Statistics**

**👥 Users:**
• Total Users: {total_users}
• Students: {total_students}
• Admins: {total_admins}
• Super Admins: {total_super_admins}

**📤 Uploads:**
• Total Uploads: {total_uploads}
• Pending: {pending_uploads}
• Approved: {approved_uploads}
• Rejected: {rejected_uploads}

**🔑 Access Control:**
• Active Access Codes: {active_codes}

**📈 System Health:** ✅ Operational"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in view_global_stats_command: {e}")
            await update.message.reply_text("❌ Error retrieving global statistics.")
    
    async def approve_upload_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /approve_upload command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /approve_upload <upload_id>")
                return
            
            try:
                upload_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Upload ID must be a number.")
                return
            
            session = SessionLocal()
            
            # Find upload
            upload = session.query(QuestionUpload).filter(QuestionUpload.upload_id == upload_id).first()
            
            if not upload:
                session.close()
                await update.message.reply_text("❌ Upload not found.")
                return
            
            if upload.status != "pending":
                session.close()
                await update.message.reply_text("❌ Upload is not pending approval.")
                return
            
            # Approve upload
            upload.status = "approved"
            upload.approved_by = user_id
            upload.approved_at = datetime.utcnow()
            
            session.commit()
            session.close()
            
            await update.message.reply_text(f"✅ Upload {upload_id} approved successfully.")
            
        except Exception as e:
            logger.error(f"Error in approve_upload_command: {e}")
            await update.message.reply_text("❌ Error approving upload.")
    
    async def list_admins_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_admins command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            admins = self.role_service.get_admin_list()
            
            if not admins:
                await update.message.reply_text("📋 No admins found.")
                return
            
            message = "👥 **Admin List**\n\n"
            
            for admin in admins:
                role_emoji = "👑" if admin['role'] == "super_admin" else "👨‍🏫"
                status = "✅ Active" if admin['is_active'] else "❌ Disabled"
                
                message += f"{role_emoji} **{admin['first_name'] or admin['username']}**\n"
                message += f"• Role: {admin['role'].title()}\n"
                message += f"• Status: {status}\n"
                if admin['university'] and admin['course']:
                    message += f"• Scope: {admin['university']} - {admin['course']}\n"
                message += f"• Last Activity: {admin['last_activity'].strftime('%Y-%m-%d %H:%M') if admin['last_activity'] else 'Never'}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in list_admins_command: {e}")
            await update.message.reply_text("❌ Error retrieving admin list.")
    
    async def list_access_codes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /list_access_codes command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            codes = self.role_service.get_active_access_codes()
            
            if not codes:
                await update.message.reply_text("🔑 No active access codes found.")
                return
            
            message = "🔑 **Active Admin Access Codes**\n\n"
            
            for code in codes:
                status = "✅ Used" if code['is_used'] else "⏳ Available"
                used_by = f" by {code['used_by']}" if code['used_by'] else ""
                
                message += f"**Code ID:** {code['code_id']}\n"
                message += f"• Created by: {code['created_by']}\n"
                message += f"• Status: {status}{used_by}\n"
                message += f"• Created: {code['created_at'].strftime('%Y-%m-%d %H:%M')}\n"
                message += f"• Expires: {code['expires_at'].strftime('%Y-%m-%d %H:%M')}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in list_access_codes_command: {e}")
            await update.message.reply_text("❌ Error retrieving access codes.")
    
    async def revoke_access_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /revoke_access_code command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /revoke_access_code <code_id>")
                return
            
            try:
                code_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Code ID must be a number.")
                return
            
            result = self.role_service.revoke_access_code(code_id, user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in revoke_access_code_command: {e}")
            await update.message.reply_text("❌ Error revoking access code.")
    
    async def audit_logs_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /audit_logs command - Super Admin only"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            if self.role_service.get_user_role(user_id) != "super_admin":
                await update.message.reply_text("❌ Super admin privileges required.")
                return
            
            # Parse limit if provided
            limit = 20  # Default
            if context.args:
                try:
                    limit = int(context.args[0])
                except ValueError:
                    await update.message.reply_text("❌ Limit must be a number.")
                    return
            
            logs = self.role_service.get_audit_logs(limit)
            
            if not logs:
                await update.message.reply_text("📋 No audit logs found.")
                return
            
            message = f"📋 **Recent Audit Logs** (Last {len(logs)} entries)\n\n"
            
            for log in logs:
                action_emoji = {
                    "role_change": "🔄",
                    "admin_promotion": "⬆️",
                    "admin_demotion": "⬇️",
                    "admin_disabled": "❌",
                    "admin_code_generated": "🔑",
                    "access_code_revoked": "🔒"
                }.get(log['action'], "📝")
                
                message += f"{action_emoji} **{log['user']}**\n"
                message += f"• Action: {log['action'].replace('_', ' ').title()}\n"
                if log['old_role'] and log['new_role']:
                    message += f"• Role Change: {log['old_role']} → {log['new_role']}\n"
                if log['details']:
                    message += f"• Details: {log['details']}\n"
                message += f"• Time: {log['timestamp'].strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in audit_logs_command: {e}")
            await update.message.reply_text("❌ Error retrieving audit logs.")
    
    async def admin_code_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin access code input"""
        try:
            if not context.user_data.get('awaiting_admin_code'):
                return
            
            user_id = update.effective_user.id
            code = update.message.text.strip()
            
            result = self.role_service.verify_admin_access_code(code, user_id)
            
            if result['success']:
                # Update user state
                self.session_service.save_user_state(user_id, "admin")
                
                await update.message.reply_text(result['message'])
                
                # Show admin dashboard
                await self._show_admin_dashboard(update)
            else:
                await update.message.reply_text(
                    result['message'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")]
                    ])
                )
            
            context.user_data.pop('awaiting_admin_code', None)
            
        except Exception as e:
            logger.error(f"Error in admin_code_handler: {e}")
    
    async def super_admin_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle super admin key input"""
        try:
            if not context.user_data.get('awaiting_super_admin_key'):
                return
            
            user_id = update.effective_user.id
            key = update.message.text.strip()
            
            result = self.role_service.verify_super_admin_key(key, user_id)
            
            if result['success']:
                # Update user state
                self.session_service.save_user_state(user_id, "super_admin")
                
                await update.message.reply_text(result['message'])
                
                # Show super admin dashboard
                await self._show_super_admin_dashboard(update)
            else:
                await update.message.reply_text(
                    result['message'],
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")]
                    ])
                )
            
            context.user_data.pop('awaiting_super_admin_key', None)
            
        except Exception as e:
            logger.error(f"Error in super_admin_key_handler: {e}")
    
    async def _show_admin_dashboard(self, update: Update):
        """Show admin dashboard"""
        try:
            message = """⚙️ **ADMIN DASHBOARD**
Select what you'd like to do:"""
            
            keyboard = [
                [InlineKeyboardButton("📤 Upload Questions", callback_data="admin_upload")],
                [InlineKeyboardButton("📋 Review Uploads", callback_data="admin_review")],
                [InlineKeyboardButton("📊 View Unit Stats", callback_data="admin_stats")],
                [InlineKeyboardButton("📈 My Uploads", callback_data="admin_my_uploads")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error showing admin dashboard: {e}")
    
    async def _show_super_admin_dashboard(self, update: Update):
        """Show super admin dashboard"""
        try:
            message = """👑 **SUPER ADMIN CONTROL PANEL**
Select an option:"""
            
            keyboard = [
                [InlineKeyboardButton("👥 Manage Admins", callback_data="super_manage_admins")],
                [InlineKeyboardButton("🔑 Generate Admin Code", callback_data="super_generate_code")],
                [InlineKeyboardButton("📊 Global Statistics", callback_data="super_global_stats")],
                [InlineKeyboardButton("📋 Review All Uploads", callback_data="super_review_uploads")],
                [InlineKeyboardButton("🔒 Security & Backup", callback_data="super_security")],
                [InlineKeyboardButton("📋 Audit Logs", callback_data="super_audit_logs")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
            
        except Exception as e:
            logger.error(f"Error showing super admin dashboard: {e}")
