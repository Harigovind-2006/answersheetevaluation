"""
Gemini grading service.

Sends OCR-extracted answers and model answers to Gemini and returns
ONLY numerical scores — no feedback, no explanations.

JSON-only output contract:
{
  "q1": {"obtained": 7, "max": 10},
  "q2": {"obtained": 4, "max": 5},
  ...
}
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Optional

import google.generativeai as genai
from loguru import logger

from ..core.config import get_settings
from ..models.schemas import (
    ExtractedAnswer,
    GradingResult,
    ModelAnswer,
    QuestionScore,
)

settings = get_settings()

# Grade boundaries
GRADE_BOUNDARIES = [
    (80, "A"),
    (65, "B"),
    (50, "C"),
    (35, "D"),
    (0,  "F"),
]


class GeminiGrader:
    """Grades extracted answers using Gemini 2.5 Flash."""

    MODEL_NAME = "gemini-2.5-flash"

    SYSTEM_INSTRUCTION = """You are an automated exam grader.
Your ONLY job is to compare student answers against model answers and return numerical marks.
You MUST:
- Return ONLY valid JSON. No text before or after the JSON.
- Never include explanations, comments, or feedback of any kind.
- Award marks fairly, giving partial credit where appropriate.
- If an answer is missing or blank, award 0.
- Clamp scores to [0, max_marks] inclusive."""

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
                    temperature=0.05,     # Near-deterministic for grading
                    max_output_tokens=2048,
                    response_mime_type="application/json",
                ),
            )
        return self._model

    async def grade(
        self,
        student_answers: list[ExtractedAnswer],
        model_answers: list[ModelAnswer],
        exam_title: str,
        student_name: str = "",
        roll_number: str = "",
        exam_id: str = "",
        total_marks: int = 0,
        passing_marks: int = 0,
        raw_student_text: str = "",
    ) -> GradingResult:
        """
        Full grading pipeline.
        Returns GradingResult with per-question scores and totals.
        """
        logger.info(
            f"Grading '{exam_title}' for {student_name or 'Unknown'} "
            f"({len(student_answers)} answers vs {len(model_answers)} questions)"
        )

        prompt = self._build_prompt(student_answers, model_answers, exam_title, raw_student_text)

        try:
            response = await self._call_gemini(prompt)
            scores_map = self._parse_scores(response, model_answers)
        except Exception as e:
            logger.error(f"Gemini grading error: {e}")
            # Fallback: zero scores for all questions
            scores_map = self._zero_scores(model_answers)

        # Calculate totals
        total_obtained = sum(s.marks_obtained for s in scores_map.values())
        computed_available = sum(m.max_marks for m in model_answers)
        total_available = total_marks if total_marks > 0 else computed_available
        percentage = (total_obtained / total_available * 100) if total_available > 0 else 0.0
        
        is_passed = (total_obtained >= passing_marks) if passing_marks > 0 else (percentage >= 50.0)
        grade_str = "Passed" if is_passed else "Failed"

        result = GradingResult(
            student_name=student_name or "Unknown Student",
            roll_number=roll_number or "N/A",
            exam_id=exam_id,
            exam_title=exam_title,
            question_scores=scores_map,
            total_marks_obtained=total_obtained,
            total_marks_available=total_available,
            percentage=round(percentage, 2),
            grade=grade_str,
            graded_at=datetime.now(timezone.utc).isoformat(),
        )

        logger.success(
            f"Graded: {student_name} — {total_obtained}/{total_available} "
            f"({percentage:.1f}%) Grade: {grade_str}"
        )
        return result

    # ──────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────

    def _build_prompt(
        self,
        student_answers: list[ExtractedAnswer],
        model_answers: list[ModelAnswer],
        exam_title: str,
        raw_student_text: str = "",
    ) -> str:
        lines = [
            f"EXAM: {exam_title}",
            "",
            "=== MODEL ANSWERS ===",
        ]

        for ma in sorted(model_answers, key=lambda x: x.question_number):
            lines.append(
                f"Q{ma.question_number} (max {ma.max_marks} marks): {ma.model_answer}"
            )
            if ma.acceptable_answers:
                lines.append(
                    f"  Also acceptable: {', '.join(ma.acceptable_answers)}"
                )

        lines += ["", "=== STUDENT ANSWERS (OCR Extracted) ==="]
        lines.append("Note: The student might have numbered their answers differently or poorly. Please read all answers below and map them to the correct model questions based on content and context if the numbers do not perfectly align.")
        
        for ans in student_answers:
            lines.append(f"[Labeled as Q{ans.question_number}]: {ans.answer_text}")
            
        if not student_answers:
            lines.append("[NO STRUCTURED ANSWERS EXTRACTED FROM SHEET]")
            
        if raw_student_text:
            lines += ["", "--- RAW STUDENT SHEET TRANSCRIPTION (FALLBACK) ---"]
            lines.append("If the structured answers above are missing or incomplete, search through this raw transcription to find and map answers to the questions:")
            lines.append(raw_student_text)
            lines.append("--------------------------------------------------")

        lines += [
            "",
            "=== REQUIRED OUTPUT ===",
            "Return ONLY this JSON structure (no other text):",
            "{",
        ]
        for ma in sorted(model_answers, key=lambda x: x.question_number):
            lines.append(
                f'  "q{ma.question_number}": {{"obtained": <integer 0-{ma.max_marks}>, "max": {ma.max_marks}}},'
            )
        lines[-1] = lines[-1].rstrip(",")  # Remove trailing comma from last entry
        lines.append("}")

        return "\n".join(lines)

    async def _call_gemini(self, prompt: str) -> str:
        """Call Gemini API asynchronously."""
        import asyncio
        import time
        from loguru import logger
        
        loop = asyncio.get_event_loop()
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                response = await loop.run_in_executor(
                    None,
                    lambda: self.model.generate_content(prompt),
                )
                text = response.text
                logger.debug(f"Gemini raw response: {text[:300]}")
                return text
            except Exception as e:
                err_str = str(e)
                if "429" in err_str or "Quota exceeded" in err_str:
                    logger.warning(f"Rate limit hit! Sleeping 40s. Attempt {attempt+1}/{max_retries}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(40)
                        continue
                raise e

    def _parse_scores(
        self,
        response_text: str,
        model_answers: list[ModelAnswer],
    ) -> dict[str, QuestionScore]:
        """Parse Gemini JSON response into QuestionScore objects."""
        scores: dict[str, QuestionScore] = {}

        # Extract JSON block
        json_str = response_text.strip()
        json_match = re.search(r"\{[\s\S]*\}", json_str)
        if json_match:
            json_str = json_match.group(0)

        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw: {json_str[:200]}")
            return self._zero_scores(model_answers)

        for ma in model_answers:
            key = f"q{ma.question_number}"
            alt_key = f"question{ma.question_number}"

            score_data = parsed.get(key) or parsed.get(alt_key) or parsed.get(str(ma.question_number))

            if isinstance(score_data, dict):
                obtained = int(score_data.get("obtained", 0) or score_data.get("marks", 0))
            elif isinstance(score_data, (int, float)):
                obtained = int(score_data)
            else:
                obtained = 0

            scores[key] = QuestionScore(
                question_number=ma.question_number,
                marks_obtained=max(0, min(obtained, ma.max_marks)),  # clamp
                max_marks=ma.max_marks,
            )

        return scores

    def _zero_scores(self, model_answers: list[ModelAnswer]) -> dict[str, QuestionScore]:
        """Return zero scores for all questions (error fallback)."""
        return {
            f"q{ma.question_number}": QuestionScore(
                question_number=ma.question_number,
                marks_obtained=0,
                max_marks=ma.max_marks,
            )
            for ma in model_answers
        }

    @staticmethod
    def _calculate_grade(percentage: float) -> str:
        for threshold, grade in GRADE_BOUNDARIES:
            if percentage >= threshold:
                return grade
        return "F"
