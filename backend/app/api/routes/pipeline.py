"""
Main processing pipeline endpoint.
POST /api/process — Upload images → OpenCV clean → OCR → Gemini grade
"""

from __future__ import annotations

import json
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from loguru import logger

from ...core.config import get_settings
from ...models.schemas import (
    FullPipelineResponse,
    GradeRequest,
    ModelAnswer,
    GradeOnlyRequest,
)
from ...services.grading_service import GeminiGrader
from ...services.image_processor import ImagePreprocessor
from ...services.ocr_service import OCRService
from ...services.key_extraction_service import KeyExtractor

router = APIRouter(prefix="/api", tags=["pipeline"])
settings = get_settings()

preprocessor = ImagePreprocessor()
ocr_service = OCRService()
grader = GeminiGrader()
key_extractor = KeyExtractor()


async def _get_ocr_text_from_files(files: list[UploadFile] | None) -> str:
    """Helper to preprocess and OCR a list of uploaded files, returning combined raw text."""
    if not files:
        return ""
    
    paths = []
    for upload in files:
        data = await upload.read()
        processed = preprocessor.preprocess_bytes(data, upload.filename or "doc.jpg")
        paths.append(processed.processed_path)
    
    ocr_result = await ocr_service.extract_from_multiple_files(paths)
    return ocr_result.raw_text


@router.post(
    "/process",
    response_model=FullPipelineResponse,
    summary="Full pipeline: images → preprocess → OCR → grade",
)
async def process_answer_sheet(
    images: Annotated[list[UploadFile], File(description="One or more answer sheet images")],
    grade_request: Annotated[str, Form(description="JSON string of GradeRequest")],
    question_paper: Annotated[list[UploadFile] | None, File(description="One or more question paper images")] = None,
    answer_key: Annotated[list[UploadFile] | None, File(description="One or more answer key images")] = None,
):
    """
    Full automated pipeline:
    1. Validate and save uploaded images
    2. OpenCV preprocessing (denoise, deskew, binarize)
    3. GPT-5.4 OCR (Vision JSON output)
    4. Gemini grading (numerical scores only)
    5. Return structured result

    The `grade_request` form field must be a JSON string matching this schema:
    ```json
    {
      "exam_id": "...",
      "exam_title": "Mathematics Mid-Term",
      "student_name": "John Smith",   // optional if OCR can detect
      "roll_number": "2024CS001",     // optional if OCR can detect
      "model_answers": [
        {"question_id": "q1", "question_number": 1, "model_answer": "...", "max_marks": 10},
        ...
      ]
    }
    ```
    """
    steps: list[str] = []
    errors: list[str] = []

    # ── Parse grade request ──
    try:
        req = GradeRequest(**json.loads(grade_request))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid grade_request JSON: {e}",
        )

    # ── Validate files ──
    if not images:
        raise HTTPException(status_code=400, detail="No images provided")
    if len(images) > settings.max_pages:
        raise HTTPException(
            status_code=400,
            detail=f"Too many pages. Max allowed: {settings.max_pages}",
        )

    # ── Handle Question Paper / Answer Key Extraction ──
    if not req.model_answers:
        if not (question_paper or answer_key):
            raise HTTPException(
                status_code=400,
                detail="No model_answers provided and no question_paper/answer_key uploaded.",
            )
        
        steps.append("key_documents_upload_received")
        try:
            qp_text = await _get_ocr_text_from_files(question_paper)
            ak_text = await _get_ocr_text_from_files(answer_key)
            
            steps.append("key_documents_ocr_complete")
            
            extracted_marking_scheme = await key_extractor.extract_key(
                question_paper_text=qp_text,
                answer_key_text=ak_text
            )
            
            if not extracted_marking_scheme:
                raise ValueError("Could not extract any questions/answers from provided documents.")
                
            req.model_answers = extracted_marking_scheme
            steps.append("key_extraction_complete")
            logger.info(f"Extracted {len(req.model_answers)} model answers from uploaded files.")
            
        except Exception as e:
            logger.error(f"Key extraction error: {e}")
            return FullPipelineResponse(
                success=False,
                message=f"Failed to extract marking scheme: {str(e)}",
                errors=errors + [str(e)],
                processing_steps=steps,
            )

    processed_paths: list[str] = []

    # ── STEP 1: Preprocess with OpenCV ──
    logger.info(f"Pipeline started for {req.student_name or 'unknown'} | {req.exam_title}")
    steps.append("upload_received")

    try:
        for i, upload in enumerate(images):
            if upload.content_type not in ("image/jpeg", "image/png", "image/webp", "image/tiff"):
                errors.append(f"Page {i+1}: unsupported file type {upload.content_type}")
                continue

            image_bytes = await upload.read()

            if len(image_bytes) > settings.max_file_size_bytes:
                errors.append(f"Page {i+1}: file too large ({len(image_bytes) // 1024}KB)")
                continue

            processed = preprocessor.preprocess_bytes(image_bytes, upload.filename or f"page_{i+1}.jpg")
            processed_paths.append(processed.processed_path)

            logger.info(
                f"Page {i+1} preprocessed: {processed.operations_applied} → {processed.processed_path}"
            )

        steps.append("opencv_preprocessing_complete")

        if not processed_paths:
            return FullPipelineResponse(
                success=False,
                message="No images could be processed",
                errors=errors,
                processing_steps=steps,
            )

    except Exception as e:
        logger.error(f"Preprocessing error: {e}")
        return FullPipelineResponse(
            success=False,
            message=f"Image preprocessing failed: {str(e)}",
            errors=errors + [str(e)],
            processing_steps=steps,
        )

    # ── STEP 2: OCR ──
    try:
        ocr_result = await ocr_service.extract_from_multiple_files(processed_paths)
        steps.append("easyocr_complete")

        # Fill in student info from OCR if not provided
        student_name = req.student_name or ocr_result.student_name or "Unknown Student"
        roll_number = req.roll_number or ocr_result.roll_number or "N/A"

        logger.info(
            f"OCR: {len(ocr_result.extracted_answers)} answers extracted, "
            f"avg confidence: {ocr_result.avg_confidence:.2f}"
        )

    except Exception as e:
        logger.error(f"OCR error: {e}")
        return FullPipelineResponse(
            success=False,
            message=f"OCR failed: {str(e)}",
            errors=errors + [str(e)],
            processing_steps=steps,
            processed_image_paths=processed_paths,
        )

    # ── STEP 3: Gemini grading ──
    try:
        grading_result = await grader.grade(
            student_answers=ocr_result.extracted_answers,
            model_answers=req.model_answers,
            exam_title=req.exam_title,
            student_name=student_name,
            roll_number=roll_number,
            exam_id=req.exam_id,
        )
        steps.append("gemini_grading_complete")

    except Exception as e:
        logger.error(f"Grading error: {e}")
        return FullPipelineResponse(
            success=False,
            message=f"Grading failed: {str(e)}",
            ocr_result=ocr_result,
            errors=errors + [str(e)],
            processing_steps=steps,
            processed_image_paths=processed_paths,
        )

    steps.append("pipeline_complete")

    return FullPipelineResponse(
        success=True,
        message="Answer sheet processed and graded successfully",
        ocr_result=ocr_result,
        grading_result=grading_result,
        processed_image_paths=processed_paths,
        processing_steps=steps,
        errors=errors,
    )


