"""
AI Question Parser Service for BotCamp Medical
Implements Part 5 - Quiz Upload Flow + AI Integration with Gemini AI
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional, Tuple
import os
from datetime import datetime
import google.generativeai as genai
from PIL import Image
import io

logger = logging.getLogger(__name__)

class AIQuestionParser:
    def __init__(self):
        self.api_key = self._get_gemini_api_key()
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel("gemini-1.5-flash")
        else:
            self.model = None
            logger.warning("Gemini API key not found. AI parsing will be disabled.")
    
    def _get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key from environment or file"""
        # Try environment variable first
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API")
        
        # Try reading from file
        if not api_key:
            try:
                with open("gemni_api", "r", encoding="utf-8") as f:
                    api_key = f.read().strip()
            except FileNotFoundError:
                pass
        
        return api_key
    
    def parse_text_questions(self, text: str, source_type: str = "text") -> Dict[str, Any]:
        """
        Parse text containing questions using Gemini AI
        Returns structured questions with confidence scores
        """
        try:
            if not self.model:
                return self._fallback_text_parsing(text)
            
            # Create prompt for Gemini AI
            prompt = self._create_parsing_prompt(text, source_type)
            
            # Send to Gemini AI
            response = self.model.generate_content(prompt)
            
            if not response.text:
                logger.error("Empty response from Gemini AI")
                return self._fallback_text_parsing(text)
            
            # Parse AI response
            parsed_data = self._parse_ai_response(response.text)
            
            # Validate and enhance parsed data
            validated_questions = self._validate_questions(parsed_data.get('questions', []))
            
            return {
                "success": True,
                "questions": validated_questions,
                "total_questions": len(validated_questions),
                "ai_confidence": parsed_data.get('overall_confidence', 0.8),
                "source_type": source_type,
                "parsed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing text questions with AI: {e}")
            return self._fallback_text_parsing(text)
    
    def parse_image_questions(self, image_data: bytes) -> Dict[str, Any]:
        """
        Parse image containing questions using Gemini Vision
        """
        try:
            if not self.model:
                return {"success": False, "message": "AI service not available"}
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Create prompt for image analysis
            prompt = """Analyze this image and extract all multiple choice questions (MCQs) you can find.

For each question, identify:
1. The question text
2. Options A, B, C, D (or similar)
3. The correct answer (marked, circled, or indicated)
4. Any explanation provided

Return the data in this exact JSON format:
{
  "questions": [
    {
      "id": 1,
      "question_text": "Full question text here",
      "options": {
        "A": "Option A text",
        "B": "Option B text", 
        "C": "Option C text",
        "D": "Option D text"
      },
      "correct_answer": "A",
      "explanation": "Explanation if available",
      "ai_confidence": 0.95
    }
  ],
  "overall_confidence": 0.92
}

If you cannot clearly identify any questions, return {"questions": [], "overall_confidence": 0.0}"""
            
            # Send image to Gemini Vision
            response = self.model.generate_content([prompt, image])
            
            if not response.text:
                return {"success": False, "message": "No response from AI"}
            
            # Parse AI response
            parsed_data = self._parse_ai_response(response.text)
            
            # Validate questions
            validated_questions = self._validate_questions(parsed_data.get('questions', []))
            
            return {
                "success": True,
                "questions": validated_questions,
                "total_questions": len(validated_questions),
                "ai_confidence": parsed_data.get('overall_confidence', 0.7),
                "source_type": "image",
                "parsed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error parsing image questions: {e}")
            return {"success": False, "message": f"Error parsing image: {str(e)}"}
    
    def parse_pdf_questions(self, pdf_text: str) -> Dict[str, Any]:
        """
        Parse PDF text containing questions
        """
        try:
            # PDF text is already extracted, so we can use text parsing
            return self.parse_text_questions(pdf_text, "pdf")
            
        except Exception as e:
            logger.error(f"Error parsing PDF questions: {e}")
            return {"success": False, "message": f"Error parsing PDF: {str(e)}"}
    
    def _create_parsing_prompt(self, text: str, source_type: str) -> str:
        """Create prompt for Gemini AI based on source type"""
        
        base_prompt = f"""You are an expert at parsing medical multiple choice questions (MCQs). 

Analyze the following {source_type} content and extract all multiple choice questions you can find.

For each question, identify:
1. The question text (the stem)
2. All options (A, B, C, D or similar format)
3. The correct answer (marked as "Answer:", "Correct:", or similar)
4. Any explanation provided

Return the data in this exact JSON format:
{{
  "questions": [
    {{
      "id": 1,
      "question_text": "Full question text here",
      "options": {{
        "A": "Option A text",
        "B": "Option B text", 
        "C": "Option C text",
        "D": "Option D text"
      }},
      "correct_answer": "A",
      "explanation": "Explanation if available",
      "ai_confidence": 0.95
    }}
  ],
  "overall_confidence": 0.92
}}

Guidelines:
- Only extract complete questions with 4 options (A, B, C, D)
- If a question is incomplete or unclear, set ai_confidence low (< 0.5)
- Preserve the exact wording of questions and options
- If no explanation is provided, leave explanation field empty
- If you cannot find any valid questions, return {{"questions": [], "overall_confidence": 0.0}}

Content to analyze:
"""
        
        return base_prompt + "\n\n" + text
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON data"""
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                logger.error("No JSON found in AI response")
                return {"questions": [], "overall_confidence": 0.0}
                
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing AI response JSON: {e}")
            return {"questions": [], "overall_confidence": 0.0}
    
    def _validate_questions(self, questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean parsed questions"""
        validated = []
        
        for i, question in enumerate(questions):
            try:
                # Validate required fields
                if not all(key in question for key in ['question_text', 'options', 'correct_answer']):
                    continue
                
                # Validate options
                options = question.get('options', {})
                if not isinstance(options, dict) or len(options) != 4:
                    continue
                
                # Validate correct answer
                correct_answer = question.get('correct_answer', '').upper()
                if correct_answer not in ['A', 'B', 'C', 'D']:
                    continue
                
                # Clean and validate question text
                question_text = question.get('question_text', '').strip()
                if len(question_text) < 10:  # Minimum question length
                    continue
                
                # Clean options
                cleaned_options = {}
                for key in ['A', 'B', 'C', 'D']:
                    option_text = options.get(key, '').strip()
                    if option_text:
                        cleaned_options[key] = option_text
                
                if len(cleaned_options) != 4:
                    continue
                
                # Create validated question
                validated_question = {
                    "id": i + 1,
                    "question_text": question_text,
                    "options": cleaned_options,
                    "correct_answer": correct_answer,
                    "explanation": question.get('explanation', '').strip(),
                    "ai_confidence": min(max(question.get('ai_confidence', 0.8), 0.0), 1.0)
                }
                
                validated.append(validated_question)
                
            except Exception as e:
                logger.error(f"Error validating question {i}: {e}")
                continue
        
        return validated
    
    def _fallback_text_parsing(self, text: str) -> Dict[str, Any]:
        """Fallback parsing when AI is not available"""
        try:
            questions = []
            
            # Simple regex-based parsing
            question_pattern = r'(\d+\.?\s*.*?)\n\s*A\)?\s*(.*?)\n\s*B\)?\s*(.*?)\n\s*C\)?\s*(.*?)\n\s*D\)?\s*(.*?)\n\s*(?:Answer|Correct):\s*([ABCD])'
            
            matches = re.findall(question_pattern, text, re.DOTALL | re.IGNORECASE)
            
            for i, match in enumerate(matches):
                question_text = match[0].strip()
                options = {
                    "A": match[1].strip(),
                    "B": match[2].strip(),
                    "C": match[3].strip(),
                    "D": match[4].strip()
                }
                correct_answer = match[5].upper()
                
                if question_text and all(options.values()) and correct_answer in ['A', 'B', 'C', 'D']:
                    questions.append({
                        "id": i + 1,
                        "question_text": question_text,
                        "options": options,
                        "correct_answer": correct_answer,
                        "explanation": "",
                        "ai_confidence": 0.6  # Lower confidence for fallback
                    })
            
            return {
                "success": True,
                "questions": questions,
                "total_questions": len(questions),
                "ai_confidence": 0.6,
                "source_type": "text_fallback",
                "parsed_at": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error in fallback parsing: {e}")
            return {
                "success": False,
                "questions": [],
                "total_questions": 0,
                "ai_confidence": 0.0,
                "message": f"Parsing failed: {str(e)}"
            }
    
    def enhance_question_metadata(self, question: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance question with additional metadata"""
        try:
            enhanced = question.copy()
            
            # Add context metadata
            enhanced.update({
                "university": context.get("university", ""),
                "course": context.get("course", ""),
                "year": context.get("year", ""),
                "unit": context.get("unit", ""),
                "topic": context.get("topic", ""),
                "uploader_id": context.get("uploader_id"),
                "uploader_username": context.get("uploader_username", ""),
                "source_type": context.get("source_type", "text"),
                "upload_timestamp": datetime.utcnow().isoformat()
            })
            
            # Add difficulty estimation based on question length and complexity
            question_length = len(question.get("question_text", ""))
            options_length = sum(len(opt) for opt in question.get("options", {}).values())
            
            if question_length > 200 or options_length > 400:
                enhanced["estimated_difficulty"] = "hard"
            elif question_length > 100 or options_length > 200:
                enhanced["estimated_difficulty"] = "medium"
            else:
                enhanced["estimated_difficulty"] = "easy"
            
            return enhanced
            
        except Exception as e:
            logger.error(f"Error enhancing question metadata: {e}")
            return question
    
    def get_parsing_statistics(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about the parsing process"""
        try:
            questions = parsed_data.get("questions", [])
            
            if not questions:
                return {
                    "total_questions": 0,
                    "avg_confidence": 0.0,
                    "high_confidence_count": 0,
                    "medium_confidence_count": 0,
                    "low_confidence_count": 0
                }
            
            confidences = [q.get("ai_confidence", 0.0) for q in questions]
            avg_confidence = sum(confidences) / len(confidences)
            
            high_confidence = len([c for c in confidences if c >= 0.8])
            medium_confidence = len([c for c in confidences if 0.5 <= c < 0.8])
            low_confidence = len([c for c in confidences if c < 0.5])
            
            return {
                "total_questions": len(questions),
                "avg_confidence": round(avg_confidence, 2),
                "high_confidence_count": high_confidence,
                "medium_confidence_count": medium_confidence,
                "low_confidence_count": low_confidence,
                "confidence_distribution": {
                    "high": high_confidence,
                    "medium": medium_confidence,
                    "low": low_confidence
                }
            }
            
        except Exception as e:
            logger.error(f"Error calculating parsing statistics: {e}")
            return {"error": str(e)}
