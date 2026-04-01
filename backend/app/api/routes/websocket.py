from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger
import json
import base64
import asyncio
import fitz
from typing import List, Dict

from ...services.image_processor import ImagePreprocessor
from ...services.ocr_service import OCRService
from ...services.grading_service import GeminiGrader
from ...services.key_extraction_service import KeyExtractor
from ...models.schemas import GradeRequest, FullPipelineResponse

router = APIRouter(tags=["websocket"])

preprocessor = ImagePreprocessor()
ocr_service = OCRService()
grader = GeminiGrader()
key_extractor = KeyExtractor()

@router.websocket("/ws/process")
async def websocket_process(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connection accepted for processing")
    
    images_data: List[Dict] = []        # {"filename": str, "data": base64_str}
    answer_key_data: List[Dict] = []    # {"filename": str, "data": base64_str}
    question_paper_data: List[Dict] = [] # {"filename": str, "data": base64_str}
    grade_request_data: Dict = {}
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            msg_type = message.get("type")
            
            if msg_type == "config":
                grade_request_data = message.get("data", {})
                await websocket.send_json({"status": "info", "message": "Configuration received"})
                
            elif msg_type == "image":
                images_data.append({
                    "filename": message.get("filename") or f"upload_{len(images_data)+1}.jpg",
                    "data": message.get("data", "")
                })
                await websocket.send_json({
                    "status": "info", 
                    "message": f"Received sheet {len(images_data)}"
                })

            elif msg_type == "answer_key":
                answer_key_data.append({
                    "filename": message.get("filename") or f"answer_key_{len(answer_key_data)+1}.jpg",
                    "data": message.get("data", "")
                })
                await websocket.send_json({
                    "status": "info",
                    "message": f"Received answer key {len(answer_key_data)}"
                })

            elif msg_type == "question_paper":
                question_paper_data.append({
                    "filename": message.get("filename") or f"question_paper_{len(question_paper_data)+1}.jpg",
                    "data": message.get("data", "")
                })
                await websocket.send_json({
                    "status": "info",
                    "message": f"Received question paper {len(question_paper_data)}"
                })
                
            elif msg_type == "process":
                if not images_data:
                    await websocket.send_json({"status": "error", "message": "No images received"})
                    continue
                
                await websocket.send_json({"status": "progress", "message": "Starting pipeline...", "percent": 5})
                
                # ── STEP 1: Preprocess student sheets ──
                await websocket.send_json({"status": "progress", "message": "Preprocessing answer sheets...", "percent": 15})
                processed_paths = []
                for entry in images_data:
                    image_bytes = base64.b64decode(entry["data"])
                    processed = preprocessor.preprocess_bytes(image_bytes, entry["filename"])
                    processed_paths.append(processed.processed_path)

                # ── STEP 2: Extract model answers from answer key / question paper ──
                req = GradeRequest(**grade_request_data)
                
                if not req.model_answers and (answer_key_data or question_paper_data):
                    await websocket.send_json({"status": "progress", "message": "Processing answer key...", "percent": 30})
                    try:
                        # Helper to extract native text or fallback to OCR
                        def process_entries(entries):
                            extracted_text = ""
                            image_paths = []
                            for entry in entries:
                                img_bytes = base64.b64decode(entry["data"])
                                filename = entry.get("filename", "").lower()
                                
                                # Try native PDF extraction first
                                if filename.endswith(".pdf"):
                                    try:
                                        doc = fitz.open(stream=img_bytes, filetype="pdf")
                                        for page in doc:
                                            extracted_text += page.get_text() + "\n"
                                        doc.close()
                                    except Exception as e:
                                        logger.warning(f"Native PDF text extraction failed: {e}")
                                
                                # If no meaningful text was extracted, treat it as image for OCR
                                if len(extracted_text.strip()) < 50:
                                    logger.info(f"Extracting '{filename}' as Image/Scanned PDF for OCR")
                                    # We reset extracted_text to avoid partial junk text
                                    extracted_text = ""
                                    result = preprocessor.preprocess_bytes(img_bytes, entry["filename"])
                                    image_paths.append(result.processed_path)
                                else:
                                    logger.info(f"Successfully extracted native text from '{filename}', skipping Gemini OCR.")
                                    
                            return extracted_text.strip(), image_paths

                        ak_native_text, ak_paths = process_entries(answer_key_data)
                        qp_native_text, qp_paths = process_entries(question_paper_data)

                        ak_text = ak_native_text
                        qp_text = qp_native_text
                        
                        # Only run OCR if native text extraction failed
                        if ak_paths:
                            await websocket.send_json({"status": "progress", "message": "Using AI OCR on Answer Key...", "percent": 35})
                            ak_ocr = await ocr_service.extract_from_multiple_files(ak_paths)
                            ak_text += "\n" + ak_ocr.raw_text
                            
                        if qp_paths:
                            await websocket.send_json({"status": "progress", "message": "Using AI OCR on Question Paper...", "percent": 40})
                            qp_ocr = await ocr_service.extract_from_multiple_files(qp_paths)
                            qp_text += "\n" + qp_ocr.raw_text

                        await websocket.send_json({"status": "progress", "message": "Extracting marking scheme...", "percent": 45})
                        extracted = await key_extractor.extract_key(
                            question_paper_text=qp_text,
                            answer_key_text=ak_text
                        )
                        if extracted:
                            req.model_answers = extracted
                            logger.info(f"Extracted {len(req.model_answers)} model answers from uploaded key")
                        else:
                            logger.warning("Key extraction returned no answers")

                    except Exception as e:
                        logger.error(f"Key extraction error: {e}")
                        await websocket.send_json({
                            "status": "error",
                            "message": f"Failed to extract marking scheme from answer key: {e}"
                        })
                        continue

                # ── STEP 3: OCR student sheets ──
                await websocket.send_json({"status": "progress", "message": f"Running OCR on {len(processed_paths)} page(s)...", "percent": 60})
                
                expected_q_nums = None
                if req.model_answers:
                    expected_q_nums = [ma.question_number for ma in req.model_answers]
                
                ocr_result = await ocr_service.extract_from_multiple_files(processed_paths, expected_questions=expected_q_nums)
                
                # ── STEP 4: Grading ──
                await websocket.send_json({"status": "progress", "message": "Evaluating answers with Gemini AI...", "percent": 80})
                
                grading_result = await grader.grade(
                    student_answers=ocr_result.extracted_answers,
                    model_answers=req.model_answers,
                    exam_title=req.exam_title,
                    student_name=req.student_name or ocr_result.student_name or "Unknown",
                    roll_number=req.roll_number or ocr_result.roll_number or "N/A",
                    exam_id=req.exam_id if hasattr(req, 'exam_id') else '',
                    total_marks=req.total_marks,
                    passing_marks=req.passing_marks,
                    raw_student_text=ocr_result.raw_text,
                )
                
                # ── STEP 5: Return result ──
                final_response = FullPipelineResponse(
                    success=True,
                    message="Processed successfully via WebSocket",
                    ocr_result=ocr_result,
                    grading_result=grading_result,
                    processed_image_paths=processed_paths,
                    processing_steps=["websocket_upload", "opencv", "key_extraction", "ocr", "gemini"],
                    errors=[]
                )
                
                await websocket.send_json({
                    "status": "complete", 
                    "message": "Processing complete!", 
                    "percent": 100,
                    "data": final_response.model_dump()
                })
                
            elif msg_type == "ping":
                await websocket.send_json({"status": "pong"})

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        try:
            await websocket.send_json({"status": "error", "message": str(e)})
        except:
            pass
