import os
import json
from typing import Dict, Any
from services.async_jobs import retry_with_backoff


SYSTEM_INSTRUCTIONS = (
    "You are an expert assistant that extracts multiple-choice questions (MCQs) from text. "
    "Identify question statements, options (A-D), the correct option if present, a brief explanation if present, "
    "and a source tag if present (e.g., CAT 1 2022). Return strict JSON with fields: "
    "unit (string optional), topic (string optional), questions (array of {question, options[4], correct_answer (string option text or letter), explanation?, source?}). "
    "Only return valid JSON."
)


def parse_mcqs_with_ai(input_text: str) -> Dict[str, Any]:
    """
    Send text to an LLM (OpenAI or Gemini) to extract MCQs into structured JSON.
    Prefers OpenAI if OPENAI_API_KEY is set, otherwise Gemini if GEMINI_API_KEY is set.
    Falls back to a naive parser stub if neither key exists.
    """
    input_text = input_text.strip()
    if not input_text:
        return {"unit": None, "topic": None, "questions": []}

    openai_key = os.getenv("OPENAI_API_KEY")
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API")

    # Try OpenAI
    if openai_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            def _call_openai():
                return client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": SYSTEM_INSTRUCTIONS},
                    {"role": "user", "content": input_text},
                ],
                temperature=0.2,
                )
            response = retry_with_backoff(_call_openai)
            content = response.choices[0].message.content
            return json.loads(content)
        except Exception:
            pass

    # Try Gemini via google-generativeai
    if gemini_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = SYSTEM_INSTRUCTIONS + "\n\nInput:\n" + input_text + "\n\nReturn JSON only."
            def _call_gemini():
                return model.generate_content(prompt)
            result = retry_with_backoff(_call_gemini)
            text = result.text or "{}"
            return json.loads(text)
        except Exception:
            pass

    # Fallback: naive single-question detector (very basic)
    lines = [l.strip() for l in input_text.splitlines() if l.strip()]
    q = ""
    opts = []
    for l in lines:
        if not q and l.endswith("?"):
            q = l
        elif len(opts) < 4:
            opts.append(l)
    questions = []
    if q and len(opts) >= 4:
        questions.append({
            "question": q,
            "options": opts[:4],
            "correct_answer": None,
            "explanation": None,
            "source": None,
        })
    return {"unit": None, "topic": None, "questions": questions}


