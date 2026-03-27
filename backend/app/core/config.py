from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

from dotenv import load_dotenv
import os

load_dotenv()  # loads .env file

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
SUPABASE_STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Gemini API key (plain string from AI Studio)
    gemini_api_key: str = GEMINI_API_KEY

    # OpenAI API key (for GPT Analysis, optional)
    openai_api_key: str = ""

    # Supabase (Database, Auth, Storage)
    supabase_url: str = SUPABASE_URL
    supabase_key: str = SUPABASE_KEY
    supabase_storage_bucket: str = SUPABASE_STORAGE_BUCKET

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True
    allowed_origins: str = "*"

    # Upload limits
    max_file_size_mb: int = 20
    max_pages: int = 10

    # OpenCV toggles
    deskew_enabled: bool = True
    denoise_enabled: bool = True
    contrast_enhance_enabled: bool = True
    binarize_enabled: bool = True

    # EasyOCR Configuration
    ocr_confidence_threshold: float = 0.50
    ocr_languages: str = "en"
    ocr_use_gpu: bool = True

    @property
    def allowed_origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
