from __future__ import annotations
from enum import Enum
from typing import Optional, Any
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, Field

# ──────────────────────────────────────────────────────────────────────────────
# Enums
# ──────────────────────────────────────────────────────────────────────────────

class UserRole(str, Enum):
    ADMIN = 'admin'
    TEACHER = 'teacher'

class ProcessingStep(str, Enum):
    UPLOAD      = "upload"
    PREPROCESS  = "preprocess"
    OCR         = "ocr"
    GRADING     = "grading"
    COMPLETE    = "complete"


# ──────────────────────────────────────────────────────────────────────────────
# Database Table Schemas (Pydantic Models)
# ──────────────────────────────────────────────────────────────────────────────

class ProfileBase(BaseModel):
    email: str
    full_name: str
    role: UserRole = UserRole.TEACHER
    department: Optional[str] = None
    is_active: bool = True

class ProfileDB(ProfileBase):
    id: UUID
    created_at: datetime
    updated_at: datetime


class StudentBase(BaseModel):
    student_name: str
    roll_number: str

class StudentDB(StudentBase):
    student_id: UUID
    created_at: datetime


class ExamBase(BaseModel):
    exam_title: str
    total_marks: int = 0
    created_by: Optional[UUID] = None

class ExamDB(ExamBase):
    exam_id: UUID
    created_at: datetime


class ModelAnswer(BaseModel):
    question_id: str
    question_number: int
    model_answer: str
    max_marks: int
    section: Optional[str] = None
    acceptable_answers: list[str] = Field(default_factory=list)

class ModelAnswerDB(ModelAnswer):
    id: UUID
    exam_id: UUID
    created_at: datetime


class AnswerSheetBase(BaseModel):
    student_id: Optional[UUID] = None
    exam_id: Optional[UUID] = None
    original_path: Optional[str] = None
    processed_path: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    operations_applied: list[str] = Field(default_factory=list)
    page_count: int = 1

class AnswerSheetDB(AnswerSheetBase):
    sheet_id: UUID
    upload_time: datetime


class ExtractedAnswer(BaseModel):
    question_id: str
    question_number: int
    answer_text: str
    confidence: float = Field(ge=0.0, le=1.0)
    section: Optional[str] = None
    bounding_box: Optional[dict[str, Any]] = None

class ExtractedAnswerDB(ExtractedAnswer):
    id: UUID
    ocr_id: UUID


class OCRResult(BaseModel):
    raw_text: str
    extracted_answers: list[ExtractedAnswer] = Field(default_factory=list)
    student_name: str = ""
    roll_number: str = ""
    page_count: int = 1
    avg_confidence: float = 0.0

class OCRResultDB(BaseModel):
    ocr_id: UUID
    sheet_id: Optional[UUID] = None
    raw_text: str
    avg_confidence: float = 0.0
    page_count: int = 1
    created_at: datetime


class QuestionScore(BaseModel):
    question_number: int
    marks_obtained: int
    max_marks: int

    @property
    def percentage(self) -> float:
        return (self.marks_obtained / self.max_marks * 100) if self.max_marks > 0 else 0.0

    @property
    def display(self) -> str:
        return f"{self.marks_obtained}/{self.max_marks}"

class QuestionScoreDB(QuestionScore):
    id: UUID
    grading_id: UUID
    question_key: str
    created_at: datetime


class GradingResult(BaseModel):
    student_name: str
    roll_number: str
    exam_id: str
    exam_title: str
    question_scores: dict[str, QuestionScore]   # "q1" -> QuestionScore
    total_marks_obtained: int
    total_marks_available: int
    percentage: float
    grade: str
    graded_at: str = ""

class GradingResultDB(BaseModel):
    grading_id: UUID
    sheet_id: Optional[UUID] = None
    exam_id: str
    exam_title: str
    student_name: str
    roll_number: str
    total_marks_obtained: int
    total_marks_available: int
    percentage: float
    grade: str
    graded_at: datetime


class PipelineLogBase(BaseModel):
    sheet_id: Optional[UUID] = None
    success: bool
    message: Optional[str] = None
    processing_steps: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

class PipelineLogDB(PipelineLogBase):
    log_id: UUID
    created_at: datetime


class LoginLogBase(BaseModel):
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    role: Optional[UserRole] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    success: bool = True

class LoginLogDB(LoginLogBase):
    log_id: UUID
    login_at: datetime


# ──────────────────────────────────────────────────────────────────────────────
# Endpoint Specific Models
# ──────────────────────────────────────────────────────────────────────────────

class ProcessedImage(BaseModel):
    original_path: str
    processed_path: str
    width: int
    height: int
    operations_applied: list[str]


class GradeRequest(BaseModel):
    exam_id: str
    exam_title: str
    student_name: str = ""
    roll_number: str = ""
    total_marks: int = 0
    passing_marks: int = 0
    model_answers: list[ModelAnswer] = Field(default_factory=list)


class GradeOnlyRequest(BaseModel):
    student_answers: list[ExtractedAnswer]
    model_answers: list[ModelAnswer]
    exam_title: str
    student_name: str = ""
    roll_number: str = ""
    exam_id: str = ""


class FullPipelineResponse(BaseModel):
    success: bool
    message: str
    ocr_result: Optional[OCRResult] = None
    grading_result: Optional[GradingResult] = None
    processed_image_paths: list[str] = Field(default_factory=list)
    processing_steps: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class HealthResponse(BaseModel):
    status: str
    version: str
    services: dict[str, bool]


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str

