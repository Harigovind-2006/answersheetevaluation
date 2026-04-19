import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from loguru import logger

# Add the current directory so we can import 'app'
sys.path.append(os.getcwd())

# Import your services (adjust paths if needed based on your local python path)
try:
    from app.services.ocr_service import OCRService
    from app.services.grading_service import GeminiGrader
    from app.models.schemas import ModelAnswer, ExtractedAnswer
except ImportError as e:
    logger.error(f"Import failed: {e}. Make sure you run this script from the 'backend' root directory.")
    sys.exit(1)

async def run_sample_evaluation():
    # 1. Setup
    load_dotenv()
    ocr = OCRService()
    grader = GeminiGrader()

    # 2. Sample Answer Sheet (use the generated image path here)
    # REPLACE with actual image path if you have a real one
    # For now, we'll assume a path like "uploads/raw/sample_handwritten.png"
    sample_image_path = "uploads/raw/sample_handwritten.png"
    
    # Ensure sample dir exists for testing
    os.makedirs("uploads/raw", exist_ok=True)
    
    if not os.path.exists(sample_image_path):
        logger.warning(f"Please place a sample image at {sample_image_path}")
        # return 

    # 3. Model Answer Key (Defining what the student SHOULD have written)
    model_answers = [
        ModelAnswer(
            question_id="q1",
            question_number="1",
            model_answer="Photosynthesis is the process where plants use sunlight, CO2 and water to make glucose and oxygen.",
            max_marks=10,
            acceptable_answers=["Solar energy", "Chloroplasts"]
        ),
        ModelAnswer(
            question_id="q2",
            question_number="2",
            model_answer="A simple cell diagram should include a nucleus, cell membrane, and mitochondria.",
            max_marks=10
        ),
        ModelAnswer(
            question_id="q3",
            question_number="3",
            model_answer="x = 5 for the equation 2x + 10 = 20.",
            max_marks=5
        )
    ]

    print("\n" + "="*50)
    print("      SAMPLE EVALUATION PIPELINE (GEMINI)")
    print("="*50)
    
    logger.info("Step 1: OCR EXTRACTION")
    logger.info("Extracting text from handwritten sheet...")
    
    try:
        # Note: In a real test, you'd provide the actual image path.
        # This will fail without a real file and valid Gemini Key.
        ocr_result = await ocr.extract_from_multiple_files(
            image_paths=[sample_image_path],
            expected_questions=["1", "2", "3"]
        )
        
        print(f"\n[OCR Result]")
        print(f"Student Name: {ocr_result.student_name}")
        print(f"Roll Number : {ocr_result.roll_number}")
        print("\nExtracted Answers:")
        for ans in ocr_result.extracted_answers:
            print(f"- Q{ans.question_number}: {ans.answer_text[:100]}...")

        logger.info("Step 2: GRADING")
        logger.info("Grading extracted answers against model key...")
        
        grading_result = await grader.grade(
            student_answers=ocr_result.extracted_answers,
            model_answers=model_answers,
            exam_title="Biology & Math Quiz",
            student_name=ocr_result.student_name,
            roll_number=ocr_result.roll_number,
            raw_student_text=ocr_result.raw_text
        )

        print("\n" + "-"*30)
        print("      GRADING SUMMARY")
        print("-"*30)
        print(f"Total Marks: {grading_result.total_marks_obtained}/{grading_result.total_marks_available}")
        print(f"Percentage : {grading_result.percentage}%")
        print(f"Grade      : {grading_result.grade}")
        
        print("\nPer-Question Breakdown:")
        for q_id in sorted(grading_result.question_scores.keys()):
            score = grading_result.question_scores[q_id]
            print(f"  [{q_id}]: {score.marks_obtained}/{score.max_marks} ({(score.marks_obtained/score.max_marks)*100:.1f}%)")
        print("="*50)

    except Exception as e:
        logger.error(f"Sample pipeline failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_sample_evaluation())
