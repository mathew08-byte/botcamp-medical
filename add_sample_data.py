#!/usr/bin/env python3
"""
Simple script to add sample data to the database
"""

from database.db import SessionLocal, create_tables
from database.models import University, Course, Unit, Topic, Question, Admin

def add_sample_data():
    """Add sample data to the database"""
    
    # Create tables first
    create_tables()
    
    db = SessionLocal()
    try:
        # Check if data already exists
        if db.query(University).first():
            print("Sample data already exists!")
            return
        
        # Create University of Nairobi
        uni = University(name="University of Nairobi")
        db.add(uni)
        db.flush()
        
        # Create MBChB course
        course = Course(name="Bachelor of Medicine and Bachelor of Surgery (MBChB)", university_id=uni.id)
        db.add(course)
        db.flush()
        
        # Create Anatomy unit
        unit = Unit(name="Anatomy", course_id=course.id, year="1")
        db.add(unit)
        db.flush()
        
        # Create General Anatomy topic
        topic = Topic(name="General Anatomy", unit_id=unit.id)
        db.add(topic)
        db.flush()
        
        # Add sample questions
        questions = [
            {
                "question_text": "Which of the following is the largest bone in the human body?",
                "option_a": "Femur",
                "option_b": "Tibia", 
                "option_c": "Humerus",
                "option_d": "Radius",
                "correct_answer": "A",
                "explanation": "The femur (thigh bone) is the longest and strongest bone in the human body.",
                "difficulty": "easy"
            },
            {
                "question_text": "The anatomical position is characterized by:",
                "option_a": "Palms facing backward",
                "option_b": "Palms facing forward",
                "option_c": "Arms at sides",
                "option_d": "Both B and C",
                "correct_answer": "D",
                "explanation": "In anatomical position, the body is upright with palms facing forward and arms at the sides.",
                "difficulty": "medium"
            },
            {
                "question_text": "Which chamber of the heart receives oxygenated blood from the lungs?",
                "option_a": "Right atrium",
                "option_b": "Left atrium",
                "option_c": "Right ventricle",
                "option_d": "Left ventricle",
                "correct_answer": "B",
                "explanation": "The left atrium receives oxygenated blood from the lungs via the pulmonary veins.",
                "difficulty": "medium"
            }
        ]
        
        for q_data in questions:
            question = Question(
                question_text=q_data["question_text"],
                option_a=q_data["option_a"],
                option_b=q_data["option_b"],
                option_c=q_data["option_c"],
                option_d=q_data["option_d"],
                correct_answer=q_data["correct_answer"],
                explanation=q_data["explanation"],
                difficulty=q_data["difficulty"],
                topic_id=topic.id
            )
            db.add(question)
        
        # Create admin user (replace with your Telegram ID)
        admin = Admin(
            telegram_id=123456789,  # Replace with your actual Telegram ID
            username="admin",
            first_name="Admin",
            last_name="User",
            is_super_admin=True
        )
        db.add(admin)
        
        # Commit all changes
        db.commit()
        print("Sample data added successfully!")
        print(f"Created: 1 university, 1 course, 1 unit, 1 topic, {len(questions)} questions, 1 admin")
        
    except Exception as e:
        db.rollback()
        print(f"Error adding sample data: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_data()
