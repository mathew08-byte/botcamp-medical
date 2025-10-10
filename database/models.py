from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)  # Telegram ID
    role = Column(String, default="student")  # student / admin / super_admin
    name = Column(String, nullable=True)  # Telegram username or set name
    university = Column(String, nullable=True)  # e.g. "University of Nairobi"
    course = Column(String, nullable=True)  # e.g. "MBChB"
    year = Column(Integer, nullable=True)  # Year of study
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional fields for enhanced functionality
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    
    # Analytics
    upload_count = Column(Integer, default=0)
    approved_count = Column(Integer, default=0)
    flagged_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    average_moderation_score = Column(Integer, nullable=True)
    total_quizzes_taken = Column(Integer, default=0)
    average_accuracy = Column(Integer, nullable=True)
    
    # Relationships
    quiz_sessions = relationship("QuizSession", back_populates="user")
    quiz_results = relationship("QuizResult", back_populates="user")
    uploaded_questions = relationship("Question", foreign_keys="Question.uploader_id", back_populates="uploader")

class University(Base):
    __tablename__ = "universities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

class Course(Base):
    __tablename__ = "courses"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id"))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    university = relationship("University")
    units = relationship("Unit", back_populates="course")

class Unit(Base):
    __tablename__ = "units"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    year = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    course = relationship("Course", back_populates="units")
    topics = relationship("Topic", back_populates="unit")

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    unit_id = Column(Integer, ForeignKey("units.id"))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    unit = relationship("Unit", back_populates="topics")
    questions = relationship("Question", back_populates="topic_rel")

class Paper(Base):
    __tablename__ = "papers"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    topic_id = Column(Integer, ForeignKey("topics.id"))
    year = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    topic = relationship("Topic")
    questions = relationship("Question", back_populates="paper")

class Question(Base):
    __tablename__ = "questions"
    
    question_id = Column(Integer, primary_key=True, index=True)
    unit = Column(String, nullable=True)  # Unit name (e.g. Anatomy)
    topic = Column(String, nullable=True)  # Topic name
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_option = Column(String, nullable=False)  # "A"/"B"/"C"/"D"
    explanation = Column(Text, nullable=True)
    uploader_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    verified_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Additional fields for enhanced functionality
    topic_id = Column(Integer, ForeignKey("topics.id"), nullable=True)
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)
    difficulty = Column(String, default="medium")  # 'easy', 'medium', 'hard'
    uploader_username = Column(String, nullable=True)
    source = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    topic_rel = relationship("Topic", back_populates="questions")
    paper = relationship("Paper", back_populates="questions")
    uploader = relationship("User", foreign_keys=[uploader_id], back_populates="uploaded_questions")
    verifier = relationship("User", foreign_keys=[verified_by])
    
    # Moderation
    moderation_score = Column(Integer, nullable=True)
    moderation_comments = Column(Text, nullable=True)
    moderated_by_ai = Column(Boolean, default=False)
    needs_review = Column(Boolean, default=False)
    reviewed_by_admin_id = Column(Integer, ForeignKey("admins.id"), nullable=True)

class QuizSession(Base):
    __tablename__ = "quiz_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    paper_id = Column(Integer, ForeignKey("papers.id"), nullable=True)
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    current_question = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    score_percentage = Column(Integer, nullable=True)
    grade = Column(String, nullable=True)
    # Analytics
    duration_seconds = Column(Integer, nullable=True)
    accuracy = Column(Integer, nullable=True)
    topic_accuracy_breakdown = Column(JSON, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="quiz_sessions")
    topic = relationship("Topic")
    paper = relationship("Paper")
    answers = relationship("QuizAnswer", back_populates="session")

class QuizAnswer(Base):
    __tablename__ = "quiz_answers"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("quiz_sessions.id"))
    question_id = Column(Integer, ForeignKey("questions.question_id"))
    user_answer = Column(String, nullable=False)  # 'A', 'B', 'C', or 'D'
    is_correct = Column(Boolean, default=False)
    answered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    session = relationship("QuizSession", back_populates="answers")
    question = relationship("Question")

class Admin(Base):
    __tablename__ = "admins"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    is_super_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class SystemLog(Base):
    __tablename__ = "system_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True)
    action = Column(String, nullable=False)
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)

class EventLog(Base):
    __tablename__ = "event_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, nullable=True)
    event_type = Column(String, nullable=False)
    context = Column(JSON, nullable=True)

class ErrorLog(Base):
    __tablename__ = "error_logs"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    module = Column(String, nullable=False)
    severity = Column(String, default="warning")
    message = Column(Text, nullable=False)
    details = Column(Text, nullable=True)
    resolved = Column(Boolean, default=False)

class TelemetrySnapshot(Base):
    __tablename__ = "telemetry_snapshots"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    data = Column(JSON, nullable=False)

