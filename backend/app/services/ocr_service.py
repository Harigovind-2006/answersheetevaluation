"""
OCR service using OpenAI GPT-5.4 (Vision capabilities).

This service replaces Google Cloud Vision with GPT-5.4 for better handwriting 
recognition and zero-shot structured data extraction.
"""

import re
import cv2
import numpy as np
from pathlib import Path
from typing import Optional

import easyocr
from loguru import logger

from ..core.config import get_settings
from ..models.schemas import ExtractedAnswer, OCRResult

settings = get_settings()


class OCRService:
    """
    EasyOCR Service with text cleaning.
    Uses local easyocr model to extract text from images and applies cleaning heuristics.
    """

    def __init__(self):
        self._reader: Optional[easyocr.Reader] = None
        # Split comma separated languages from settings into a list
        self.languages = [l.strip() for l in settings.ocr_languages.split(",")]

    @property
    def reader(self) -> easyocr.Reader:
        """Lazily create the EasyOCR reader."""
        if self._reader is None:
            logger.info(f"Initializing EasyOCR with languages: {self.languages}")
            gpu_support = settings.ocr_use_gpu
            try:
                # Use settings to control GPU use
                self._reader = easyocr.Reader(self.languages, gpu=gpu_support)
            except Exception as e:
                logger.warning(f"Failed to initialize EasyOCR (GPU={gpu_support}): {e}. Retrying with CPU.")
                self._reader = easyocr.Reader(self.languages, gpu=False)
        return self._reader

    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text to remove OCR noise and standardize.
        Called after text is extracted.
        """
        if not text:
            return ""

        # 1. Normalize whitespace
        text = " ".join(text.split())

        # 2. Basic noise removal (stray symbols common in OCR)
        # Remove unusual characters that are likely noise (keeping basic punctuation)
        text = re.sub(r"[^\x20-\x7E]", "", text)

        # 3. Strip trailing/leading punctuation that's likely noise
        text = text.strip(" |._-,")

        return text

    async def extract_from_file(self, image_path: str) -> OCRResult:
        """Run OCR on a single preprocessed image file."""
        logger.info(f"Running EasyOCR on: {image_path}")
        
        try:
            # easyocr reads directly from file path
            results = self.reader.readtext(image_path)
            return self._parse_ocr_results(results)
        except Exception as e:
            logger.error(f"EasyOCR error on {image_path}: {e}")
            raise RuntimeError(f"OCR failed via EasyOCR: {str(e)}")

    async def extract_from_bytes(self, image_bytes: bytes) -> OCRResult:
        """Run EasyOCR on raw bytes."""
        try:
            # Convert bytes to numpy array for OpenCV
            nparr = np.frombuffer(image_bytes, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            results = self.reader.readtext(image)
            return self._parse_ocr_results(results)
        except Exception as e:
            logger.error(f"EasyOCR bytes error: {e}")
            raise RuntimeError(f"OCR failed via EasyOCR: {str(e)}")

    async def extract_from_multiple_files(self, image_paths: list[str]) -> OCRResult:
        """OCR multiple pages and merge results."""
        if not image_paths:
            return OCRResult(raw_text="", extracted_answers=[])

        all_results: list[OCRResult] = []
        
        # We process pages individually to handle large exams
        for idx, path in enumerate(image_paths):
            logger.info(f"OCR page {idx + 1}/{len(image_paths)}: {path}")
            result = await self.extract_from_file(path)
            all_results.append(result)

        merged_answers = self._merge_answers(all_results)
        
        # Combine raw text if possible, or just note the pages
        combined_text = "\n\n--- PAGE BREAK ---\n\n".join(
            [r.raw_text for r in all_results]
        )

        avg_conf = (
            sum(a.confidence for a in merged_answers) / len(merged_answers)
            if merged_answers else 0.0
        )

        return OCRResult(
            raw_text=combined_text,
            extracted_answers=merged_answers,
            student_name=all_results[0].student_name if all_results else "",
            roll_number=all_results[0].roll_number if all_results else "",
            page_count=len(image_paths),
            avg_confidence=round(avg_conf, 3),
        )

    def _parse_ocr_results(self, results: list) -> OCRResult:
        """
        Process EasyOCR raw output (box, text, confidence).
        Heuristically identifies question/answer splits.
        """
        full_text_parts = []
        confidences = []
        
        for (bbox, text, prob) in results:
            cleaned = self._clean_text(text)
            if cleaned:
                full_text_parts.append(cleaned)
                confidences.append(prob)

        raw_text = "\n".join(full_text_parts)
        avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

        # Heuristic to split into questions
        # Look for "Qn", "Q.n", "n.", "Question n"
        extracted_answers: list[ExtractedAnswer] = []
        
        # Current naive approach: Search for "Q1", "Q2" etc or "1.", "2."
        # We'll split the text by these patterns
        split_pattern = r"(?i)(?:^|\n)\s*(?:Q(?:\.|uestion)?\s*)?(\d+)[\.:\)\-\s]+"
        parts = re.split(split_pattern, raw_text)
        
        # re.split with capturing group returns: [pre_text, q_num, text_after, q_num, text_after...]
        if len(parts) >= 3:
            # We found some numbered questions
            for i in range(1, len(parts), 2):
                q_num_str = parts[i]
                ans_text = parts[i+1].strip() if i+1 < len(parts) else ""
                
                # Further clean the answer text
                ans_text = self._clean_text(ans_text)
                
                if q_num_str.isdigit():
                    q_num = int(q_num_str)
                    extracted_answers.append(
                        ExtractedAnswer(
                            question_id=f"q{q_num}",
                            question_number=q_num,
                            answer_text=ans_text,
                            confidence=round(avg_conf, 2), # Using avg confidence for simplicity
                        )
                    )
        
        # If no structure found, put everything as a single fallback result or dummy
        if not extracted_answers and raw_text:
             extracted_answers.append(
                ExtractedAnswer(
                    question_id="q1",
                    question_number=1,
                    answer_text=raw_text,
                    confidence=round(avg_conf, 2),
                )
            )

        # Try to find student info (very naive)
        student_name = ""
        roll_number = ""
        for line in full_text_parts[:5]:  # Look in first few lines
            if "name" in line.lower():
                student_name = line.split(":")[-1].strip()
            if "roll" in line.lower() or "id" in line.lower():
                roll_number = re.findall(r"\d+", line)[0] if re.findall(r"\d+", line) else ""

        return OCRResult(
            raw_text=raw_text,
            extracted_answers=extracted_answers,
            student_name=student_name,
            roll_number=roll_number,
            page_count=1,
            avg_confidence=round(avg_conf, 3),
        )

    def _merge_answers(self, results: list[OCRResult]) -> list[ExtractedAnswer]:
        """Keep highest-confidence answer per question across all pages."""
        best: dict[int, ExtractedAnswer] = {}
        for result in results:
            for answer in result.extracted_answers:
                existing = best.get(answer.question_number)
                if existing is None or answer.confidence > existing.confidence:
                    best[answer.question_number] = answer
        return sorted(best.values(), key=lambda a: a.question_number)
