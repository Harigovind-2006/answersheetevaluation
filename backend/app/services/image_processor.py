"""
Core image preprocessing library using OpenCV.
Designed for document/answer sheet cleaning and normalization.

Pipeline:
1. Resize (normalize width)
2. Document edge detection (find the paper) or Deskew
3. Grayscale & Contrast enhancement
4. Adaptive thresholding (binarize)
5. Morphological denoising
"""

import cv2
import numpy as np
import math
from pathlib import Path
import uuid
from loguru import logger
from ..models.schemas import ProcessedImage

class ImagePreprocessor:
    TARGET_WIDTH = 1500

    def __init__(self, target_width: int = 1500):
        self.target_width = target_width
        self.raw_dir = Path("uploads/raw")
        self.processed_dir = Path("uploads/processed")
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def preprocess_bytes(self, image_bytes: bytes, filename: str) -> ProcessedImage:
        """Main entry point for image cleaning."""
        uid = uuid.uuid4().hex[:8]
        raw_path = self.raw_dir / f"{uid}_{filename}"
        with open(raw_path, "wb") as f:
            f.write(image_bytes)
        
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Invalid image data")

        operations = []
        
        orig = img.copy()
        h, w = img.shape[:2]
        
        if w > self.TARGET_WIDTH:
            ratio = self.TARGET_WIDTH / float(w)
            img = cv2.resize(img, (self.TARGET_WIDTH, int(h * ratio)))
            operations.append("resize")

        # Find document edges
        ratio_small = img.shape[0] / 500.0
        small = cv2.resize(img, (int(img.shape[1] / ratio_small), 500))
        doc_contour = self._find_document_outline(small)
        
        if doc_contour is not None:
            doc_contour = doc_contour.reshape(4, 2) * ratio_small
            img = self._four_point_transform(img, doc_contour)
            operations.append("perspective_warp")
        
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        operations.append("grayscale")
        
        # Fallback to deskew if no contour was found
        if doc_contour is None:
            gray, angle = self._deskew(gray)
            if abs(angle) > 0.1:
                operations.append("deskew")
                
        denoised = self._denoise(gray)
        operations.append("denoise")
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        contrast = clahe.apply(denoised)
        operations.append("clahe")
        
        binary = self._binarize(contrast)
        operations.append("threshold")
        
        cleaned = self._morphological_cleanup(binary)
        operations.append("morphological")
        
        proc_path = self.processed_dir / f"clean_{uid}.png"
        cv2.imwrite(str(proc_path), cleaned)
        
        return ProcessedImage(
            original_path=str(raw_path),
            processed_path=str(proc_path),
            width=cleaned.shape[1],
            height=cleaned.shape[0],
            operations_applied=operations
        )

    def _find_document_outline(self, image):
        """Detect the largest rectangular contour (the paper)."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(gray, 75, 200)
        
        cnts, _ = cv2.findContours(edged.copy(), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
        cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:5]
        
        for c in cnts:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            if len(approx) == 4:
                return approx
        return None

    def _four_point_transform(self, image, pts):
        """Straightens the image based on detected corners."""
        rect = self._order_points(pts)
        (tl, tr, br, bl) = rect
        
        widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
        widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
        maxWidth = max(int(widthA), int(widthB))
        
        heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
        heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
        maxHeight = max(int(heightA), int(heightB))
        
        dst = np.array([
            [0, 0],
            [maxWidth - 1, 0],
            [maxWidth - 1, maxHeight - 1],
            [0, maxHeight - 1]], dtype="float32")
        
        M = cv2.getPerspectiveTransform(rect, dst)
        return cv2.warpPerspective(image, M, (maxWidth, maxHeight))

    def _order_points(self, pts):
        rect = np.zeros((4, 2), dtype="float32")
        s = pts.sum(axis=1)
        rect[0] = pts[np.argmin(s)]
        rect[2] = pts[np.argmax(s)]
        diff = np.diff(pts, axis=1)
        rect[1] = pts[np.argmin(diff)]
        rect[3] = pts[np.argmax(diff)]
        return rect

    def _deskew(self, image):
        edges = cv2.Canny(image, 50, 150, apertureSize=3)
        lines = cv2.HoughLinesP(edges, 1, np.pi/180, 100, minLineLength=100, maxLineGap=10)
        
        angle = 0.0
        if lines is not None:
            angles = []
            for line in lines:
                x1, y1, x2, y2 = line[0]
                a = math.degrees(math.atan2(y2 - y1, x2 - x1))
                if -45 < a < 45:
                    angles.append(a)
            if angles:
                angle = np.median(angles)
        
        if abs(angle) > 0.1:
            (h, w) = image.shape[:2]
            center = (w // 2, h // 2)
            M = cv2.getRotationMatrix2D(center, angle, 1.0)
            rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
            return rotated, float(angle)
            
        return image, 0.0

    def _denoise(self, image):
        return cv2.fastNlMeansDenoising(image, None, 10, 7, 21)

    def _binarize(self, image):
        return cv2.adaptiveThreshold(
            image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )

    def _morphological_cleanup(self, image):
        return image.copy()
        
    def get_image_quality_score(self, path: str) -> dict:
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return {"score": 0.0, "is_blurry": True, "sharpness": 0.0}
            
        laplacian_var = cv2.Laplacian(img, cv2.CV_64F).var()
        is_blurry = laplacian_var < 500
        score = min(1.0, laplacian_var / 2000.0)
        
        return {
            "score": float(score),
            "is_blurry": bool(is_blurry),
            "sharpness": float(laplacian_var)
        }
