import os

def enhance_grading_robustness():
    base_dir = r"c:\Users\harig\Desktop\project\mini project\app\backend\app"
    grading_path = os.path.join(base_dir, "services", "grading_service.py")
    ws_path = os.path.join(base_dir, "api", "routes", "websocket.py")

    # --- grading_service.py ---
    with open(grading_path, "r", encoding="utf-8") as f:
        grad_content = f.read()

    # Update grade signature
    grad_sig_old = """    async def grade(
        self,
        student_answers: list[ExtractedAnswer],
        model_answers: list[ModelAnswer],
        exam_title: str,
        student_name: str = "",
        roll_number: str = "",
        exam_id: str = "",
        total_marks: int = 0,
        passing_marks: int = 0,
    ) -> GradingResult:"""
    grad_sig_new = """    async def grade(
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
    ) -> GradingResult:"""
    grad_content = grad_content.replace(grad_sig_old, grad_sig_new)

    # Update build prompt call
    prompt_call_old = "        prompt = self._build_prompt(student_answers, model_answers, exam_title)"
    prompt_call_new = "        prompt = self._build_prompt(student_answers, model_answers, exam_title, raw_student_text)"
    grad_content = grad_content.replace(prompt_call_old, prompt_call_new)

    # Update build prompt def
    build_sig_old = """    def _build_prompt(
        self,
        student_answers: list[ExtractedAnswer],
        model_answers: list[ModelAnswer],
        exam_title: str,
    ) -> str:"""
    build_sig_new = """    def _build_prompt(
        self,
        student_answers: list[ExtractedAnswer],
        model_answers: list[ModelAnswer],
        exam_title: str,
        raw_student_text: str = "",
    ) -> str:"""
    grad_content = grad_content.replace(build_sig_old, build_sig_new)

    # Add raw text to prompt
    ans_block_old = """            
        if not student_answers:
            lines.append("[NO ANSWERS EXTRACTED FROM SHEET]")"""
    ans_block_new = """            
        if not student_answers:
            lines.append("[NO STRUCTURED ANSWERS EXTRACTED FROM SHEET]")
            
        if raw_student_text:
            lines += ["", "--- RAW STUDENT SHEET TRANSCRIPTION (FALLBACK) ---"]
            lines.append("If the structured answers above are missing or incomplete, search through this raw transcription to find and map answers to the questions:")
            lines.append(raw_student_text)
            lines.append("--------------------------------------------------")"""
    grad_content = grad_content.replace(ans_block_old, ans_block_new)

    with open(grading_path, "w", encoding="utf-8") as f:
        f.write(grad_content)

    # --- websocket.py ---
    with open(ws_path, "r", encoding="utf-8") as f:
        ws_content = f.read()

    ws_call_old = """                grading_result = await grader.grade(
                    student_answers=ocr_result.extracted_answers,
                    model_answers=req.model_answers,
                    exam_title=req.exam_title,
                    student_name=req.student_name or ocr_result.student_name or "Unknown",
                    roll_number=req.roll_number or ocr_result.roll_number or "N/A",
                    exam_id=req.exam_id,
                    total_marks=req.total_marks,
                    passing_marks=req.passing_marks,
                )"""
    ws_call_new = """                grading_result = await grader.grade(
                    student_answers=ocr_result.extracted_answers,
                    model_answers=req.model_answers,
                    exam_title=req.exam_title,
                    student_name=req.student_name or ocr_result.student_name or "Unknown",
                    roll_number=req.roll_number or ocr_result.roll_number or "N/A",
                    exam_id=req.req.exam_id if hasattr(req, 'exam_id') else '',
                    total_marks=req.total_marks,
                    passing_marks=req.passing_marks,
                    raw_student_text=ocr_result.raw_text,
                )"""
    # Wait there's a typo in req.req.exam_id
    ws_call_new = ws_call_new.replace("req.req", "req")
    
    ws_content = ws_content.replace(ws_call_old, ws_call_new)
    
    with open(ws_path, "w", encoding="utf-8") as f:
        f.write(ws_content)

if __name__ == "__main__":
    enhance_grading_robustness()
