"""
Analytics handlers for Step 5 - AI Moderation, Analytics & Dashboards
"""

import logging
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.models import User
from database.db_v2 import SessionLocal
from services.analytics_service import AnalyticsService

logger = logging.getLogger(__name__)

class AnalyticsHandlers:
    def __init__(self):
        self.analytics_service = AnalyticsService()
    
    async def analytics_quizzes_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show quiz analytics"""
        try:
            user_id = update.effective_user.id
            
            # Check user role
            session = get_db_session()()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ User not found.")
                session.close()
                return
            
            # Get analytics based on user role
            if user.role == 'student':
                analytics = self.analytics_service.get_quiz_analytics(user_id=user.user_id)
            else:
                analytics = self.analytics_service.get_quiz_analytics()
            
            if not analytics:
                await update.message.reply_text("📊 No quiz data available yet.")
                session.close()
                return
            
            # Format message
            message = "📊 **Quiz Analytics**\n\n"
            
            if user.role == 'student':
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
            if user.role in ['admin', 'super_admin'] and analytics['top_students']:
                message += "🏆 **Top Students:**\n"
                for student in analytics['top_students'][:5]:
                    message += f"• {student['username']}: {student['accuracy']}% ({student['quizzes']} quizzes)\n"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Refresh", callback_data="analytics_quizzes")],
                [InlineKeyboardButton("📈 My Stats", callback_data="my_stats")] if user.role == 'student' else [],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]
            ]
            
            # Remove empty lists
            keyboard = [row for row in keyboard if row]
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in analytics_quizzes_command: {e}")
            await update.message.reply_text("❌ Error loading quiz analytics.")
    
    async def my_contributions_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show contributor dashboard"""
        try:
            user_id = update.effective_user.id
            
            # Get user info
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ User not found.")
                session.close()
                return
            
            # Get contributor analytics
            analytics = self.analytics_service.get_contributor_analytics(user.user_id)
            
            if not analytics:
                await update.message.reply_text("📊 No contribution data available.")
                session.close()
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
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in my_contributions_command: {e}")
            await update.message.reply_text("❌ Error loading contribution data.")
    
    async def admin_dashboard_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin dashboard"""
        try:
            user_id = update.effective_user.id
            
            # Check if user is admin or super_admin
            session = get_db_session()()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            if not user or user.role not in ['admin', 'super_admin']:
                await update.message.reply_text("❌ Access denied. Admin privileges required.")
                session.close()
                return
            
            # Get dashboard data
            dashboard_data = self.analytics_service.get_admin_dashboard_data()
            
            if not dashboard_data:
                await update.message.reply_text("📊 No dashboard data available.")
                session.close()
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
            
            if user.role == 'super_admin':
                keyboard.append([InlineKeyboardButton("⚙️ System Status", callback_data="system_status")])
            
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in admin_dashboard_command: {e}")
            await update.message.reply_text("❌ Error loading admin dashboard.")
    
    async def my_stats_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show personal stats for students"""
        try:
            user_id = update.effective_user.id
            
            # Get user info
            session = SessionLocal()
            user = session.query(User).filter(User.telegram_id == user_id).first()
            
            if not user:
                await update.message.reply_text("❌ User not found.")
                session.close()
                return
            
            # Get personal analytics
            analytics = self.analytics_service.get_quiz_analytics(user_id=user.user_id)
            contributor_analytics = self.analytics_service.get_contributor_analytics(user.user_id)
            
            message = f"👤 **{user.username or user.first_name or 'Student'}**\n\n"
            
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
            
            if user.role in ['admin', 'super_admin']:
                keyboard.append([InlineKeyboardButton("📤 My Contributions", callback_data="my_contributions")])
            
            keyboard.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
            
            await update.message.reply_text(
                message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            session.close()
            
        except Exception as e:
            logger.error(f"Error in my_stats_command: {e}")
            await update.message.reply_text("❌ Error loading personal stats.")
