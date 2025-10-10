from datetime import datetime
from enum import Enum
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON, Enum as SAEnum
)
from sqlalchemy.orm import relationship, declarative_base


Base = declarative_base()


class RoleEnum(str, Enum):
    student = "student"
    admin = "admin"
    super_admin = "super_admin"


class UploadStatusEnum(str, Enum):
    draft = "draft"
    review = "review"
    approved = "approved"
    rejected = "rejected"


class University(Base):
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

    courses = relationship("Course", back_populates="university", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True)
    university_id = Column(Integer, ForeignKey("universities.id"), index=True)
    name = Column(String, unique=True, index=True)
    is_active = Column(Boolean, default=True)

    university = relationship("University", back_populates="courses")
    units = relationship("Unit", back_populates="course", cascade="all, delete-orphan")


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True)
    course_id = Column(Integer, ForeignKey("courses.id"), index=True)
    name = Column(String, index=True)
    year = Column(Integer, index=True)
    is_active = Column(Boolean, default=True)

    course = relationship("Course", back_populates="units")
    topics = relationship("Topic", back_populates="unit", cascade="all, delete-orphan")


class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey("units.id"), index=True)
    name = Column(String, index=True)
    is_active = Column(Boolean, default=True)

    unit = relationship("Unit", back_populates="topics")
    papers = relationship("Paper", back_populates="topic", cascade="all, delete-orphan")
    # Remove the questions relationship for now since the foreign key doesn't exist


class Paper(Base):
    __tablename__ = "papers"

    id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey("topics.id"), index=True)
    name = Column(String, index=True)
    year = Column(Integer, nullable=True)
    is_active = Column(Boolean, default=True)

    topic = relationship("Topic", back_populates="papers")
    # Remove the questions relationship for now since the foreign key doesn't exist


class User(Base):
    __tablename__ = "users"

    user_id = Column(Integer, primary_key=True)
    role = Column(String, nullable=True)
    name = Column(String, nullable=True)
    university = Column(String, nullable=True)
    course = Column(String, nullable=True)
    year = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)
    telegram_id = Column(Integer, nullable=True)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    upload_count = Column(Integer, nullable=True)
    approved_count = Column(Integer, nullable=True)
    flagged_count = Column(Integer, nullable=True)
    rejected_count = Column(Integer, nullable=True)
    average_moderation_score = Column(Integer, nullable=True)
    total_quizzes_taken = Column(Integer, nullable=True)
    average_accuracy = Column(Integer, nullable=True)

    # Helper properties to maintain compatibility
    @property
    def id(self):
        return self.user_id


class Question(Base):
    __tablename__ = "questions"

    question_id = Column(Integer, primary_key=True)
    unit = Column(String, nullable=True)
    topic = Column(String, nullable=True)
    question_text = Column(Text, nullable=False)
    option_a = Column(Text, nullable=False)
    option_b = Column(Text, nullable=False)
    option_c = Column(Text, nullable=False)
    option_d = Column(Text, nullable=False)
    correct_option = Column(String, nullable=False)
    explanation = Column(Text, nullable=True)
    uploader_id = Column(Integer, nullable=True)
    verified_by = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=True)
    topic_id = Column(Integer, nullable=True)
    paper_id = Column(Integer, nullable=True)
    difficulty = Column(String, nullable=True)
    uploader_username = Column(String, nullable=True)
    source = Column(String, nullable=True)
    is_active = Column(Boolean, nullable=True)
    moderation_score = Column(Integer, nullable=True)
    moderation_comments = Column(Text, nullable=True)
    moderated_by_ai = Column(Boolean, nullable=True)
    needs_review = Column(Boolean, nullable=True)
    reviewed_by_admin_id = Column(Integer, nullable=True)

    # Helper properties to maintain compatibility
    @property
    def id(self):
        return self.question_id
    
    @property
    def options_json(self):
        return [self.option_a, self.option_b, self.option_c, self.option_d]
    
    @property
    def correct_index(self):
        return ord(self.correct_option) - ord('A') if self.correct_option else 0
    
    @property
    def uploader_user_id(self):
        return self.uploader_id


class UploadBatch(Base):
    __tablename__ = "upload_batches"

    id = Column(Integer, primary_key=True)
    uploader_user_id = Column(Integer, ForeignKey("users.user_id"), index=True)
    source_type = Column(String)  # pdf|image|text
    source_ref = Column(String)   # file name or message id
    status = Column(SAEnum(UploadStatusEnum), default=UploadStatusEnum.draft, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    uploader = relationship("User")
    items = relationship("UploadItem", back_populates="batch", cascade="all, delete-orphan")


class UploadItem(Base):
    __tablename__ = "upload_items"

    id = Column(Integer, primary_key=True)
    batch_id = Column(Integer, ForeignKey("upload_batches.id"), index=True)
    raw_text = Column(Text)
    parsed_json = Column(JSON)
    reviewer_user_id = Column(Integer, ForeignKey("users.user_id"), nullable=True)
    status = Column(SAEnum(UploadStatusEnum), default=UploadStatusEnum.draft, index=True)
    notes = Column(Text, nullable=True)

    batch = relationship("UploadBatch", back_populates="items")
    reviewer = relationship("User")


class QuizSession(Base):
    __tablename__ = "quiz_sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=True)
    topic_id = Column(Integer, nullable=True)
    paper_id = Column(Integer, nullable=True)
    total_questions = Column(Integer, nullable=True)
    correct_answers = Column(Integer, nullable=True)
    current_question = Column(Integer, nullable=True)
    is_completed = Column(Boolean, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    score_percentage = Column(Integer, nullable=True)
    grade = Column(String, nullable=True)
    duration_seconds = Column(Integer, nullable=True)
    accuracy = Column(Integer, nullable=True)
    question_ids = Column(Text, nullable=True)  # Comma-separated question IDs
    score_percent = Column(Integer, nullable=True)  # Final percentage score

    # Helper properties to maintain compatibility
    @property
    def current_index(self):
        return self.current_question or 0
    
    @current_index.setter
    def current_index(self, value):
        self.current_question = value


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, nullable=True)
    question_id = Column(Integer, nullable=True)
    user_answer = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    answered_at = Column(DateTime, nullable=True)

    # Helper properties to maintain compatibility
    @property
    def user_answer_index(self):
        return ord(self.user_answer) - ord('A') if self.user_answer else 0
    
    @user_answer_index.setter
    def user_answer_index(self, value):
        self.user_answer = chr(65 + value) if value is not None else None


