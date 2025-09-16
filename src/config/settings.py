import os
from pathlib import Path
from typing import List

class Settings:
    """Application configuration settings"""

    # Database settings
    DB_PATH: str = os.getenv("DB_PATH", "data/transcriptions.db")

    # File upload settings
    UPLOAD_DIR: Path = Path(os.getenv("UPLOAD_DIR", "uploads"))
    MAX_FILE_SIZE: int = int(os.getenv("MAX_FILE_SIZE", "50")) * 1024 * 1024  # 50MB default
    ALLOWED_EXTENSIONS: List[str] = [".mp3"]

    # Whisper model settings
    WHISPER_MODEL: str = os.getenv("WHISPER_MODEL", "base")
    TRANSCRIPTION_LANGUAGE: str = os.getenv("TRANSCRIPTION_LANGUAGE", "es")

    # API settings
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))

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