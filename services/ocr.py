import io
import os
from typing import Optional
from services.async_jobs import retry_with_backoff


def extract_text_from_file(file_bytes: bytes, mime_type: Optional[str] = None) -> str:
    """
    Extract text from file bytes.
    - For PDFs/images, prefers Google Vision API if credentials are configured via
      GOOGLE_APPLICATION_CREDENTIALS env var.
    - Falls back to a naive decode for text payloads.

    Returns a best-effort extracted text string.
    """
    # Lazy imports to avoid hard dependency if not configured
    use_google = bool(os.getenv("GOOGLE_APPLICATION_CREDENTIALS"))
    text_content = ""

    if use_google:
        try:
            def _call_vision():
                from google.cloud import vision
                client = vision.ImageAnnotatorClient()
                image = vision.Image(content=file_bytes)
                return client.document_text_detection(image=image)
            response = retry_with_backoff(_call_vision)
            if response.full_text_annotation and response.full_text_annotation.text:
                return response.full_text_annotation.text
        except Exception:
            # Fall through to basic handling
            pass

    # Basic fallback: try to decode as utf-8 text
    try:
        text_content = file_bytes.decode("utf-8", errors="ignore")
    except Exception:
        text_content = ""

    return text_content or ""


