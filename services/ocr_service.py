"""
OCR Service for BotCamp Medical
Implements Part 5 - OCR parsing for PDF and image processing
"""

import logging
import io
import base64
from typing import Dict, Any, Optional, List
import os
from PIL import Image
import fitz  # PyMuPDF for PDF processing
import requests

logger = logging.getLogger(__name__)

class OCRService:
    def __init__(self):
        self.google_vision_api_key = self._get_google_vision_api_key()
        self.gemini_api_key = self._get_gemini_api_key()
    
    def _get_google_vision_api_key(self) -> Optional[str]:
        """Get Google Vision API key"""
        return os.getenv("GOOGLE_VISION_API_KEY")
    
    def _get_gemini_api_key(self) -> Optional[str]:
        """Get Gemini API key"""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API")
        if not api_key:
            try:
                with open("gemni_api", "r", encoding="utf-8") as f:
                    api_key = f.read().strip()
            except FileNotFoundError:
                pass
        return api_key
    
    def extract_text_from_pdf(self, pdf_data: bytes) -> Dict[str, Any]:
        """
        Extract text from PDF using PyMuPDF
        """
        try:
            # Open PDF from bytes
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            
            extracted_text = ""
            page_count = len(pdf_document)
            
            for page_num in range(page_count):
                page = pdf_document[page_num]
                text = page.get_text()
                extracted_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
            
            pdf_document.close()
            
            return {
                "success": True,
                "text": extracted_text,
                "page_count": page_count,
                "method": "pymupdf",
                "confidence": 0.9  # PyMuPDF is very reliable for text extraction
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "page_count": 0
            }
    
    def extract_text_from_image(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extract text from image using Google Vision API or Gemini Vision
        """
        try:
            # Try Google Vision API first
            if self.google_vision_api_key:
                result = self._extract_with_google_vision(image_data)
                if result["success"]:
                    return result
            
            # Fallback to Gemini Vision
            if self.gemini_api_key:
                result = self._extract_with_gemini_vision(image_data)
                if result["success"]:
                    return result
            
            # If both fail, return error
            return {
                "success": False,
                "error": "No OCR service available",
                "text": "",
                "confidence": 0.0
            }
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "confidence": 0.0
            }
    
    def _extract_with_google_vision(self, image_data: bytes) -> Dict[str, Any]:
        """Extract text using Google Vision API"""
        try:
            # Encode image to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
            
            # Prepare request
            url = f"https://vision.googleapis.com/v1/images:annotate?key={self.google_vision_api_key}"
            
            payload = {
                "requests": [
                    {
                        "image": {
                            "content": image_base64
                        },
                        "features": [
                            {
                                "type": "TEXT_DETECTION",
                                "maxResults": 1
                            }
                        ]
                    }
                ]
            }
            
            # Make request
            response = requests.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if "responses" in result and len(result["responses"]) > 0:
                response_data = result["responses"][0]
                
                if "textAnnotations" in response_data and len(response_data["textAnnotations"]) > 0:
                    extracted_text = response_data["textAnnotations"][0]["description"]
                    
                    # Calculate confidence based on detected text quality
                    confidence = self._calculate_ocr_confidence(extracted_text)
                    
                    return {
                        "success": True,
                        "text": extracted_text,
                        "confidence": confidence,
                        "method": "google_vision"
                    }
            
            return {
                "success": False,
                "error": "No text detected",
                "text": "",
                "confidence": 0.0
            }
            
        except Exception as e:
            logger.error(f"Error with Google Vision API: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "confidence": 0.0
            }
    
    def _extract_with_gemini_vision(self, image_data: bytes) -> Dict[str, Any]:
        """Extract text using Gemini Vision API"""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.gemini_api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Create prompt for text extraction
            prompt = """Extract all text from this image. Return only the raw text content, preserving the original formatting and structure. Do not add any explanations or formatting."""
            
            # Send to Gemini
            response = model.generate_content([prompt, image])
            
            if response.text:
                extracted_text = response.text.strip()
                confidence = self._calculate_ocr_confidence(extracted_text)
                
                return {
                    "success": True,
                    "text": extracted_text,
                    "confidence": confidence,
                    "method": "gemini_vision"
                }
            
            return {
                "success": False,
                "error": "No text extracted",
                "text": "",
                "confidence": 0.0
            }
            
        except Exception as e:
            logger.error(f"Error with Gemini Vision: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "confidence": 0.0
            }
    
    def _calculate_ocr_confidence(self, text: str) -> float:
        """Calculate confidence score based on text quality"""
        try:
            if not text or len(text.strip()) < 10:
                return 0.0
            
            # Basic quality indicators
            confidence = 0.5  # Base confidence
            
            # Check for question-like patterns
            if any(keyword in text.lower() for keyword in ['question', 'what', 'which', 'how', 'why']):
                confidence += 0.2
            
            # Check for multiple choice patterns
            if re.search(r'[A-D]\)', text) or re.search(r'[A-D]\.', text):
                confidence += 0.2
            
            # Check for answer patterns
            if re.search(r'(answer|correct):\s*[A-D]', text, re.IGNORECASE):
                confidence += 0.1
            
            # Penalize for too many special characters (might be garbled)
            special_char_ratio = len(re.findall(r'[^\w\s\.\,\!\?]', text)) / len(text)
            if special_char_ratio > 0.3:
                confidence -= 0.2
            
            return min(max(confidence, 0.0), 1.0)
            
        except Exception as e:
            logger.error(f"Error calculating OCR confidence: {e}")
            return 0.5
    
    def process_multiple_images(self, image_data_list: List[bytes]) -> Dict[str, Any]:
        """Process multiple images and combine results"""
        try:
            all_text = ""
            total_confidence = 0.0
            successful_extractions = 0
            
            for i, image_data in enumerate(image_data_list):
                result = self.extract_text_from_image(image_data)
                
                if result["success"]:
                    all_text += f"\n--- Image {i + 1} ---\n{result['text']}\n"
                    total_confidence += result["confidence"]
                    successful_extractions += 1
            
            if successful_extractions == 0:
                return {
                    "success": False,
                    "error": "No images processed successfully",
                    "text": "",
                    "confidence": 0.0
                }
            
            avg_confidence = total_confidence / successful_extractions
            
            return {
                "success": True,
                "text": all_text,
                "confidence": avg_confidence,
                "images_processed": successful_extractions,
                "total_images": len(image_data_list)
            }
            
        except Exception as e:
            logger.error(f"Error processing multiple images: {e}")
            return {
                "success": False,
                "error": str(e),
                "text": "",
                "confidence": 0.0
            }
    
    def extract_images_from_pdf(self, pdf_data: bytes) -> List[bytes]:
        """Extract images from PDF for OCR processing"""
        try:
            pdf_document = fitz.open(stream=pdf_data, filetype="pdf")
            images = []
            
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                image_list = page.get_images()
                
                for img_index, img in enumerate(image_list):
                    xref = img[0]
                    pix = fitz.Pixmap(pdf_document, xref)
                    
                    if pix.n - pix.alpha < 4:  # GRAY or RGB
                        img_data = pix.tobytes("png")
                        images.append(img_data)
                    
                    pix = None
            
            pdf_document.close()
            return images
            
        except Exception as e:
            logger.error(f"Error extracting images from PDF: {e}")
            return []
    
    def get_ocr_statistics(self, extraction_result: Dict[str, Any]) -> Dict[str, Any]:
        """Get statistics about OCR extraction"""
        try:
            if not extraction_result["success"]:
                return {
                    "success": False,
                    "error": extraction_result.get("error", "Unknown error")
                }
            
            text = extraction_result.get("text", "")
            
            return {
                "success": True,
                "text_length": len(text),
                "word_count": len(text.split()),
                "line_count": len(text.split('\n')),
                "confidence": extraction_result.get("confidence", 0.0),
                "method": extraction_result.get("method", "unknown"),
                "has_questions": bool(re.search(r'[A-D]\)', text) or re.search(r'[A-D]\.', text)),
                "has_answers": bool(re.search(r'(answer|correct):\s*[A-D]', text, re.IGNORECASE))
            }
            
        except Exception as e:
            logger.error(f"Error calculating OCR statistics: {e}")
            return {"success": False, "error": str(e)}
