from typing import List
from models import Question


def format_question(question: Question, index: int, total: int) -> str:
    """
    Format a question for display in Telegram.
    Returns formatted text with question, options, and uploader attribution.
    """
    # Format options
    options = "\n".join([
        f"{chr(65+i)}) {option}" for i, option in enumerate(question.options_json)
    ])
    
    # Add uploader attribution
    uploader = ""
    if question.uploader and question.uploader.username:
        uploader = f"\n\n_Uploaded by @{question.uploader.username}_"
    elif question.uploader and question.uploader.first_name:
        uploader = f"\n\n_Uploaded by {question.uploader.first_name}_"
    
    return f"Q{index}/{total}: {question.question_text}\n\n{options}{uploader}"


def format_quiz_result(session, topic_name: str) -> str:
    """
    Format quiz completion summary.
    """
    percentage = session.score_percent or 0
    grade = session.grade or "N/A"
    
    result_text = f"""✅ Quiz Completed!
Topic: {topic_name}
Correct: {session.correct_answers}/{session.total_questions}
Score: {percentage:.0f}%
Grade: {grade}

🧠 Keep studying, you're doing great!"""
    
    return result_text


def format_quiz_history(sessions: List) -> str:
    """
    Format quiz history for display.
    """
    if not sessions:
        return "📚 No quiz history found. Take your first quiz to get started!"
    
    history_text = "📚 Your Recent Quiz History:\n\n"
    
    for session in sessions:
        percentage = session.score_percent or 0
        grade = session.grade or "N/A"
        topic_name = session.topic.name if session.topic else "Unknown Topic"
        
        history_text += f"📖 {topic_name}\n"
        history_text += f"   Score: {session.correct_answers}/{session.total_questions} ({percentage:.0f}%) - Grade: {grade}\n"
        history_text += f"   Date: {session.completed_at.strftime('%Y-%m-%d %H:%M')}\n\n"
    
    return history_text


def format_answer_feedback(is_correct: bool, correct_answer: str, explanation: str = None) -> str:
    """
    Format feedback for a quiz answer.
    """
    if is_correct:
        feedback = "✅ Correct!"
    else:
        feedback = f"❌ Incorrect — correct answer: **{correct_answer}**"
    
    if explanation:
        feedback += f"\n\n💡 {explanation}"
    
    return feedback


def get_grade_emoji(grade: str) -> str:
    """
    Get emoji for grade display.
    """
    grade_emojis = {
        "A": "🥇",
        "B": "🥈", 
        "C": "🥉",
        "D": "📚",
        "E": "💪",
        "Incomplete": "⏸️"
    }
    return grade_emojis.get(grade, "📝")


def format_question_preview(question: dict, index: int) -> str:
    """
    Format a question for preview display during upload review.
    """
    preview = f"**Q{index}:** {question['question']}\n\n"
    
    for i, option in enumerate(question['options']):
        letter = chr(65 + i)  # A, B, C, D
        marker = " ✅" if letter == question['correct_answer'] else ""
        preview += f"{letter}) {option}{marker}\n"
    
    if question.get('explanation'):
        preview += f"\n💡 **Explanation:** {question['explanation']}"
    
    if question.get('source'):
        preview += f"\n📚 **Source:** {question['source']}"
    
    return preview


def format_upload_summary(questions: list, uploaded_count: int) -> str:
    """
    Format upload summary for display.
    """
    summary = f"📤 **Upload Summary**\n\n"
    summary += f"**Total Questions:** {len(questions)}\n"
    summary += f"**Successfully Uploaded:** {uploaded_count}\n"
    
    if uploaded_count < len(questions):
        summary += f"**Failed:** {len(questions) - uploaded_count}\n"
    
    return summary
