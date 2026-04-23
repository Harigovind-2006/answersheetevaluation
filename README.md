# 📝 AutoGrade — AI-Powered Answer Sheet Evaluation

An end-to-end system for automatically grading handwritten student answer sheets using computer vision, multimodal AI (Gemini), and a Flutter mobile frontend.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Flutter Frontend                         │
│  (Camera / File Picker → Upload Screen → Results Dashboard) │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTP (multipart/form-data)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  FastAPI Backend (Python)                    │
│                                                             │
│  Image Upload                                               │
│      │                                                      │
│      ▼                                                      │
│  OpenCV Preprocessing                                       │
│  (resize → edge detect / deskew → CLAHE → binarize)        │
│      │                                                      │
│      ▼                                                      │
│  Gemini 2.5 Flash OCR                                       │
│  (multimodal vision → structured JSON extraction)           │
│      │                                                      │
│      ▼                                                      │
│  Gemini 2.5 Flash Grader                                    │
│  (compare student answers vs model answers → scores)        │
│      │                                                      │
│      ▼                                                      │
│  JSON Result / CSV / PDF Export                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📂 Project Structure

```
app/
├── backend/                    # Python FastAPI server
│   ├── app/
│   │   ├── api/routes/
│   │   │   ├── pipeline.py     # POST /api/process (main endpoint)
│   │   │   ├── export.py       # CSV / PDF export
│   │   │   └── health.py       # GET /health
│   │   ├── core/
│   │   │   ├── config.py       # Pydantic settings (env vars)
│   │   │   └── logging.py      # Loguru setup
│   │   ├── models/
│   │   │   └── schemas.py      # All Pydantic request/response models
│   │   ├── services/
│   │   │   ├── image_processor.py  # OpenCV pipeline
│   │   │   ├── ocr_service.py      # Gemini multimodal OCR
│   │   │   ├── grading_service.py  # Gemini AI grader
│   │   │   └── export_service.py   # ReportLab PDF / openpyxl CSV
│   │   └── main.py             # FastAPI app factory + CORS
│   ├── tests/
│   ├── uploads/
│   │   ├── raw/                # Original uploaded files
│   │   └── processed/          # OpenCV-cleaned images
│   ├── .env.example
│   ├── requirements.txt
│   ├── pytest.ini
│   └── run.py
│
└── frontend/                   # Flutter mobile app
    ├── lib/
    │   ├── main.dart
    │   ├── theme.dart
    │   ├── screens/
    │   │   ├── login_screen.dart
    │   │   ├── register_screen.dart
    │   │   ├── main_screen.dart
    │   │   ├── dashboard_screen.dart
    │   │   ├── upload_screen.dart
    │   │   └── camera_screen.dart
    │   └── services/
    └── pubspec.yaml
```

---

## ✨ Features

| Feature | Details |
|---|---|
| **AI OCR** | Gemini 2.5 Flash reads handwritten answers from multi-page answer sheets |
| **Auto Grading** | Gemini compares student answers to a model answer key and returns per-question scores |
| **Image Preprocessing** | OpenCV pipeline: resize → perspective warp / deskew → CLAHE → adaptive threshold |
| **PDF Support** | PyMuPDF converts multi-page PDFs to images before processing |
| **Auto Marking Scheme** | If no model answers are provided, Gemini extracts them from an uploaded question paper / answer key |
| **Export** | Download results as CSV (openpyxl) or a styled PDF report (ReportLab) |
| **Mobile Frontend** | Flutter app with camera capture, file picker, and results dashboard |
| **Rate Limit Handling** | Automatic 40 s retry with back-off on Gemini 429 errors |

---

## 🚀 Backend — Quick Start

### 1. Clone & create virtual environment

```bash
git clone <repo-url>
cd app/backend

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
copy .env.example .env        # Windows
# cp .env.example .env        # Linux / macOS
```

Open `.env` and fill in the following keys:

