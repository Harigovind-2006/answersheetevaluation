"""
Service to extract ModelAnswer objects from Question Paper and Answer Key images
using OCR followed by Gemini structured extraction.
"""

from __future__ import annotations

import json
import re
from typing import Optional

import google.generativeai as genai
from loguru import logger

from ..core.config import get_settings
from ..models.schemas import ModelAnswer

settings = get_settings()

class KeyExtractor:
    """Extracts marking schemes and model answers using Gemini."""

    MODEL_NAME = "gemini-1.5-flash"  # Flash is faster and good for extraction

    SYSTEM_INSTRUCTION = """You are an expert exam coordinator.
Your task is to extract a structured marking scheme from OCR text of a Question Paper and/or an Answer Key.
You MUST:
- Identify each question number.
- Extract the model/correct answer for each question.
- Extract the maximum marks assigned to each question.
- If multiple parts exist (e.g. 1a, 1b), flatten them or treat them as separate entries if possible.
- Return ONLY valid JSON as a list of objects.
JSON structure:
[
  {
    "question_id": "q1",
    "question_number": 1,
    "model_answer": "The capital of France is Paris.",
    "max_marks": 5,
    "section": "A",
    "acceptable_answers": ["Paris"]
  },
  ...
]
"""

    def __init__(self):
        if settings.gemini_api_key:
            genai.configure(api_key=settings.gemini_api_key)
        self._model: Optional[genai.GenerativeModel] = None

    @property
    def model(self) -> genai.GenerativeModel:
        if self._model is None:
            self._model = genai.GenerativeModel(
                model_name=self.MODEL_NAME,
                system_instruction=self.SYSTEM_INSTRUCTION,
                generation_config=genai.GenerationConfig(
                    temperature=0.1,
                    response_mime_type="application/json",
                ),
            )
        return self._model

    async def extract_key(
        self, 
        question_paper_text: str = "", 
        answer_key_text: str = ""
    ) -> list[ModelAnswer]:
        """
        Takes raw OCR text from Q-Paper and A-Key and returns list of ModelAnswer.
        """
        if not (question_paper_text or answer_key_text):
            return []

        prompt = f"""
QUESTION PAPER OCR TEXT:
{question_paper_text}

ANSWER KEY OCR TEXT:
{answer_key_text}

Extract the marking scheme now.
"""
        logger.info("Extracting marking scheme from provided documents...")
        
        try:
            response_text = await self._call_gemini(prompt)
            data = json.loads(response_text)
            
            # Ensure data is a list
            if not isinstance(data, list):
                if isinstance(data, dict) and "marking_scheme" in data:
                    data = data["marking_scheme"]
                elif isinstance(data, dict):
                    data = [data]
                else:
                    raise ValueError(f"Unexpected JSON format: {type(data)}")

            model_answers = [ModelAnswer(**item) for item in data]
            
            logger.success(f"Successfully extracted {len(model_answers)} model answers.")
            return model_answers
            
        except Exception as e:
            logger.error(f"Failed to extract marking scheme: {e}")
            return []

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API asynchronously."""
        import asyncio
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self.model.generate_content(prompt),
        )
        return response.text
