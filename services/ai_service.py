"""
AI Service for BotCamp Medical
Handles OCR, text parsing, and question validation using Gemini/GPT APIs
"""

import os
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
import openai
from PIL import Image
import io
import base64
from deployment.fallback_adapter import get_active_ai_provider

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.confidence_threshold = float(os.getenv("AI_CONFIDENCE_THRESHOLD", "0.8"))
        self.ocr_provider = os.getenv("OCR_PROVIDER", "gemini")
        
        # Initialize AI clients
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-pro')
            self.gemini_vision_model = genai.GenerativeModel('gemini-1.5-pro-vision')
        
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        
        logger.info(f"AI Service initialized - Gemini: {bool(self.gemini_api_key)}, OpenAI: {bool(self.openai_api_key)}")
    
    async def extract_text_from_image(self, image_data: bytes) -> str:
        """Extract text from image using OCR"""
        try:
            if self.ocr_provider == "gemini" and self.gemini_api_key:
                return await self._gemini_ocr(image_data)
            elif self.openai_api_key:
                return await self._openai_vision_ocr(image_data)
            else:
                # Fallback to basic text extraction
                return await self._fallback_ocr(image_data)
        except Exception as e:
            logger.error(f"Error in extract_text_from_image: {e}")
            raise
    
    async def _gemini_ocr(self, image_data: bytes) -> str:
        """Use Gemini Vision for OCR"""
        try:
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Create prompt for OCR
            prompt = """
            Extract all text from this image. This appears to be a medical quiz or exam paper.
            Please return ONLY the raw text content, preserving the structure and formatting.
            Include question numbers, options (A, B, C, D), and any answer indicators.
            Do not add any commentary or explanations.
            """
            
            # Generate content
            response = self.gemini_vision_model.generate_content([prompt, image])
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Gemini OCR error: {e}")
            raise
    
    async def _openai_vision_ocr(self, image_data: bytes) -> str:
        """Use OpenAI Vision for OCR"""
        try:
            # Convert to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4-vision-preview",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all text from this image. This appears to be a medical quiz or exam paper. Return only the raw text content, preserving structure and formatting."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=2000
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"OpenAI Vision OCR error: {e}")
            raise
    
    async def _fallback_ocr(self, image_data: bytes) -> str:
        """Fallback OCR using basic image processing"""
        try:
            # This is a placeholder for Tesseract OCR or other fallback
            # For now, return a message indicating OCR is not available
            return "OCR service not available. Please provide text input instead."
        except Exception as e:
            logger.error(f"Fallback OCR error: {e}")
            raise
    
    async def parse_questions_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse questions from text using AI"""
        try:
            provider = get_active_ai_provider()
            if provider == "gemini" and self.gemini_api_key:
                return await self._gemini_parse_questions(text)
            if provider == "openai" and self.openai_api_key:
                return await self._openai_parse_questions(text)
            # try the other as fallback
            if self.gemini_api_key:
                try:
                    return await self._gemini_parse_questions(text)
                except Exception:
                    pass
            if self.openai_api_key:
                try:
                    return await self._openai_parse_questions(text)
                except Exception:
                    pass
            return await self._fallback_parse_questions(text)
        except Exception as e:
            logger.error(f"Error in parse_questions_from_text: {e}")
            raise
    
    async def _gemini_parse_questions(self, text: str) -> List[Dict[str, Any]]:
        """Use Gemini to parse questions from text"""
        try:
            prompt = f"""
            Parse the following text and extract medical quiz questions. Return a JSON array where each question has this structure:
            
            {{
                "question_text": "The question text",
                "options": {{
                    "A": "Option A text",
                    "B": "Option B text", 
                    "C": "Option C text",
                    "D": "Option D text"
                }},
                "correct_option": "A/B/C/D",
                "explanation": "Brief explanation of why this is correct (optional)",
                "confidence": 0.95
            }}
            
            Rules:
            1. Only include complete multiple choice questions with 4 options (A, B, C, D)
            2. If correct answer is not explicitly stated, infer from context
            3. Set confidence score (0.0-1.0) based on how certain you are
            4. Return valid JSON only, no other text
            5. If no valid questions found, return empty array []
            
            Text to parse:
            {text}
            """
            
            response = self.gemini_model.generate_content(prompt)
            result_text = response.text.strip()
            
            # Clean up the response to extract JSON
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            questions = json.loads(result_text)
            
            # Validate and filter by confidence
            validated_questions = []
            for q in questions:
                if self._validate_question(q):
                    validated_questions.append(q)
            
            return validated_questions
            
        except Exception as e:
            logger.error(f"Gemini parse error: {e}")
            raise
    
    async def _openai_parse_questions(self, text: str) -> List[Dict[str, Any]]:
        """Use OpenAI to parse questions from text"""
        try:
            prompt = f"""
            Parse the following text and extract medical quiz questions. Return a JSON array where each question has this structure:
            
            {{
                "question_text": "The question text",
                "options": {{
                    "A": "Option A text",
                    "B": "Option B text", 
                    "C": "Option C text",
                    "D": "Option D text"
                }},
                "correct_option": "A/B/C/D",
                "explanation": "Brief explanation of why this is correct (optional)",
                "confidence": 0.95
            }}
            
            Rules:
            1. Only include complete multiple choice questions with 4 options (A, B, C, D)
            2. If correct answer is not explicitly stated, infer from context
            3. Set confidence score (0.0-1.0) based on how certain you are
            4. Return valid JSON only, no other text
            5. If no valid questions found, return empty array []
            
            Text to parse:
            {text}
            """
            
            response = await openai.ChatCompletion.acreate(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are an expert at parsing medical quiz questions from text. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=2000,
                temperature=0.1
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Clean up the response
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
            
            questions = json.loads(result_text)
            
            # Validate and filter by confidence
            validated_questions = []
            for q in questions:
                if self._validate_question(q):
                    validated_questions.append(q)
            
            return validated_questions
            
        except Exception as e:
            logger.error(f"OpenAI parse error: {e}")
            raise
    
    async def _fallback_parse_questions(self, text: str) -> List[Dict[str, Any]]:
        """Fallback parsing using simple regex patterns"""
        try:
            # This is a basic fallback parser
            # In a real implementation, you'd use regex to extract questions
            logger.warning("Using fallback question parser - results may be limited")
            return []
        except Exception as e:
            logger.error(f"Fallback parse error: {e}")
            raise
    
    def _validate_question(self, question: Dict[str, Any]) -> bool:
        """Validate a parsed question"""
        try:
            # Check required fields
            required_fields = ["question_text", "options", "correct_option"]
            for field in required_fields:
                if field not in question:
                    return False
            
            # Check options structure
            options = question["options"]
            if not isinstance(options, dict):
                return False
            
            required_options = ["A", "B", "C", "D"]
            for opt in required_options:
                if opt not in options or not options[opt]:
                    return False
            
            # Check correct option
            correct = question["correct_option"]
            if correct not in required_options:
                return False
            
            # Check confidence score
            confidence = question.get("confidence", 0.0)
            if confidence < self.confidence_threshold:
                logger.info(f"Question rejected due to low confidence: {confidence}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Question validation error: {e}")
            return False
    
    async def generate_explanation(self, question_text: str, correct_option: str, options: Dict[str, str]) -> str:
        """Generate explanation for a question using AI"""
        try:
            if not (self.gemini_api_key or self.openai_api_key):
                return ""
            
            prompt = f"""
            Provide a brief, educational explanation for this medical question:
            
            Question: {question_text}
            Options:
            A. {options.get('A', '')}
            B. {options.get('B', '')}
            C. {options.get('C', '')}
            D. {options.get('D', '')}
            
            Correct Answer: {correct_option}
            
            Provide a concise explanation (1-2 sentences) of why {correct_option} is correct.
            Focus on the medical/biological reasoning.
            """
            
            if self.gemini_api_key:
                response = self.gemini_model.generate_content(prompt)
                return response.text.strip()
            else:
                response = await openai.ChatCompletion.acreate(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are a medical educator. Provide concise, accurate explanations."},
                        {"role": "user", "content": prompt}
                    ],
                    max_tokens=150,
                    temperature=0.3
                )
                return response.choices[0].message.content.strip()
                
        except Exception as e:
            logger.error(f"Error generating explanation: {e}")
            return ""
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get status of AI services"""
        return {
            "gemini_available": bool(self.gemini_api_key),
            "openai_available": bool(self.openai_api_key),
            "confidence_threshold": self.confidence_threshold,
            "ocr_provider": self.ocr_provider
        }
