"""
Role-based authentication handlers for BotCamp Medical
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.user_service import UserService
from config.auth import verify_admin_code, verify_super_admin_code, get_admin_name
from handlers.quiz_handler import QuizHandler
import logging

logger = logging.getLogger(__name__)

class RoleAuthHandler:
    def __init__(self):
        self.user_service = UserService()
        self.quiz_handler = QuizHandler()
        self.pending_auth = {}  # Store pending authentication attempts
    
    async def show_role_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show role selection menu"""
        try:
            telegram_id = update.effective_user.id
            user_prefs = self.user_service.get_user_preferences(telegram_id)
            
            # If user already has preferences and is a student, skip role selection
            if (user_prefs.get("role") == "student" and 
                user_prefs.get("university") and 
                user_prefs.get("course") and 
                user_prefs.get("year")):
                
                # Skip to unit selection
                await self.show_unit_selection(update, context)
                return
            
            keyboard = [
                [InlineKeyboardButton("1️⃣ Student", callback_data="role_student")],
                [InlineKeyboardButton("2️⃣ Admin", callback_data="role_admin")],
                [InlineKeyboardButton("3️⃣ Super Admin", callback_data="role_super_admin")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            welcome_text = """👋 Welcome to BotCamp Medical!

Please choose your role:
1️⃣ Student - Access quizzes and study materials
2️⃣ Admin - Upload and manage questions
3️⃣ Super Admin - System administration

Choose your role to continue:"""
            
            await update.message.reply_text(welcome_text, reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"Error in show_role_selection: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def handle_role_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle role selection callback"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            role_data = query.data
            
            if role_data == "role_student":
                # Set user as student and proceed to university selection
                self.user_service.set_user_role(telegram_id, "student")
                await self.show_university_selection(update, context)
                
            elif role_data == "role_admin":
                # Request admin code
                self.pending_auth[telegram_id] = {"role": "admin", "step": "code"}
                await query.edit_message_text(
                    "🔐 Admin Access Required\n\n"
                    "Please enter your admin code:",
                    reply_markup=None
                )
                
            elif role_data == "role_super_admin":
                # Request super admin code
                self.pending_auth[telegram_id] = {"role": "super_admin", "step": "code"}
                await query.edit_message_text(
                    "🔐 Super Admin Access Required\n\n"
                    "Please enter your super admin code:",
                    reply_markup=None
                )
                
        except Exception as e:
            logger.error(f"Error in handle_role_callback: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_auth_code(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle authentication code input"""
        try:
            telegram_id = update.effective_user.id
            code = update.message.text.strip()
            
            if telegram_id not in self.pending_auth:
                await update.message.reply_text("❌ No pending authentication. Please start over with /start")
                return
            
            auth_info = self.pending_auth[telegram_id]
            role = auth_info["role"]
            
            # Verify code based on role
            if role == "admin":
                if verify_admin_code(code):
                    self.user_service.set_user_role(telegram_id, "admin", code)
                    admin_name = get_admin_name(code)
                    await update.message.reply_text(
                        f"✅ Welcome, {admin_name}!\n\n"
                        "You now have admin access. Use /admin to access admin features."
                    )
                    del self.pending_auth[telegram_id]
                else:
                    await update.message.reply_text(
                        "❌ Invalid admin code. Please try again or contact support."
                    )
                    
            elif role == "super_admin":
                if verify_super_admin_code(code):
                    self.user_service.set_user_role(telegram_id, "super_admin", code)
                    await update.message.reply_text(
                        "✅ Welcome, Super Admin!\n\n"
                        "You now have full system access. Use /superadmin to access admin features."
                    )
                    del self.pending_auth[telegram_id]
                else:
                    await update.message.reply_text(
                        "❌ Invalid super admin code. Please try again or contact support."
                    )
            
        except Exception as e:
            logger.error(f"Error in handle_auth_code: {e}")
            await update.message.reply_text("❌ An error occurred. Please try again.")
    
    async def show_university_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show university selection (defaults to University of Nairobi)"""
        try:
            keyboard = [
                [InlineKeyboardButton("🏛️ University of Nairobi", callback_data="university_uon")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "🏛️ Select University:\n\n"
                "Currently available:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_university_selection: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_course_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show course selection (defaults to MBChB)"""
        try:
            keyboard = [
                [InlineKeyboardButton("🎓 MBChB (Bachelor of Medicine)", callback_data="course_mbchb")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "🎓 Select Course:\n\n"
                "Available courses:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_course_selection: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_year_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show year selection (1-6)"""
        try:
            keyboard = [
                [InlineKeyboardButton("Year 1", callback_data="year_1"),
                 InlineKeyboardButton("Year 2", callback_data="year_2")],
                [InlineKeyboardButton("Year 3", callback_data="year_3"),
                 InlineKeyboardButton("Year 4", callback_data="year_4")],
                [InlineKeyboardButton("Year 5", callback_data="year_5"),
                 InlineKeyboardButton("Year 6", callback_data="year_6")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "📚 Select Your Year of Study:\n\n"
                "Choose your current year:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_year_selection: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_unit_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show unit selection based on user's year"""
        try:
            telegram_id = update.effective_user.id
            user_prefs = self.user_service.get_user_preferences(telegram_id)
            year = user_prefs.get("year")
            
            if not year:
                await update.message.reply_text("❌ Please select your year first with /start")
                return
            
            # Define units by year (simplified for now)
            units_by_year = {
                1: ["Human Anatomy", "Physiology I", "Biochemistry", "Behavioural Science", "IT in Medicine"],
                2: ["Microbiology", "Immunology", "Pathology I", "Physiology II"],
                3: ["Pathology II", "Clinical Pharmacology I", "General Surgery I", "Internal Medicine I"],
                4: ["Obstetrics & Gynaecology", "Psychiatry"],
                5: ["Community Health", "Internal Medicine"],
                6: ["Clinical Rotations"]
            }
            
            units = units_by_year.get(year, [])
            if not units:
                await update.message.reply_text(f"❌ No units available for Year {year}")
                return
            
            keyboard = []
            for unit in units:
                keyboard.append([InlineKeyboardButton(f"📖 {unit}", callback_data=f"unit_{unit}")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                f"📖 Select Unit (Year {year}):\n\n"
                "Choose a unit to study:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_unit_selection: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def handle_navigation_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle navigation callbacks (university, course, year, unit)"""
        try:
            query = update.callback_query
            await query.answer()
            
            telegram_id = update.effective_user.id
            callback_data = query.data
            
            if callback_data == "university_uon":
                self.user_service.set_user_preferences(telegram_id, university="University of Nairobi")
                await self.show_course_selection(update, context)
                
            elif callback_data == "course_mbchb":
                self.user_service.set_user_preferences(telegram_id, course="MBChB")
                await self.show_year_selection(update, context)
                
            elif callback_data.startswith("year_"):
                year = int(callback_data.split("_")[1])
                self.user_service.set_user_preferences(telegram_id, year=year)
                await self.show_unit_selection(update, context)
                
            elif callback_data.startswith("unit_"):
                unit = callback_data.replace("unit_", "")
                # Store current unit in context for quiz
                context.user_data["current_unit"] = unit
                await self.show_topic_selection(update, context, unit)
                
            elif callback_data.startswith("topic_"):
                topic = callback_data.replace("topic_", "")
                unit = context.user_data.get("current_unit", "General")
                await self.quiz_handler.start_quiz(update, context, unit, topic)
                
            elif callback_data == "quiz_all":
                unit = context.user_data.get("current_unit", "General")
                await self.quiz_handler.start_quiz(update, context, unit)
                
            elif callback_data.startswith("answer_"):
                await self.quiz_handler.handle_answer(update, context)
                
            elif callback_data == "next_question":
                await self.quiz_handler.next_question(update, context)
                
            elif callback_data == "view_stats":
                await self.quiz_handler.show_stats(update, context)
                
        except Exception as e:
            logger.error(f"Error in handle_navigation_callback: {e}")
            await query.edit_message_text("❌ An error occurred. Please try again.")
    
    async def show_topic_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE, unit: str):
        """Show topic selection for a unit"""
        try:
            # Define topics by unit (simplified for now)
            topics_by_unit = {
                "Human Anatomy": ["Upper Limb", "Head and Neck", "Thorax", "Abdomen", "Lower Limb", "Neuroanatomy"],
                "Physiology I": ["Cardiovascular", "Respiratory", "Renal", "Endocrine"],
                "Biochemistry": ["Carbohydrates", "Proteins", "Lipids", "Enzymes"],
                "Microbiology": ["Bacteriology", "Virology", "Parasitology", "Mycology"],
                "Pathology I": ["Cellular Injury", "Inflammation", "Neoplasia"]
            }
            
            topics = topics_by_unit.get(unit, ["General Topics"])
            
            keyboard = []
            for topic in topics:
                keyboard.append([InlineKeyboardButton(f"📚 {topic}", callback_data=f"topic_{topic}")])
            
            # Add quiz option
            keyboard.append([InlineKeyboardButton("📝 Take Quiz (All Topics)", callback_data="quiz_all")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                f"📚 Select Topic in {unit}:\n\n"
                "Choose a specific topic or take a quiz covering all topics:",
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"Error in show_topic_selection: {e}")
            await update.callback_query.edit_message_text("❌ An error occurred. Please try again.")
    
    def cleanup_pending_auth(self, telegram_id: int):
        """Clean up pending authentication for a user"""
        if telegram_id in self.pending_auth:
            del self.pending_auth[telegram_id]
