#!/usr/bin/env python3
"""
Script to populate the database with sample data
"""

import json
import asyncio
from sqlalchemy import select
from database.db import AsyncSessionLocal, create_tables_sync
from database.models import (
    University, Course, Unit, Topic, Question, Admin
)

async def populate_database():
    """Populate database with sample data"""
    
    # Create tables first
    create_tables_sync()
    
    # Load sample data
    with open('data/sample_questions.json', 'r') as f:
        data = json.load(f)
    
    async with AsyncSessionLocal() as session:
        try:
            # Create universities and their data
            for uni_data in data['universities']:
                # Create university
                university = University(name=uni_data['name'])
                session.add(university)
                await session.flush()  # Get the ID
                
                print(f"Created university: {university.name}")
                
                # Create courses
                for course_data in uni_data['courses']:
                    course = Course(
                        name=course_data['name'],
                        university_id=university.id
                    )
                    session.add(course)
                    await session.flush()
                    
                    print(f"  Created course: {course.name}")
                    
                    # Create units
                    for unit_data in course_data['units']:
                        unit = Unit(
                            name=unit_data['name'],
                            course_id=course.id,
                            year=unit_data['year']
                        )
                        session.add(unit)
                        await session.flush()
                        
                        print(f"    Created unit: {unit.name}")
                        
                        # Create topics and questions
                        for topic_data in unit_data['topics']:
                            topic = Topic(
                                name=topic_data['name'],
                                unit_id=unit.id
                            )
                            session.add(topic)
                            await session.flush()
                            
                            print(f"      Created topic: {topic.name}")
                            
                            # Create questions
                            for question_data in topic_data['questions']:
                                question = Question(
                                    question_text=question_data['question_text'],
                                    option_a=question_data['option_a'],
                                    option_b=question_data['option_b'],
                                    option_c=question_data['option_c'],
                                    option_d=question_data['option_d'],
                                    correct_answer=question_data['correct_answer'],
                                    explanation=question_data['explanation'],
                                    difficulty=question_data['difficulty'],
                                    topic_id=topic.id
                                )
                                session.add(question)
                                
                                print(f"        Created question: {question_data['question_text'][:50]}...")
            
            # Create a default admin user (replace with your Telegram ID)
            admin = Admin(
                telegram_id=123456789,  # Replace with your actual Telegram ID
                username="admin",
                first_name="Admin",
                last_name="User",
                is_super_admin=True
            )
            session.add(admin)
            print("Created admin user")
            
            # Commit all changes
            await session.commit()
            print("Database populated successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"Error populating database: {e}")
            raise

if __name__ == "__main__":
    asyncio.run(populate_database())
