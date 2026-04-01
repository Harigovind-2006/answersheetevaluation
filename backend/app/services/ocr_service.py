"""
OCR service using Gemini 1.5 Flash (Vision capabilities).

This service replaces EasyOCR with Gemini 1.5 Flash for significantly better 
handwriting recognition, zero-shot structured data extraction, and handling 
messy or poorly scanned student answer sheets.
"""

import json
from pathlib import Path
from typing import Optional

import google.generativeai as genai
from PIL import Image
from loguru import logger

from ..core.config import get_settings
from ..models.schemas import ExtractedAnswer, OCRResult

settings = get_settings()

class OCRService:
    """
    OCR Service using Gemini Multimodal AI.
    It takes images, extracts handwritten/printed text, and directly organizes 
    it into properly structured ExtractedAnswer objects without brittle Regex.
    """

    MODEL_NAME = "gemini-2.5-flash"  # Flash is extremely fast, cheap, and excellent at OCR

    SYSTEM_INSTRUCTION = """You are an expert OCR and transcription AI specializing in reading handwritten exam answer sheets.
Your task is to extract all handwritten and printed text from the provided images of an exam sheet.

You MUST follow these rules:
1. Transcribe the text exactly as written.
2. Identify the student's name and roll number/ID strictly from the frontsheet/first page.
3. Identify where each numbered question begins and ends. Extract the full answer for each question.
4. If a question has multiple parts (e.g. 1a, 1b), combine them into the single answer text for that main question number, or format them clearly within that answer text.
5. Return the result ONLY as valid JSON. No markdown formatting blocks around the JSON.

Expected JSON format:
{
  "raw_text": "The entire unformatted transcription of all pages combined...",
  "student_name": "John Doe",
  "roll_number": "STU12345",
  "extracted_answers": [
    {
      "question_number": 1,
      "answer_text": "The mitochondria is the powerhouse of the cell."
    },
    {
      "question_number": 2,
      "answer_text": "Water boils at 100 degrees Celsius."
    }
  ]
}

If you cannot find a student name or roll number, leave them as empty strings.
If you cannot find any numbered questions, put all the text into question_number 1.
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
                    temperature=0.1,  # Low temp for accurate transcription
                    response_mime_type="application/json",
                ),
            )
        return self._model

    async def extract_from_multiple_files(self, image_paths: list[str], expected_questions: Optional[list] = None) -> OCRResult:
        """
        Pass multiple pages of a student's answer sheet to Gemini at once.
        This provides perfect context across pages (e.g., an answer spanning two pages).
        """
        if not image_paths:
            return OCRResult(raw_text="", extracted_answers=[])

        logger.info(f"Running Gemini OCR on {len(image_paths)} pages: {image_paths}")
        
        try:
            # Load all images using PIL
            pil_images = []
            for path in image_paths:
                img = Image.open(path)
                pil_images.append(img)
            
            prompt = "Extract the text and structure it as JSON. Please ensure you extract the Name and Roll No from the frontsheet."
            if expected_questions:
                prompt += f"\n\nCRITICAL: Map the student's handwritten answers to these specific question numbers: {expected_questions}. Look carefully for these numbers in the margins or text."
            contents = pil_images + [prompt]

            response_text = await self._call_gemini(contents)
            
            # Close images
            for img in pil_images:
                img.close()

            # Parse the structured JSON response
            data = json.loads(response_text)
            
            # Convert to our ExtractedAnswer schemas
            answers = []
            raw_answers = data.get("extracted_answers", [])
            for ans_dict in raw_answers:
                q_num = ans_dict.get("question_number", 1)
                ans_text = ans_dict.get("answer_text", "").strip()
                if ans_text:
                    answers.append(
                        ExtractedAnswer(
                            question_id=f"q{q_num}",
                            question_number=q_num,
                            answer_text=ans_text,
                            confidence=0.95, # High pseudo-confidence
                        )
                    )
            
            return OCRResult(
                raw_text=data.get("raw_text", ""),
                student_name=data.get("student_name", ""),
                roll_number=data.get("roll_number", ""),
                extracted_answers=answers,
                page_count=len(image_paths),
                avg_confidence=0.95
            )

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini OCR JSON response: {e}\nRaw output: {response_text}")
            raise RuntimeError("OCR failed: Gemini returned invalid JSON")
        except Exception as e:
            logger.error(f"Gemini OCR error: {e}")
            raise RuntimeError(f"OCR failed via Gemini: {str(e)}")

    async def extract_from_file(self, image_path: str) -> OCRResult:
        """Run OCR on a single preprocessed image file."""
        return await self.extract_from_multiple_files([image_path])

    async def extract_from_bytes(self, image_bytes: bytes) -> OCRResult:
        """Run Gemini OCR on raw bytes (saving to a temp file first since Gemini likes files/PIL)."""
        import tempfile
        import os
        
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(image_bytes)
                tmp_path = tmp.name
            
            result = await self.extract_from_multiple_files([tmp_path])
            return result
        finally:
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.remove(tmp_path)

    async def _call_gemini(self, contents: list) -> str:
        """Call Gemini API asynchronously."""
        import asyncio
        from loguru import logger
        loop = asyncio.get_event_loop()
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(contents),
                )
                return response.text
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "Quota exceeded" in err_str:
                    logger.warning(f"Rate limit hit! Sleeping 40s. Attempt {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(40)
                        continue
                raise e
