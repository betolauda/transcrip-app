import os
import secrets
from pathlib import Path
from typing import List

class Settings:
    """Application configuration settings"""

    # Database settings
    DB_PATH: str = os.getenv("DB_PATH", "data/transcriptions.db")

    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", secrets.token_urlsafe(32))
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))

    # File upload settings
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "uploads"))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB default
    MAX_FILE_SIZE_MB: int = int(os.getenv("MAX_FILE_SIZE", "50"))  # For validation messages
    ALLOWED_EXTENSIONS: List[str] = [".mp3"]

    # Whisper model settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    TRANSCRIPTION_LANGUAGE: str = os.getenv("TRANSCRIPTION_LANGUAGE", "es")

    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    API_VERSION: str = "v1"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:8501",  # Streamlit default
        "http://localhost:3000",  # React default
        "http://127.0.0.1:8501",
        "http://127.0.0.1:3000"
    ]

    # Rate limiting settings
    RATE_LIMIT_GENERAL: int = int(os.getenv("RATE_LIMIT_GENERAL", "100"))  # requests per hour
    RATE_LIMIT_UPLOAD: int = int(os.getenv("RATE_LIMIT_UPLOAD", "10"))   # uploads per hour
    RATE_LIMIT_AUTH: int = int(os.getenv("RATE_LIMIT_AUTH", "5"))        # auth attempts per 5 minutes
    RATE_LIMIT_IP: int = int(os.getenv("RATE_LIMIT_IP", "1000"))         # requests per hour per IP

    # Request validation settings
    MAX_REQUEST_SIZE: int = int(os.getenv("MAX_REQUEST_SIZE", "52428800"))  # 50MB in bytes
    MAX_JSON_SIZE: int = int(os.getenv("MAX_JSON_SIZE", "1048576"))         # 1MB in bytes
    MAX_FILENAME_LENGTH: int = int(os.getenv("MAX_FILENAME_LENGTH", "255"))
    ENABLE_SECURITY_HEADERS: bool = os.getenv("ENABLE_SECURITY_HEADERS", "true").lower() == "true"

    # Middleware settings
    ENABLE_RATE_LIMITING: bool = os.getenv("ENABLE_RATE_LIMITING", "true").lower() == "true"
    ENABLE_REQUEST_VALIDATION: bool = os.getenv("ENABLE_REQUEST_VALIDATION", "true").lower() == "true"
    ENABLE_SECURITY_SCANNING: bool = os.getenv("ENABLE_SECURITY_SCANNING", "true").lower() == "true"

    # IP blocking settings
    AUTO_BLOCK_SUSPICIOUS_IPS: bool = os.getenv("AUTO_BLOCK_SUSPICIOUS_IPS", "true").lower() == "true"
    SUSPICIOUS_IP_THRESHOLD: int = int(os.getenv("SUSPICIOUS_IP_THRESHOLD", "50"))  # requests before blocking
    IP_BLOCK_DURATION: int = int(os.getenv("IP_BLOCK_DURATION", "3600"))           # seconds (1 hour)

    # Economic terms (hardcoded for now, could be moved to database)
    ECONOMIC_TERMS: List[str] = [
        "inflación", "pobreza", "desempleo", "reservas", "dólar", "peso",
        "PIB", "déficit", "superávit", "tarifas", "subsidios", "impuestos"
    ]

    # Argentine expressions (hardcoded for now, could be moved to database)
    ARGENTINE_EXPRESSIONS: List[str] = [
        "laburo", "guita", "quilombo", "bondi", "mango", "fiaca",
        "che", "posta", "macana", "changas"
    ]

    # Spanish stopwords
    SPANISH_STOPWORDS: set = {
        "el","la","los","las","de","del","y","o","que","en","es","un","una","por",
        "con","al","se","lo","su","para","a","como","más","menos","ya","pero","sin",
        "sobre","esto","esta","ese","esa","esas","estos","esas","sí","no"
    }

    def __init__(self):
        # Ensure directories exist
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        Path(self.DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# Global settings instance
settings = Settings()