| Key | Description |
|---|---|
| `GEMINI_API_KEY` | API key from [Google AI Studio](https://aistudio.google.com) |
| `GOOGLE_VISION_SERVICE_ACCOUNT_PATH` | Path to your GCP Vision service account JSON *(optional if using Gemini OCR)* |
| `FIREBASE_SERVICE_ACCOUNT_PATH` | Path to Firebase service account JSON *(optional)* |
| `FIREBASE_STORAGE_BUCKET` | Firebase Storage bucket name *(optional)* |

> **Tip:** The project currently uses **Gemini multimodal** for OCR (no Cloud Vision required unless you re-enable it). You only need `GEMINI_API_KEY` to get started.

### 4. Run the server

```bash
python run.py
```

- API base: `http://localhost:8000`
- Interactive docs: `http://localhost:8000/docs`

---

## 📡 API Reference

### `POST /api/process` — Full Grading Pipeline

Upload one or more answer sheet images together with exam metadata. Returns per-question scores, total marks, and a Pass/Fail grade.

**Form fields:**

| Field | Type | Required | Description |
|---|---|---|---|
| `images` | File(s) | ✅ | Student answer sheet (JPEG / PNG / WEBP / PDF) |
| `grade_request` | JSON string | ✅ | Exam metadata and model answers (see schema below) |
| `question_paper` | File(s) | ❌ | Question paper image(s) — used to auto-extract marking scheme |
| `answer_key` | File(s) | ❌ | Answer key image(s) — used to auto-extract marking scheme |

**`grade_request` JSON schema:**

```json
{
  "exam_id": "mid2024",
  "exam_title": "Mathematics Mid-Term",
  "student_name": "Jane Doe",
  "roll_number": "2024CS042",
  "total_marks": 50,
  "passing_marks": 25,
  "model_answers": [
    {
      "question_id": "q1",
      "question_number": 1,
      "model_answer": "Newton's second law states F = ma",
      "max_marks": 10,
      "acceptable_answers": ["Force equals mass times acceleration"]
    }
  ]
}
```

> If `model_answers` is empty, the backend will automatically extract the marking scheme from the uploaded `question_paper` / `answer_key` images using Gemini.

**Response:**

```json
{
  "success": true,
  "grading_result": {
    "student_name": "Jane Doe",
    "roll_number": "2024CS042",
    "exam_title": "Mathematics Mid-Term",
    "question_scores": {
      "q1": { "question_number": 1, "marks_obtained": 8, "max_marks": 10 }
    },
    "total_marks_obtained": 8,
    "total_marks_available": 10,
    "percentage": 80.0,
    "grade": "Passed",
    "graded_at": "2026-04-23T17:00:00+00:00"
  }
}
```

---

### Other Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/preprocess-only` | POST | Run OpenCV preprocessing only — returns quality score |
| `/api/ocr-only` | POST | Run OCR only — returns raw text and extracted Q&A pairs |
| `/api/export/csv` | POST | Export grading results as a CSV file |
| `/api/export/pdf` | POST | Export a styled PDF report |
| `/health` | GET | Server health check |

---

## 🖼️ OpenCV Preprocessing Pipeline

| Step | Method | Purpose |
|---|---|---|
| Resize | `cv2.resize` | Cap at 1500 px width for API efficiency |
| Edge Detection | `cv2.Canny` + `cv2.findContours` | Locate document boundary in the frame |
| Perspective Warp | `cv2.getPerspectiveTransform` | Straighten a photographed page |
| Deskew (fallback) | `cv2.HoughLinesP` | Correct slight rotation when no contour found |
| Grayscale | `cv2.cvtColor` | Remove colour channels |
| Denoise | `cv2.medianBlur` | Fast noise removal optimised for Gemini input |
| Contrast | `cv2.createCLAHE` | CLAHE — fix uneven lighting / shadows |
| Binarize | `cv2.adaptiveThreshold` | Gaussian adaptive thresholding |

---

## 🤖 AI Models Used

| Task | Model | Notes |
|---|---|---|
| OCR / Transcription | `gemini-2.5-flash` | Multimodal: receives PIL images + prompt, returns structured JSON |
| Grading | `gemini-2.5-flash` | Near-deterministic (temp = 0.05), JSON-only output contract |

---

## 📱 Frontend — Flutter App

### Prerequisites
- Flutter SDK `^3.11.0`
- Android Studio / Xcode (for device/emulator)

### Key packages

| Package | Purpose |
|---|---|
| `go_router` | Client-side navigation |
| `google_fonts` | Custom typography |
| `camera` | Live camera capture for scanning sheets |
| `image_picker` | Gallery / file picker fallback |
| `file_picker` | Document/PDF picking |
| `http` | REST API communication with backend |
| `web_socket_channel` | Real-time updates |

### Screens

| Screen | Description |
|---|---|
| `login_screen.dart` | User authentication |
| `register_screen.dart` | New account registration |
| `main_screen.dart` | Root navigation shell |
| `dashboard_screen.dart` | Results overview and history |
| `upload_screen.dart` | Image upload, form fill, and grading trigger |
| `camera_screen.dart` | Live camera capture |

### Running the frontend

```bash
cd app/frontend
flutter pub get
flutter run
```

> **Important:** Update the backend URL in the service layer to point to your running FastAPI instance (default: `http://10.0.2.2:8000` for Android emulator, `http://localhost:8000` for web/desktop).

---

## 🧪 Running Tests

```bash
cd app/backend
pytest tests/ -v
```

---

## 🔧 Tech Stack

| Layer | Technology |
|---|---|
| Mobile Frontend | Flutter (Dart) |
| Backend Framework | FastAPI (Python 3.12+) |
| Image Processing | OpenCV (`opencv-python-headless`), Pillow, PyMuPDF |
| AI / OCR / Grading | Google Gemini 2.5 Flash (`google-generativeai`) |
| Data Validation | Pydantic v2 |
| PDF Export | ReportLab |
| CSV Export | openpyxl |
| Logging | Loguru |
| Testing | pytest, pytest-asyncio |

---

## 📄 License

This project is for educational / mini-project purposes.
