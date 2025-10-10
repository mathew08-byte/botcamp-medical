"""
Specification Handlers for BotCamp Medical
Implements Master Specification Sections 11-15 command handlers
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User, AdminScope
from database.db_v2 import SessionLocal
from services.session_service import SessionService
from services.multi_admin_service import MultiAdminService
from services.backup_export_service import BackupExportService
from services.multi_university_service import MultiUniversityService

logger = logging.getLogger(__name__)

class SpecificationHandlers:
    def __init__(self):
        self.session_service = SessionService()
        self.multi_admin_service = MultiAdminService()
        self.backup_service = BackupExportService()
        self.university_service = MultiUniversityService()
    
    async def exportdata_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /exportdata command per Section 14.2"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            # Parse filters from command arguments
            filters = {}
            if context.args:
                for arg in context.args:
                    if '=' in arg:
                        key, value = arg.split('=', 1)
                        filters[key] = value
            
            # Create export
            result = self.backup_service.export_data(filters)
            
            if result['success']:
                await update.message.reply_text(
                    f"✅ Export created successfully!\n"
                    f"📊 Records exported: {result['records_exported']}\n"
                    f"📁 File: {result['file_path']}"
                )
            else:
                await update.message.reply_text(f"❌ Export failed: {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in exportdata_command: {e}")
            await update.message.reply_text("❌ Error creating export.")
    
    async def adduniversity_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /adduniversity command per Section 15.2"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /adduniversity <name>")
                return
            
            university_name = ' '.join(context.args)
            result = self.university_service.add_university(university_name, user.user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in adduniversity_command: {e}")
            await update.message.reply_text("❌ Error adding university.")
    
    async def addcourse_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addcourse command per Section 15.2"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            if len(context.args) < 2:
                await update.message.reply_text("Usage: /addcourse <university> <course>")
                return
            
            university_name = context.args[0]
            course_name = ' '.join(context.args[1:])
            
            result = self.university_service.add_course(university_name, course_name, user.user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in addcourse_command: {e}")
            await update.message.reply_text("❌ Error adding course.")
    
    async def addunit_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addunit command per Section 15.2"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            if len(context.args) < 3:
                await update.message.reply_text("Usage: /addunit <course> <year> <unit>")
                return
            
            course_name = context.args[0]
            try:
                year = int(context.args[1])
            except ValueError:
                await update.message.reply_text("❌ Year must be a number.")
                return
            
            unit_name = ' '.join(context.args[2:])
            
            result = self.university_service.add_unit(course_name, year, unit_name, user.user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in addunit_command: {e}")
            await update.message.reply_text("❌ Error adding unit.")
    
    async def addtopic_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /addtopic command per Section 15.2"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            if len(context.args) < 2:
                await update.message.reply_text("Usage: /addtopic <unit> <topic>")
                return
            
            unit_name = context.args[0]
            topic_name = ' '.join(context.args[1:])
            
            result = self.university_service.add_topic(unit_name, topic_name, user.user_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in addtopic_command: {e}")
            await update.message.reply_text("❌ Error adding topic.")
    
    async def healthcheck_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /healthcheck command per Section 14.5"""
        try:
            # Check database connection
            session = SessionLocal()
            try:
                session.execute("SELECT 1")
                db_status = "✅ Connected"
            except Exception as e:
                db_status = f"❌ Error: {str(e)}"
            finally:
                session.close()
            
            # Check backup status
            backup_status = self.backup_service.get_backup_status()
            
            # Check expired locks
            expired_locks = self.multi_admin_service.cleanup_expired_locks()
            
            message = f"""🔍 **System Health Check**

**Database:** {db_status}

**Backups:**
📁 Total Backups: {backup_status.get('backup_count', 0)}
📊 Total Exports: {backup_status.get('export_count', 0)}
💾 Total Size: {backup_status.get('total_size_mb', 0)} MB
🗑️ Retention: {backup_status.get('retention_days', 0)} days

**Admin Coordination:**
🔓 Expired Locks Cleaned: {expired_locks}

**Status:** ✅ System Operational"""
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in healthcheck_command: {e}")
            await update.message.reply_text("❌ Health check failed.")
    
    async def backup_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /backup command for manual backup creation"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            await update.message.reply_text("📦 Creating backup... Please wait.")
            
            result = self.backup_service.create_daily_backup()
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in backup_command: {e}")
            await update.message.reply_text("❌ Backup failed.")
    
    async def restore_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /restore command for database restoration"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            if not context.args:
                await update.message.reply_text("Usage: /restore <backup_file_path>")
                return
            
            backup_path = context.args[0]
            
            await update.message.reply_text("⚠️ **WARNING: This will replace the current database!**\n\nType 'CONFIRM' to proceed:")
            context.user_data['awaiting_restore_confirmation'] = backup_path
            
        except Exception as e:
            logger.error(f"Error in restore_command: {e}")
            await update.message.reply_text("❌ Restore command failed.")
    
    async def restore_confirmation_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle restore confirmation"""
        try:
            if not context.user_data.get('awaiting_restore_confirmation'):
                return
            
            if update.message.text.strip().upper() != 'CONFIRM':
                await update.message.reply_text("❌ Restore cancelled.")
                context.user_data.pop('awaiting_restore_confirmation', None)
                return
            
            backup_path = context.user_data.pop('awaiting_restore_confirmation')
            
            await update.message.reply_text("🔄 Restoring database... Please wait.")
            
            result = self.backup_service.restore_from_backup(backup_path)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in restore_confirmation_handler: {e}")
            await update.message.reply_text("❌ Restore failed.")
    
    async def listuniversities_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /listuniversities command"""
        try:
            hierarchy = self.university_service.get_university_hierarchy()
            
            if 'error' in hierarchy:
                await update.message.reply_text(f"❌ {hierarchy['error']}")
                return
            
            message = "🏫 **Available Universities:**\n\n"
            
            for uni in hierarchy.get('universities', []):
                message += f"• {uni['name']} ({uni['courses_count']} courses)\n"
            
            await update.message.reply_text(message, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Error in listuniversities_command: {e}")
            await update.message.reply_text("❌ Error listing universities.")
    
    async def setadminscope_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /setadminscope command per Section 15.3"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is super admin
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            session.close()
            
            if not user or user.role != 'super_admin':
                await update.message.reply_text("❌ Super admin access required.")
                return
            
            if len(context.args) < 3:
                await update.message.reply_text("Usage: /setadminscope <admin_username> <university_id> <course_id>")
                return
            
            admin_username = context.args[0]
            try:
                university_id = int(context.args[1])
                course_id = int(context.args[2])
            except ValueError:
                await update.message.reply_text("❌ University ID and Course ID must be numbers.")
                return
            
            # Find admin user
            session = SessionLocal()
            admin_user = session.query(User).filter(User.username == admin_username).first()
            session.close()
            
            if not admin_user:
                await update.message.reply_text(f"❌ Admin user '{admin_username}' not found.")
                return
            
            result = self.university_service.set_admin_scope(admin_user.user_id, university_id, course_id)
            
            if result['success']:
                await update.message.reply_text(f"✅ {result['message']}")
            else:
                await update.message.reply_text(f"❌ {result['message']}")
                
        except Exception as e:
            logger.error(f"Error in setadminscope_command: {e}")
            await update.message.reply_text("❌ Error setting admin scope.")
