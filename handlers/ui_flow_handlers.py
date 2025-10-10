"""
UI/UX Flow Handlers for BotCamp Medical
Implements Master Specification Section 11 - Telegram UI/UX and Conversation Flow Design
"""

import logging
from typing import Dict, Any, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User, University, Course, Unit, Topic, AdminScope
from database.db_v2 import SessionLocal
from services.session_service import SessionService
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

class UIFlowHandlers:
    def __init__(self):
        self.session_service = SessionService()
        self.analytics_service = AnalyticsService()
    
    async def start_command_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command with role selection per Section 11.2"""
        try:
            user = update.effective_user
            user_id = user.id
            
            # Check if user has existing state
            resume_message = self.session_service.get_resume_message(user_id)
            
            if resume_message:
                # User has existing state, show resume message
                keyboard = [
                    [InlineKeyboardButton("✅ Continue", callback_data="continue_session")],
                    [InlineKeyboardButton("🔄 Reset", callback_data="reset_session")]
                ]
                
                await update.message.reply_text(
                    resume_message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # New user or no existing state
            message = f"""👋 Hello {user.first_name or 'there'}!
Welcome to BotCamp Medical.

Please choose your role to continue:"""
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Student", callback_data="role_student")],
                [InlineKeyboardButton("2️⃣ Admin", callback_data="role_admin")],
                [InlineKeyboardButton("3️⃣ Super Admin", callback_data="role_super_admin")]
            ]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error in start_command_handler: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def role_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection per Section 11.3"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            role_data = query.data.split('_')[1]  # student, admin, or super_admin
            
            if role_data == "student":
                # Store role and show university selection
                self.session_service.save_user_state(user_id, "student")
                await self._show_university_selection(query)
                
            elif role_data == "admin":
                # Prompt for admin passcode
                await query.edit_message_text(
                    "🔑 Please enter your Admin access code:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")]
                    ])
                )
                context.user_data['awaiting_admin_code'] = True
                
            elif role_data == "super_admin":
                # Prompt for super admin key
                await query.edit_message_text(
                    "🔒 Please enter Super Admin key:",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")]
                    ])
                )
                context.user_data['awaiting_super_admin_key'] = True
                
        except Exception as e:
            logger.error(f"Error in role_selection_handler: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def admin_code_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin code verification"""
        try:
            if not context.user_data.get('awaiting_admin_code'):
                return
            
            user_id = update.effective_user.id
            code = update.message.text.strip()
            
            # Verify admin code (you can implement your own verification logic)
            if self._verify_admin_code(code):
                self.session_service.save_user_state(user_id, "admin")
                await self._show_admin_dashboard(update)
            else:
                await update.message.reply_text(
                    "❌ Incorrect code",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")]
                    ])
                )
            
            context.user_data.pop('awaiting_admin_code', None)
            
        except Exception as e:
            logger.error(f"Error in admin_code_handler: {e}")
    
    async def super_admin_key_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle super admin key verification"""
        try:
            if not context.user_data.get('awaiting_super_admin_key'):
                return
            
            user_id = update.effective_user.id
            key = update.message.text.strip()
            
            # Verify super admin key (you can implement your own verification logic)
            if self._verify_super_admin_key(key):
                self.session_service.save_user_state(user_id, "super_admin")
                await self._show_super_admin_dashboard(update)
            else:
                await update.message.reply_text(
                    "❌ Incorrect key",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")]
                    ])
                )
            
            context.user_data.pop('awaiting_super_admin_key', None)
            
        except Exception as e:
            logger.error(f"Error in super_admin_key_handler: {e}")
    
    async def _show_university_selection(self, query):
        """Show university selection per Section 11.4"""
        try:
            hierarchy_data = self.session_service.get_hierarchy_data()
            universities = hierarchy_data.get('universities', [])
            
            if not universities:
                await query.edit_message_text("❌ No universities available.")
                return
            
            message = "🏫 Select your University"
            keyboard = []
            
            for uni in universities[:10]:  # Limit to 10 for UI
                keyboard.append([
                    InlineKeyboardButton(uni['name'], callback_data=f"university_{uni['id']}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Role Selection", callback_data="back_to_roles")])
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing university selection: {e}")
    
    async def university_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle university selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            university_id = int(query.data.split('_')[1])
            
            # Get university name and save to state
            session = SessionLocal()
            university = session.query(University).filter(University.id == university_id).first()
            session.close()
            
            if university:
                self.session_service.save_user_state(
                    user_id, 
                    "student", 
                    university=university.name
                )
                await self._show_course_selection(query, university.name)
            else:
                await query.edit_message_text("❌ University not found.")
                
        except Exception as e:
            logger.error(f"Error in university_selection_handler: {e}")
    
    async def _show_course_selection(self, query, university_name: str):
        """Show course selection"""
        try:
            hierarchy_data = self.session_service.get_hierarchy_data(university=university_name)
            courses = hierarchy_data.get('courses', [])
            
            if not courses:
                await query.edit_message_text("❌ No courses available for this university.")
                return
            
            message = f"🎓 Select your Course (University: {university_name})"
            keyboard = []
            
            for course in courses:
                keyboard.append([
                    InlineKeyboardButton(course['name'], callback_data=f"course_{course['id']}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to University", callback_data="back_to_university")])
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing course selection: {e}")
    
    async def course_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle course selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            course_id = int(query.data.split('_')[1])
            
            # Get course name and save to state
            session = SessionLocal()
            course = session.query(Course).filter(Course.id == course_id).first()
            session.close()
            
            if course:
                self.session_service.save_user_state(
                    user_id, 
                    "student", 
                    course=course.name
                )
                await self._show_year_selection(query, course.name)
            else:
                await query.edit_message_text("❌ Course not found.")
                
        except Exception as e:
            logger.error(f"Error in course_selection_handler: {e}")
    
    async def _show_year_selection(self, query, course_name: str):
        """Show year selection (1-6)"""
        try:
            message = f"📅 Select your Year (Course: {course_name})"
            keyboard = []
            
            for year in range(1, 7):  # Years 1-6
                keyboard.append([
                    InlineKeyboardButton(f"Year {year}", callback_data=f"year_{year}")
                ])
            
            keyboard.append([InlineKeyboardButton("🔙 Back to Course", callback_data="back_to_course")])
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing year selection: {e}")
    
    async def year_selection_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle year selection"""
        try:
            query = update.callback_query
            await query.answer()
            
            user_id = update.effective_user.id
            year = int(query.data.split('_')[1])
            
            self.session_service.save_user_state(
                user_id, 
                "student", 
                year=year
            )
            await self._show_student_dashboard(query)
            
        except Exception as e:
            logger.error(f"Error in year_selection_handler: {e}")
    
    async def _show_student_dashboard(self, query):
        """Show student dashboard per Section 11.4"""
        try:
            message = """🎓 STUDENT DASHBOARD
Select an option:"""
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Select University and Course", callback_data="select_university_course")],
                [InlineKeyboardButton("2️⃣ Take Quiz", callback_data="take_quiz")],
                [InlineKeyboardButton("3️⃣ View Statistics", callback_data="view_statistics")],
                [InlineKeyboardButton("4️⃣ Help", callback_data="help")]
            ]
            
            await query.edit_message_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        except Exception as e:
            logger.error(f"Error showing student dashboard: {e}")
    
    async def _show_admin_dashboard(self, update: Update):
        """Show admin dashboard per Section 11.5"""
        try:
            message = """⚙️ ADMIN DASHBOARD
Select what you'd like to do:"""
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Upload Questions", callback_data="upload_questions")],
                [InlineKeyboardButton("2️⃣ Review Pending Uploads", callback_data="review_uploads")],
                [InlineKeyboardButton("3️⃣ Manage Topics/Units", callback_data="manage_topics")],
                [InlineKeyboardButton("4️⃣ View Upload History", callback_data="upload_history")],
                [InlineKeyboardButton("5️⃣ Back to Main Menu", callback_data="main_menu")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
        except Exception as e:
            logger.error(f"Error showing admin dashboard: {e}")
    
    async def _show_super_admin_dashboard(self, update: Update):
        """Show super admin dashboard per Section 11.6"""
        try:
            message = """🔐 SUPER ADMIN PANEL
Select an option:"""
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Manage Admins", callback_data="manage_admins")],
                [InlineKeyboardButton("2️⃣ Broadcast Announcement", callback_data="broadcast")],
                [InlineKeyboardButton("3️⃣ Review All Uploads", callback_data="review_all_uploads")],
                [InlineKeyboardButton("4️⃣ Edit Curriculum", callback_data="edit_curriculum")],
                [InlineKeyboardButton("5️⃣ Data Export", callback_data="data_export")],
                [InlineKeyboardButton("6️⃣ System Health", callback_data="system_health")],
                [InlineKeyboardButton("7️⃣ Back to Main Menu", callback_data="main_menu")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
        except Exception as e:
            logger.error(f"Error showing super admin dashboard: {e}")
    
    async def help_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show help section per Section 11.7"""
        try:
            message = """📘 HELP
- To take a quiz: Select your University → Course → Year → Unit → Topic → Take Quiz.
- To upload questions: Must be an Admin.
- Need access? Contact @BotCampSupport."""
            
            keyboard = [
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            else:
                await update.message.reply_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
            
        except Exception as e:
            logger.error(f"Error in help_handler: {e}")
    
    def _verify_admin_code(self, code: str) -> bool:
        """Verify admin access code"""
        # Implement your admin code verification logic
        # For now, using a simple example
        return code == "admin123"  # Replace with your actual verification
    
    def _verify_super_admin_key(self, key: str) -> bool:
        """Verify super admin key"""
        # Implement your super admin key verification logic
        # For now, using a simple example
        return key == "superadmin456"  # Replace with your actual verification