class DailyStats(Base):
    __tablename__ = "daily_stats"
    id = Column(Integer, primary_key=True, index=True)
    date = Column(String, index=True)
    data = Column(JSON, nullable=False)

class UserActivity(Base):
    __tablename__ = "user_activity"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    last_activity = Column(DateTime, default=datetime.utcnow)
    quizzes_completed = Column(Integer, default=0)
    avg_score = Column(Integer, nullable=True)
    uploads_made = Column(Integer, default=0)

# New tables according to specification
class QuizResult(Base):
    __tablename__ = "quiz_results"
    
    result_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    unit = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    score = Column(Integer, default=0)
    total_questions = Column(Integer, default=0)
    correct = Column(Integer, default=0)
    wrong = Column(Integer, default=0)
    date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="quiz_results")

class AdminUpload(Base):
    __tablename__ = "admin_uploads"
    
    upload_id = Column(Integer, primary_key=True, index=True)
    uploader_id = Column(Integer, ForeignKey("users.user_id"))
    upload_type = Column(String, nullable=False)  # text/pdf/image
    status = Column(String, default="pending")  # pending/approved/rejected
    ai_model = Column(String, nullable=True)  # Gemini/GPT
    questions_detected = Column(Integer, default=0)
    approved_questions = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    uploader = relationship("User")

class Announcement(Base):
    __tablename__ = "announcements"
    
    message_id = Column(Integer, primary_key=True, index=True)
    message_text = Column(Text, nullable=False)
    created_by = Column(Integer, ForeignKey("users.user_id"))
    date = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    creator = relationship("User")

class UserState(Base):
    __tablename__ = "user_states"
    
    user_id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False)  # student/admin/super_admin
    university = Column(String, nullable=True)
    course = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    unit = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    last_action = Column(String, nullable=True)  # last interaction (quiz, upload, etc.)
    updated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id])

class UploadBatch(Base):
    __tablename__ = "upload_batches"
    
    batch_id = Column(Integer, primary_key=True, index=True)
    uploader_id = Column(Integer, ForeignKey("users.user_id"))
    status = Column(String, default="draft")  # draft | review | approved | rejected
    locked_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    locked_at = Column(DateTime, nullable=True)
    questions_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    uploader = relationship("User", foreign_keys=[uploader_id])
    locker = relationship("User", foreign_keys=[locked_by])
    items = relationship("UploadItem", back_populates="batch", cascade="all, delete-orphan")

class UploadItem(Base):
    __tablename__ = "upload_items"
    
    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.batch_id"), index=True)
    raw_text = Column(Text, nullable=True)
    parsed_json = Column(JSON, nullable=True)
    reviewer_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    status = Column(String, default="draft", index=True)
    notes = Column(Text, nullable=True)
    
    batch = relationship("UploadBatch", back_populates="items")
    reviewer = relationship("User")

class UploadAudit(Base):
    __tablename__ = "upload_audits"
    
    audit_id = Column(Integer, primary_key=True, index=True)
    upload_id = Column(Integer, ForeignKey("questions.question_id"))
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    admin_id = Column(Integer, ForeignKey("users.user_id"))
    action = Column(String, nullable=False)  # edit, approve, reject, etc.
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    question = relationship("Question")
    admin = relationship("User")

class AdminScope(Base):
    __tablename__ = "admin_scopes"
    
    id = Column(Integer, primary_key=True, index=True)
    admin_id = Column(Integer, ForeignKey("users.user_id"))
    university_id = Column(Integer, ForeignKey("universities.id"))
    course_id = Column(Integer, ForeignKey("courses.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    admin = relationship("User")
    university = relationship("University")
    course = relationship("Course")

class AdminAccessCode(Base):
    __tablename__ = "admin_access_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, nullable=False)
    created_by = Column(Integer, ForeignKey("users.user_id"))
    is_active = Column(Boolean, default=True)
    used_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    user = relationship("User", foreign_keys=[used_by])

class QuestionUpload(Base):
    __tablename__ = "question_uploads"
    
    upload_id = Column(Integer, primary_key=True, index=True)
    uploaded_by = Column(Integer, ForeignKey("users.user_id"))
    approved_by = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    upload_type = Column(String, nullable=False)  # "text", "pdf", "image"
    ai_processed = Column(Boolean, default=False)
    status = Column(String, default="pending")  # "pending", "approved", "rejected"
    questions_count = Column(Integer, default=0)
    ai_confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])
    approver = relationship("User", foreign_keys=[approved_by])

class RoleAuditLog(Base):
    __tablename__ = "role_audit_logs"
    
    log_id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"))
    action = Column(String, nullable=False)  # "role_change", "access_granted", "access_denied", etc.
    old_role = Column(String, nullable=True)
    new_role = Column(String, nullable=True)
    details = Column(Text, nullable=True)
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
