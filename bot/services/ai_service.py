"""
AI service for text extraction and MCQ parsing using Google Gemini API.
"""
import json
import base64
import requests
import os
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class AIService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.gemini_base_url = "https://generativelanguage.googleapis.com/v1beta"
        
        if not self.gemini_api_key:
            logger.warning("GEMINI_API_KEY not found in environment variables")
    
    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using Google Vision API or Gemini Vision.
        """
        try:
            if not self.gemini_api_key:
                return "Error: Gemini API key not configured"
            
            # Read image file
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')
            
            # Use Gemini Vision API
            url = f"{self.gemini_base_url}/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Extract all text from this image. Return only the raw text without any formatting or explanations."},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_data
                            }
                        }
                    ]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                extracted_text = result['candidates'][0]['content']['parts'][0]['text']
                return extracted_text
            else:
                return "No text found in image"
                
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return f"Error extracting text: {str(e)}"
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text from PDF using Gemini Vision API.
        Note: This is a simplified implementation. For production, consider using PyPDF2 or similar.
        """
        try:
            # For now, return a placeholder. In production, you'd use a proper PDF text extraction library
            return "PDF text extraction not yet implemented. Please convert PDF to images or copy text manually."
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return f"Error extracting text from PDF: {str(e)}"
    
    def parse_mcqs_with_ai(self, text: str) -> List[Dict]:
        """
        Parse text to extract multiple choice questions using Gemini AI.
        """
        try:
            if not self.gemini_api_key:
                # Return mock data for testing
                return self._get_mock_questions()
            
            prompt = f"""
            Analyze the following text and extract all multiple choice questions (MCQs). 
            Return a JSON array where each question has this structure:
            
            {{
                "question": "The question text",
                "options": ["Option A", "Option B", "Option C", "Option D"],
                "correct_answer": "The correct option letter (A, B, C, or D)",
                "explanation": "Brief explanation if available",
                "source": "Source reference if mentioned (e.g., 'CAT 1 2022')"
            }}
            
            Rules:
            1. Only extract complete MCQs with 4 options (A, B, C, D)
            2. If correct answer is marked with *, bold, underline, or similar, identify it
            3. If no clear correct answer is indicated, mark as "Unknown"
            4. Clean up formatting and remove question numbers
            5. If explanation is provided, include it
            6. If source is mentioned, include it
            7. Return empty array if no valid MCQs found
            
            Text to analyze:
            {text}
            
            Return only valid JSON array, no other text.
            """
            
            url = f"{self.gemini_base_url}/models/gemini-1.5-flash:generateContent?key={self.gemini_api_key}"
            
            payload = {
                "contents": [{
                    "parts": [{"text": prompt}]
                }]
            }
            
            response = requests.post(url, json=payload, timeout=60)
            response.raise_for_status()
            
            result = response.json()
            if 'candidates' in result and len(result['candidates']) > 0:
                ai_response = result['candidates'][0]['content']['parts'][0]['text']
                
                # Try to parse JSON response
                try:
                    # Clean up the response to extract JSON
                    ai_response = ai_response.strip()
                    if ai_response.startswith('```json'):
                        ai_response = ai_response[7:]
                    if ai_response.endswith('```'):
                        ai_response = ai_response[:-3]
                    
                    questions = json.loads(ai_response)
                    
                    # Validate and clean questions
                    validated_questions = []
                    for q in questions:
                        if self._validate_question(q):
                            validated_questions.append(self._clean_question(q))
                    
                    return validated_questions
                    
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse AI response as JSON: {e}")
                    return [{"error": f"Failed to parse AI response: {ai_response[:200]}..."}]
            else:
                return [{"error": "No response from AI service"}]
                
        except Exception as e:
            logger.error(f"Error parsing MCQs with AI: {e}")
            return [{"error": f"AI parsing failed: {str(e)}"}]
    
    def _validate_question(self, question: Dict) -> bool:
        """Validate that a question has required fields."""
        required_fields = ['question', 'options', 'correct_answer']
        
        for field in required_fields:
            if field not in question or not question[field]:
                return False
        
        # Check that options is a list with 4 items
        if not isinstance(question['options'], list) or len(question['options']) != 4:
            return False
        
        # Check that correct_answer is A, B, C, or D
        if question['correct_answer'] not in ['A', 'B', 'C', 'D']:
            return False
        
        return True
    
    def _clean_question(self, question: Dict) -> Dict:
        """Clean and standardize question data."""
        cleaned = {
            'question': question['question'].strip(),
            'options': [opt.strip() for opt in question['options']],
            'correct_answer': question['correct_answer'].upper(),
            'explanation': question.get('explanation', '').strip() if question.get('explanation') else '',
            'source': question.get('source', '').strip() if question.get('source') else ''
        }
        
        return cleaned
    
    def _get_mock_questions(self) -> List[Dict]:
        """
        Return mock questions for testing when API key is not available.
        """
        return [
            {
                "question": "What is the main neurotransmitter in the sympathetic nervous system?",
                "options": ["Acetylcholine", "Noradrenaline", "Dopamine", "Serotonin"],
                "correct_answer": "B",
                "explanation": "Noradrenaline (norepinephrine) is the primary neurotransmitter released by postganglionic sympathetic neurons.",
                "source": "Mock Test"
            },
            {
                "question": "Which cranial nerve is responsible for facial expression?",
                "options": ["Trigeminal (V)", "Facial (VII)", "Glossopharyngeal (IX)", "Vagus (X)"],
                "correct_answer": "B",
                "explanation": "The facial nerve (cranial nerve VII) innervates the muscles of facial expression.",
                "source": "Mock Test"
            },
            {
                "question": "What is the normal range for adult blood pressure?",
                "options": ["<120/80 mmHg", "120-139/80-89 mmHg", "140-159/90-99 mmHg", ">160/100 mmHg"],
                "correct_answer": "A",
                "explanation": "Normal blood pressure is considered to be less than 120/80 mmHg.",
                "source": "Mock Test"
            }
        ]
    
    def get_ai_confidence(self, questions: List[Dict]) -> str:
        """
        Analyze questions and return confidence level.
        """
        if not questions:
            return "No questions found"
        
        if any('error' in q for q in questions):
            return "Low - AI extraction errors detected"
        
        # Simple confidence scoring
        total_questions = len(questions)
        complete_questions = sum(1 for q in questions if q.get('explanation'))
        
        if total_questions == 0:
            return "No questions found"
        
        completeness_ratio = complete_questions / total_questions
        
        if completeness_ratio >= 0.8:
            return f"High - {total_questions} questions extracted with good structure"
        elif completeness_ratio >= 0.5:
            return f"Medium - {total_questions} questions extracted, some missing explanations"
        else:
            return f"Low - {total_questions} questions extracted, many incomplete"
