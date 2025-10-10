from telegram.ext import BaseFilter
from telegram import Update
from typing import Optional

class AdminFilter(BaseFilter):
    """Filter to check if user is admin"""
    
    def filter(self, message):
        # This will be implemented with database check in the handler
        return True  # Placeholder

class CallbackDataFilter(BaseFilter):
    """Filter for specific callback data patterns"""
    
    def __init__(self, pattern: str):
        self.pattern = pattern
    
    def filter(self, update: Update) -> bool:
        if not update.callback_query:
            return False
        return update.callback_query.data.startswith(self.pattern)

# Specific callback filters
class UniversityCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("university_")

class CourseCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("course_")

class UnitCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("unit_")

class TopicCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("topic_")

class PaperCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("paper_")

class QuizCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("quiz_")

class AnswerCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("answer_")

class AdminCallbackFilter(CallbackDataFilter):
    def __init__(self):
        super().__init__("admin_")
