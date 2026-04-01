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

    MODEL_NAME = "gemini-2.5-flash"  # Flash is faster and good for extraction

    SYSTEM_INSTRUCTION = """You are an expert exam coordinator and subject matter expert.
Your task is to build a structured marking scheme from the OCR text of a Question Paper and optionally an Answer Key.

Rules:
- Identify each question number and its maximum marks.
- If an Answer Key is provided, use it as the model answer.
- If NO Answer Key is provided, use your subject knowledge to generate the correct/expected model answer for each question based on the question text.
- If multiple parts exist (e.g. 1a, 1b), treat each as a separate entry.
- Return ONLY valid JSON — a list of objects, no extra text.

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

        has_answer_key = bool(answer_key_text.strip())
        has_question_paper = bool(question_paper_text.strip())

        if has_answer_key and has_question_paper:
            mode_note = "Both a question paper and an answer key are provided. Use the answer key as model answers."
        elif has_answer_key:
            mode_note = "Only an answer key is provided. Extract questions and answers from it."
        else:
            mode_note = (
                "Only a question paper is provided — NO answer key. "
                "Use your subject knowledge to generate the correct expected answer for each question. "
                "Do NOT leave model_answer blank."
            )

        prompt = f"""
{mode_note}

QUESTION PAPER OCR TEXT:
{question_paper_text or '(not provided)'}

ANSWER KEY OCR TEXT:
{answer_key_text or '(not provided)'}

Build the marking scheme now.
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
