"""
Export endpoints — CSV and PDF generation.
"""

from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from ...models.schemas import GradingResult
from ...services.export_service import ExportService

router = APIRouter(prefix="/api/export", tags=["export"])
exporter = ExportService()


@router.post("/csv", summary="Export results to CSV")
async def export_csv(
    results_json: str,
    exam_title: str = "Exam Results",
):
    """
    Body: JSON array of GradingResult objects.
    Returns: CSV file download.
    """
    try:
        raw = json.loads(results_json)
        results = [GradingResult(**r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid results JSON: {e}")

    csv_bytes = exporter.to_csv_bytes(results, exam_title)
    filename = exam_title.replace(" ", "_") + ".csv"

    return Response(
        content=csv_bytes,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/pdf", summary="Export results to PDF")
async def export_pdf(
    results_json: str,
    exam_title: str = "Exam Results",
):
    """
    Body: JSON array of GradingResult objects.
    Returns: PDF file download.
    """
    try:
        raw = json.loads(results_json)
        results = [GradingResult(**r) for r in raw]
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid results JSON: {e}")

    pdf_bytes = exporter.to_pdf_bytes(results, exam_title)
    filename = exam_title.replace(" ", "_") + ".pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
