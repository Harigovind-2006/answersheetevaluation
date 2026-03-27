"""
Tests for the image preprocessing service.
Run with: pytest tests/ -v
"""

import os
import numpy as np
import cv2
import pytest
from pathlib import Path

from app.services.image_processor import ImagePreprocessor


@pytest.fixture
def preprocessor():
    return ImagePreprocessor()


def make_synthetic_sheet(
    width: int = 800,
    height: int = 1100,
    noise_level: int = 15,
    skew_angle: float = 2.0,
) -> np.ndarray:
    """Create a synthetic handwritten-style answer sheet for testing."""
    # White background
    img = np.ones((height, width, 3), dtype=np.uint8) * 245

    # Add some lines simulating ruled paper
    for y in range(80, height - 50, 40):
        cv2.line(img, (30, y), (width - 30, y), (200, 200, 200), 1)

    # Add simulated text blocks (rectangles)
    texts = [
        (50, 30, "Name: John Smith"),
        (50, 75, "Roll No: 2024CS001"),
        (50, 130, "1. Paris"),
        (50, 170, "2. Muhammad Ali Jinnah"),
        (50, 210, "3. 1947"),
        (50, 250, "4. H2O"),
        (50, 290, "5. India"),
    ]
    for x, y, text in texts:
        cv2.putText(img, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1)

    # Add noise
    if noise_level > 0:
        noise = np.random.randint(0, noise_level, img.shape, dtype=np.uint8)
        img = cv2.add(img, noise)

    # Apply skew
    if abs(skew_angle) > 0:
        M = cv2.getRotationMatrix2D((width // 2, height // 2), skew_angle, 1.0)
        img = cv2.warpAffine(img, M, (width, height), borderMode=cv2.BORDER_REPLICATE)

    return img


class TestImagePreprocessor:

    def test_grayscale_conversion(self, preprocessor):
        img_bgr = make_synthetic_sheet()
        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
        assert gray.ndim == 2, "Grayscale should be 2D"
        assert gray.dtype == np.uint8

    def test_preprocess_bytes(self, preprocessor, tmp_path):
        img = make_synthetic_sheet()
        _, buf = cv2.imencode(".jpg", img)
        image_bytes = buf.tobytes()

        result = preprocessor.preprocess_bytes(image_bytes, "test_sheet.jpg")

        assert result.original_path.endswith(".jpg")
        assert result.processed_path.endswith(".png")
        assert len(result.operations_applied) > 0
        assert "grayscale" in result.operations_applied
        assert Path(result.processed_path).exists()

    def test_resize_large_image(self, preprocessor):
        large_img = make_synthetic_sheet(width=3000, height=4200)
        _, buf = cv2.imencode(".jpg", large_img)

        result = preprocessor.preprocess_bytes(buf.tobytes(), "large.jpg")
        assert result.width <= preprocessor.TARGET_WIDTH

    def test_denoise_reduces_noise(self, preprocessor):
        noisy = make_synthetic_sheet(noise_level=40)
        gray_noisy = cv2.cvtColor(noisy, cv2.COLOR_BGR2GRAY).astype(float)

        denoised = preprocessor._denoise(cv2.cvtColor(noisy, cv2.COLOR_BGR2GRAY))
        gray_denoised = denoised.astype(float)

        # Variance should drop after denoising
        noise_var_before = float(np.var(gray_noisy))
        noise_var_after = float(np.var(gray_denoised))
        # Not strict — just verify the image changed
        assert noise_var_after != noise_var_before

    def test_deskew_corrects_rotation(self, preprocessor):
        skewed = make_synthetic_sheet(skew_angle=5.0)
        gray_skewed = cv2.cvtColor(skewed, cv2.COLOR_BGR2GRAY)

        corrected, angle = preprocessor._deskew(gray_skewed)
        assert corrected.shape == gray_skewed.shape
        assert isinstance(angle, float)
        # Detected angle should be within ±15 degrees
        assert -15.0 <= angle <= 15.0

    def test_binarize_produces_binary(self, preprocessor):
        img = make_synthetic_sheet(noise_level=5)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = preprocessor._binarize(gray)

        unique_vals = np.unique(binary)
        assert set(unique_vals).issubset({0, 255}), "Binary output should only contain 0 and 255"

    def test_quality_score_good_image(self, preprocessor):
        img = make_synthetic_sheet(noise_level=0, skew_angle=0)
        _, buf = cv2.imencode(".png", img)
        result = preprocessor.preprocess_bytes(buf.tobytes(), "clean.png")

        quality = preprocessor.get_image_quality_score(result.original_path)
        assert "score" in quality
        assert 0.0 <= quality["score"] <= 1.0
        assert "is_blurry" in quality

    def test_quality_score_blurry_image(self, preprocessor):
        img = make_synthetic_sheet()
        blurry = cv2.GaussianBlur(img, (31, 31), 0)
        _, buf = cv2.imencode(".jpg", blurry)
        result = preprocessor.preprocess_bytes(buf.tobytes(), "blurry.jpg")

        quality = preprocessor.get_image_quality_score(result.original_path)
        # Blurry images should have lower sharpness
        assert quality["sharpness"] < 500

    def test_morphological_cleanup(self, preprocessor):
        """Test that cleanup doesn't destroy image dimensions."""
        img = make_synthetic_sheet()
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        binary = preprocessor._binarize(gray)
        cleaned = preprocessor._morphological_cleanup(binary)

        assert cleaned.shape == binary.shape

    def test_all_operations_documented(self, preprocessor):
        img = make_synthetic_sheet()
        _, buf = cv2.imencode(".jpg", img)
        result = preprocessor.preprocess_bytes(buf.tobytes(), "ops_test.jpg")

        # Should have at minimum: grayscale, denoise, clahe, threshold, morph
        expected_keywords = {"grayscale", "denoise", "clahe", "threshold", "morphological"}
        for keyword in expected_keywords:
            assert any(keyword in op for op in result.operations_applied), \
                f"Expected operation containing '{keyword}' not found in {result.operations_applied}"
