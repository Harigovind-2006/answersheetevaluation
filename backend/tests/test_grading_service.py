"""
Tests for Gemini grading service (with mocked API calls).
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.schemas import ExtractedAnswer, ModelAnswer, QuestionScore
from app.services.grading_service import GeminiGrader


SAMPLE_MODEL_ANSWERS = [
    ModelAnswer(question_id="q1", question_number=1, model_answer="Paris", max_marks=10),
    ModelAnswer(question_id="q2", question_number=2, model_answer="Muhammad Ali Jinnah", max_marks=15),
    ModelAnswer(question_id="q3", question_number=3, model_answer="1947", max_marks=5),
    ModelAnswer(question_id="q4", question_number=4, model_answer="H2O", max_marks=5),
    ModelAnswer(question_id="q5", question_number=5, model_answer="India", max_marks=15, acceptable_answers=["Bharat", "Republic of India"]),
]

SAMPLE_STUDENT_ANSWERS = [
    ExtractedAnswer(question_id="q1", question_number=1, answer_text="Paris", confidence=0.95),
    ExtractedAnswer(question_id="q2", question_number=2, answer_text="Jinnah", confidence=0.88),
    ExtractedAnswer(question_id="q3", question_number=3, answer_text="1947", confidence=0.92),
    ExtractedAnswer(question_id="q4", question_number=4, answer_text="H2O", confidence=0.90),
    ExtractedAnswer(question_id="q5", question_number=5, answer_text="India", confidence=0.91),
]


class TestGeminiGrader:

    def test_parse_scores_valid_json(self):
        grader = GeminiGrader()
        response = json.dumps({
            "q1": {"obtained": 10, "max": 10},
            "q2": {"obtained": 12, "max": 15},
            "q3": {"obtained": 5, "max": 5},
            "q4": {"obtained": 5, "max": 5},
            "q5": {"obtained": 15, "max": 15},
        })
        scores = grader._parse_scores(response, SAMPLE_MODEL_ANSWERS)

        assert len(scores) == 5
        assert scores["q1"].marks_obtained == 10
        assert scores["q2"].marks_obtained == 12
        assert scores["q3"].marks_obtained == 5

    def test_parse_scores_clamps_to_max(self):
        grader = GeminiGrader()
        # Gemini returns 12 for q1 but max is 10 — should clamp
        response = json.dumps({"q1": {"obtained": 12, "max": 10}})
        scores = grader._parse_scores(response, [SAMPLE_MODEL_ANSWERS[0]])

        assert scores["q1"].marks_obtained == 10  # clamped

    def test_parse_scores_missing_question(self):
        grader = GeminiGrader()
        # Only q1 in response, q2-q5 not mentioned
        response = json.dumps({"q1": {"obtained": 8, "max": 10}})
        scores = grader._parse_scores(response, SAMPLE_MODEL_ANSWERS)

        assert scores["q1"].marks_obtained == 8
        # Missing questions should be 0
        for key in ["q2", "q3", "q4", "q5"]:
            assert scores[key].marks_obtained == 0

    def test_parse_scores_handles_json_in_text(self):
        grader = GeminiGrader()
        # Gemini sometimes wraps JSON in markdown — should still parse
        response = '```json\n{"q1": {"obtained": 7, "max": 10}}\n```'
        scores = grader._parse_scores(response, [SAMPLE_MODEL_ANSWERS[0]])
        assert scores["q1"].marks_obtained == 7

    def test_parse_scores_invalid_json_returns_zeros(self):
        grader = GeminiGrader()
        scores = grader._parse_scores("This is not JSON at all!", SAMPLE_MODEL_ANSWERS)
        for score in scores.values():
            assert score.marks_obtained == 0

    def test_calculate_grade(self):
        grader = GeminiGrader()
        assert grader._calculate_grade(95.0) == "A"
        assert grader._calculate_grade(80.0) == "A"
        assert grader._calculate_grade(70.0) == "B"
        assert grader._calculate_grade(65.0) == "B"
        assert grader._calculate_grade(55.0) == "C"
        assert grader._calculate_grade(50.0) == "C"
        assert grader._calculate_grade(40.0) == "D"
        assert grader._calculate_grade(35.0) == "D"
        assert grader._calculate_grade(20.0) == "F"
        assert grader._calculate_grade(0.0) == "F"

    def test_zero_scores_fallback(self):
        grader = GeminiGrader()
        scores = grader._zero_scores(SAMPLE_MODEL_ANSWERS)
        assert len(scores) == 5
        for score in scores.values():
            assert score.marks_obtained == 0

    def test_build_prompt_includes_all_questions(self):
        grader = GeminiGrader()
        prompt = grader._build_prompt(
            SAMPLE_STUDENT_ANSWERS, SAMPLE_MODEL_ANSWERS, "Test Exam"
        )
        for ma in SAMPLE_MODEL_ANSWERS:
            assert f"Q{ma.question_number}" in prompt
            assert ma.model_answer in prompt

    def test_build_prompt_marks_missing_answers(self):
        grader = GeminiGrader()
        # Only provide 2 of 5 answers
        partial_answers = SAMPLE_STUDENT_ANSWERS[:2]
        prompt = grader._build_prompt(partial_answers, SAMPLE_MODEL_ANSWERS, "Test")
        assert "[NO ANSWER]" in prompt

    @pytest.mark.asyncio
    async def test_grade_full_pipeline_mocked(self):
        grader = GeminiGrader()
        mock_response = json.dumps({
            "q1": {"obtained": 10, "max": 10},
            "q2": {"obtained": 12, "max": 15},
            "q3": {"obtained": 5, "max": 5},
            "q4": {"obtained": 5, "max": 5},
            "q5": {"obtained": 14, "max": 15},
        })

        with patch.object(grader, "_call_gemini", return_value=mock_response):
            result = await grader.grade(
                student_answers=SAMPLE_STUDENT_ANSWERS,
                model_answers=SAMPLE_MODEL_ANSWERS,
                exam_title="Test Exam",
                student_name="John Smith",
                roll_number="2024CS001",
            )

        assert result.total_marks_obtained == 46
        assert result.total_marks_available == 50
        assert result.percentage == 92.0
        assert result.grade == "A"
        assert result.student_name == "John Smith"
        assert result.roll_number == "2024CS001"
        assert len(result.question_scores) == 5
