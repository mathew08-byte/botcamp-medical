"""
Add sample questions to the database for testing
"""

from database.db import SessionLocal, create_tables_sync
from database.models import Question, User
import logging

logger = logging.getLogger(__name__)

def add_sample_questions():
    """Add sample medical questions to the database"""
    create_tables_sync()
    db = SessionLocal()
    
    try:
        # Check if questions already exist
        existing_questions = db.query(Question).count()
        if existing_questions > 0:
            print(f"Database already has {existing_questions} questions. Skipping sample data.")
            return
        
        # Sample questions for Human Anatomy - Thorax
        sample_questions = [
            {
                "unit": "Human Anatomy",
                "topic": "Thorax",
                "question_text": "Which of the following structures is NOT found in the mediastinum?",
                "option_a": "Heart",
                "option_b": "Trachea",
                "option_c": "Lungs",
                "option_d": "Esophagus",
                "correct_option": "C",
                "explanation": "The lungs are located in the pleural cavities, not in the mediastinum. The mediastinum contains the heart, trachea, esophagus, and other structures."
            },
            {
                "unit": "Human Anatomy",
                "topic": "Thorax",
                "question_text": "The right lung has how many lobes?",
                "option_a": "Two",
                "option_b": "Three",
                "option_c": "Four",
                "option_d": "Five",
                "correct_option": "B",
                "explanation": "The right lung has three lobes: superior, middle, and inferior. The left lung has only two lobes: superior and inferior."
            },
            {
                "unit": "Human Anatomy",
                "topic": "Thorax",
                "question_text": "Which rib is the first rib that can be palpated?",
                "option_a": "1st rib",
                "option_b": "2nd rib",
                "option_c": "3rd rib",
                "option_d": "4th rib",
                "correct_option": "B",
                "explanation": "The 2nd rib is the first rib that can be palpated, as the 1st rib is located behind the clavicle."
            },
            {
                "unit": "Human Anatomy",
                "topic": "Upper Limb",
                "question_text": "Which muscle is the primary flexor of the elbow joint?",
                "option_a": "Biceps brachii",
                "option_b": "Triceps brachii",
                "option_c": "Brachialis",
                "option_d": "Brachioradialis",
                "correct_option": "C",
                "explanation": "The brachialis is the primary flexor of the elbow joint, as it crosses only the elbow joint and has the most direct line of pull."
            },
            {
                "unit": "Human Anatomy",
                "topic": "Upper Limb",
                "question_text": "The median nerve passes through which structure in the wrist?",
                "option_a": "Carpal tunnel",
                "option_b": "Guyon's canal",
                "option_c": "Anatomical snuffbox",
                "option_d": "Cubital fossa",
                "correct_option": "A",
                "explanation": "The median nerve passes through the carpal tunnel along with the flexor tendons of the fingers."
            },
            {
                "unit": "Physiology I",
                "topic": "Cardiovascular",
                "question_text": "What is the normal range for systolic blood pressure in adults?",
                "option_a": "90-120 mmHg",
                "option_b": "120-140 mmHg",
                "option_c": "140-160 mmHg",
                "option_d": "160-180 mmHg",
                "correct_option": "A",
                "explanation": "Normal systolic blood pressure in adults is typically 90-120 mmHg. Values above 140 mmHg are considered hypertensive."
            },
            {
                "unit": "Physiology I",
                "topic": "Cardiovascular",
                "question_text": "Which chamber of the heart has the thickest wall?",
                "option_a": "Right atrium",
                "option_b": "Left atrium",
                "option_c": "Right ventricle",
                "option_d": "Left ventricle",
                "correct_option": "D",
                "explanation": "The left ventricle has the thickest wall because it must pump blood against the high pressure of the systemic circulation."
            },
            {
                "unit": "Biochemistry",
                "topic": "Carbohydrates",
                "question_text": "What is the primary storage form of glucose in the liver?",
                "option_a": "Glucose",
                "option_b": "Fructose",
                "option_c": "Glycogen",
                "option_d": "Starch",
                "correct_option": "C",
                "explanation": "Glycogen is the primary storage form of glucose in the liver and muscle. It can be rapidly broken down to release glucose when needed."
            },
            {
                "unit": "Biochemistry",
                "topic": "Proteins",
                "question_text": "Which amino acid is essential and cannot be synthesized by the human body?",
                "option_a": "Alanine",
                "option_b": "Glycine",
                "option_c": "Histidine",
                "option_d": "Glutamine",
                "correct_option": "C",
                "explanation": "Histidine is one of the essential amino acids that cannot be synthesized by the human body and must be obtained from the diet."
            },
            {
                "unit": "Microbiology",
                "topic": "Bacteriology",
                "question_text": "Which staining method is used to differentiate between Gram-positive and Gram-negative bacteria?",
                "option_a": "Acid-fast stain",
                "option_b": "Gram stain",
                "option_c": "Capsule stain",
                "option_d": "Flagella stain",
                "correct_option": "B",
                "explanation": "The Gram stain is the standard method used to differentiate between Gram-positive (purple) and Gram-negative (pink) bacteria based on their cell wall structure."
            }
        ]
        
        # Add questions to database
        for q_data in sample_questions:
            question = Question(
                unit=q_data["unit"],
                topic=q_data["topic"],
                question_text=q_data["question_text"],
                option_a=q_data["option_a"],
                option_b=q_data["option_b"],
                option_c=q_data["option_c"],
                option_d=q_data["option_d"],
                correct_option=q_data["correct_option"],
                explanation=q_data["explanation"],
                is_active=True
            )
            db.add(question)
        
        db.commit()
        print(f"Successfully added {len(sample_questions)} sample questions to the database.")
        
    except Exception as e:
        logger.error(f"Error adding sample questions: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    add_sample_questions()
