"""
Integration tests for FastAPI routes (no real API calls).
"""

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestHealthRoute:
    def test_health_check_returns_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "services" in data
        assert "opencv" in data["services"]

    def test_root_returns_api_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "AutoGrade" in data["name"]


class TestPipelineRoute:
    SAMPLE_GRADE_REQUEST = {
        "exam_id": "exam123",
        "exam_title": "Geography Test",
        "student_name": "Jane Doe",
        "roll_number": "2024GEO001",
        "model_answers": [
            {"question_id": "q1", "question_number": 1, "model_answer": "Paris", "max_marks": 10},
            {"question_id": "q2", "question_number": 2, "model_answer": "London", "max_marks": 10},
        ],
    }

    def test_process_requires_images(self, client):
        response = client.post(
            "/api/process",
            data={"grade_request": json.dumps(self.SAMPLE_GRADE_REQUEST)},
        )
        assert response.status_code == 422  # Unprocessable — no images

    def test_invalid_grade_request_json(self, client):
        import io
        fake_image = io.BytesIO(b"not a real image")
        response = client.post(
            "/api/process",
            files={"images": ("test.jpg", fake_image, "image/jpeg")},
            data={"grade_request": "invalid json {{{"},
        )
        assert response.status_code == 422

    def test_preprocess_only_endpoint_exists(self, client):
        """Endpoint should exist even if processing a dummy image fails."""
        import io
        # PNG magic bytes (minimal valid PNG)
        tiny_png = (
            b'\x89PNG\r\n\x1a\n'
            b'\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
            b'\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx'
            b'\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N'
            b'\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        with patch("app.services.image_processor.ImagePreprocessor.preprocess_bytes") as mock:
            from app.models.schemas import ProcessedImage
            mock.return_value = ProcessedImage(
                original_path="test.png",
                processed_path="processed.png",
                width=100,
                height=100,
                operations_applied=["grayscale"],
            )
            with patch("app.services.image_processor.ImagePreprocessor.get_image_quality_score") as qmock:
                qmock.return_value = {"score": 0.8, "is_blurry": False}
                response = client.post(
                    "/api/preprocess-only",
                    files={"images": ("test.png", io.BytesIO(tiny_png), "image/png")},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
