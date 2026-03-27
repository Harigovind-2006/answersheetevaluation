"""
Tests for KeyExtractor service.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.key_extraction_service import KeyExtractor
from app.models.schemas import ModelAnswer

class TestKeyExtractor:

    @pytest.mark.asyncio
    async def test_extract_key_success(self):
        extractor = KeyExtractor()
        mock_response = json.dumps([
            {
                "question_id": "q1",
                "question_number": 1,
                "model_answer": "Paris",
                "max_marks": 5,
                "section": "A",
                "acceptable_answers": ["Paris"]
            }
        ])

        with patch.object(extractor, "_call_gemini", return_value=mock_response):
            result = await extractor.extract_key("some text", "some key")
            
        assert len(result) == 1
        assert result[0].question_number == 1
        assert result[0].model_answer == "Paris"

    @pytest.mark.asyncio
    async def test_extract_key_failure(self):
        extractor = KeyExtractor()
        
        with patch.object(extractor, "_call_gemini", side_effect=Exception("API Error")):
            result = await extractor.extract_key("some text", "some key")
            assert result == []