@router.post(
    "/preprocess-only",
    summary="Run only OpenCV preprocessing on uploaded images",
)
async def preprocess_only(
    images: Annotated[list[UploadFile], File()],
):
    """
    Preprocess images with OpenCV only (no OCR, no grading).
    Useful for preview and quality checking before full pipeline.
    """
    results = []
    for upload in images:
        image_bytes = await upload.read()
        processed = preprocessor.preprocess_bytes(image_bytes, upload.filename or "image.jpg")
        quality = preprocessor.get_image_quality_score(processed.original_path)
        results.append({
            "original": upload.filename,
            "processed_path": processed.processed_path,
            "operations": processed.operations_applied,
            "dimensions": f"{processed.width}x{processed.height}",
            "quality": quality,
        })

    return {"success": True, "results": results}


@router.post(
    "/ocr-only",
    summary="Run OCR only on already-preprocessed or raw images",
)
async def ocr_only(
    images: Annotated[list[UploadFile], File()],
    preprocess: bool = True,
):
    """
    Run OCR only, optionally with preprocessing.
    Returns raw text + extracted answers with confidence scores.
    """
    image_paths: list[str] = []

    for upload in images:
        data = await upload.read()
        if preprocess:
            processed = preprocessor.preprocess_bytes(data, upload.filename or "img.jpg")
            image_paths.append(processed.processed_path)
        else:
            import uuid, pathlib
            p = pathlib.Path("uploads/raw") / f"{uuid.uuid4().hex[:8]}.jpg"
            p.write_bytes(data)
            image_paths.append(str(p))

    ocr_result = await ocr_service.extract_from_multiple_files(image_paths)

    return {
        "success": True,
        "raw_text": ocr_result.raw_text,
        "extracted_answers": [a.model_dump() for a in ocr_result.extracted_answers],
        "student_name": ocr_result.student_name,
        "roll_number": ocr_result.roll_number,
        "avg_confidence": ocr_result.avg_confidence,
        "page_count": ocr_result.page_count,
    }


@router.post(
    "/grade-only",
    summary="Run Gemini grading on provided OCR answers and model answers",
)
async def grade_only(request: GradeOnlyRequest):
    """
    Run Gemini grading separately from OCR. 
    Useful when the OCR and answers are already available or modified by the user.
    """
    try:
        grading_result = await grader.grade(
            student_answers=request.student_answers,
            model_answers=request.model_answers,
            exam_title=request.exam_title,
            student_name=request.student_name,
            roll_number=request.roll_number,
            exam_id=request.exam_id,
        )
        return {"success": True, "grading_result": grading_result.model_dump()}
    except Exception as e:
        logger.error(f"Grading error: {e}")
        return {"success": False, "message": str(e), "errors": [str(e)]}

