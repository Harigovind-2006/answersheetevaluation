AutoGrade Backend
=================

Python FastAPI backend for automated answer sheet correction.

**Pipeline:**
```
Image Upload → OpenCV Preprocessing → Cloud Vision OCR → Gemini Grading → JSON Result
```

## Setup

### 1. Create virtual environment
```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure environment
```bash
copy .env.example .env        # Windows
# cp .env.example .env        # Linux/macOS
```

Edit `.env` and fill in:
- `GEMINI_API_KEY` — plain string from [Google AI Studio](https://aistudio.google.com)
- `GOOGLE_VISION_SERVICE_ACCOUNT_PATH` — path to your downloaded Cloud Vision service account JSON  
- `FIREBASE_SERVICE_ACCOUNT_PATH` — path to your Firebase service account JSON
- `FIREBASE_STORAGE_BUCKET` — your Firebase Storage bucket name

### Getting the Cloud Vision Service Account JSON
1. [GCP Console](https://console.cloud.google.com) → **IAM & Admin** → **Service Accounts**
2. Create or select a service account
3. Grant it the role **Cloud Vision API User** (`roles/cloudvision.viewer`)
4. **Keys** tab → **Add Key** → **Create new key** → **JSON** → Download
5. Rename the file to `vision_service_account.json` and place it in the `backend/` folder
6. Set `GOOGLE_VISION_SERVICE_ACCOUNT_PATH=vision_service_account.json` in `.env`

> **Tip**: If your Firebase and GCP projects are the same, one service account with both roles can serve both purposes.

### 4. Run the server
```bash
python run.py
```

Server starts at `http://localhost:8000`
Interactive docs at `http://localhost:8000/docs`

---

## API Endpoints

### `POST /api/process` — Full Pipeline
Upload one or more answer sheet images + exam metadata. Returns graded scores.

**Form fields:**
- `images` — one or more student answer sheet images (JPEG/PNG/WEBP)
- `grade_request` — JSON string (see below)
- `question_paper` (Optional) — one or more question paper images
- `answer_key` (Optional) — one or more answer key images

**grade_request JSON schema:**
```json
{
  "exam_id": "abc123",
  "exam_title": "Mathematics Mid-Term",
  "student_name": "John Smith",
  "roll_number": "2024CS001",
  "model_answers": [  // Optional if question_paper or answer_key is uploaded
    {
      "question_id": "q1",
      "question_number": 1,
      "model_answer": "Paris",
      "max_marks": 10,
      "acceptable_answers": ["Paris, France"]
    }
  ]
}
```

> **New Feature**: If `model_answers` is empty, the engine will automatically extract the marking scheme from the uploaded `question_paper` and `answer_key` using Gemini AI.

**Response:**
```json
{
  "success": true,
  "grading_result": {
    "student_name": "John Smith",
    "question_scores": {
      "q1": {"question_number": 1, "marks_obtained": 9, "max_marks": 10}
    },
    "total_marks_obtained": 9,
    "total_marks_available": 10,
    "percentage": 90.0,
    "grade": "A"
  }
}
```

### `POST /api/preprocess-only` — OpenCV only
Preview what the preprocessed image looks like + quality score.

### `POST /api/ocr-only` — OCR only
Extract raw text and Q&A pairs from images without grading.

### `POST /api/export/csv` — Export CSV
### `POST /api/export/pdf` — Export PDF (styled reportlab)

### `GET /health` — Health check

---

## OpenCV Preprocessing Steps

| Step | Method | Purpose |
|------|--------|---------|
| Resize | `cv2.resize` | Cap at 1800px for API efficiency |
| Grayscale | `cv2.cvtColor` | Remove color channels |
| Denoise | `cv2.fastNlMeansDenoising` | Non-Local Means — handles handwriting noise |
| Contrast | `cv2.createCLAHE` | CLAHE — fixes uneven lighting |
| Deskew | `cv2.HoughLinesP` | Hough line detection, rotate correction |
| Binarize | `cv2.adaptiveThreshold` | Gaussian adaptive + Otsu |
| Morph cleanup | `cv2.morphologyEx` | Remove specs, fill gaps |

---

## Running Tests

```bash
pytest tests/ -v
```

---

## Project Structure

```
backend/
├── app/
│   ├── api/
│   │   └── routes/
│   │       ├── pipeline.py   # Main /api/process endpoint
│   │       ├── export.py     # CSV/PDF export
│   │       └── health.py     # Health check
│   ├── core/
│   │   ├── config.py         # Pydantic settings
│   │   └── logging.py        # Loguru setup
│   ├── models/
│   │   └── schemas.py        # All Pydantic models
│   ├── services/
│   │   ├── image_processor.py  # OpenCV pipeline
│   │   ├── ocr_service.py      # Cloud Vision OCR
│   │   ├── grading_service.py  # Gemini grader
│   │   └── export_service.py   # CSV/PDF exporter
│   └── main.py               # FastAPI app factory
├── tests/
│   ├── test_image_processor.py
│   ├── test_grading_service.py
│   └── test_routes.py
├── uploads/
│   ├── raw/                  # Original uploaded images
│   └── processed/            # OpenCV-processed versions
├── .env.example              # Environment template
├── requirements.txt
├── pytest.ini
└── run.py
```
