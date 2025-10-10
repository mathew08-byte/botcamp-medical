from telegram import InlineKeyboardMarkup, InlineKeyboardButton


def student_main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 Take Quiz", callback_data="stu_take_quiz")],
        [InlineKeyboardButton("📊 My Results", callback_data="stu_results")],
        [InlineKeyboardButton("📈 My Stats", callback_data="my_stats")],
        [InlineKeyboardButton("📊 Quiz Analytics", callback_data="analytics_quizzes")],
        [InlineKeyboardButton("ℹ️ About BotCamp", callback_data="stu_about")],
    ])


