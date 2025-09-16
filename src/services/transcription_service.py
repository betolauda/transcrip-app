import whisper
import logging
import os
import magic
from pathlib import Path
from typing import Optional

from ..config.settings import settings
from ..models.domain_models import TranscriptionResult
from ..repositories.database_repository import DatabaseRepository

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Service for handling audio transcription operations"""

    def __init__(self, db_repository: DatabaseRepository = None):
        self.db_repository = db_repository or DatabaseRepository()
        self._model = None

    @property
    def model(self):
        """Lazy loading of Whisper model"""
        if self._model is None:
            logger.info(f"Loading Whisper model: {settings.WHISPER_MODEL}")
            self._model = whisper.load_model(settings.WHISPER_MODEL)
        return self._model

    def validate_audio_file(self, file_path: Path) -> tuple[bool, Optional[str]]:
        """
        Validate uploaded audio file for security and format compliance
        Returns: (is_valid, error_message)
        """
        try:
            # Check file size
            file_size = os.path.getsize(file_path)
            if file_size > settings.MAX_FILE_SIZE:
                return False, f"File size ({file_size} bytes) exceeds maximum allowed ({settings.MAX_FILE_SIZE} bytes)"

            # Check file extension
            if file_path.suffix.lower() not in settings.ALLOWED_EXTENSIONS:
                return False, f"File extension {file_path.suffix} not allowed. Allowed: {settings.ALLOWED_EXTENSIONS}"

            # Check MIME type using python-magic for security
            try:
                mime_type = magic.from_file(str(file_path), mime=True)
                if not mime_type.startswith('audio/'):
                    return False, f"Invalid file type: {mime_type}. Expected audio file."
            except Exception as e:
                logger.warning(f"Could not determine MIME type for {file_path}: {e}")
                # Continue without MIME check if python-magic is not available

            return True, None

        except Exception as e:
            logger.error(f"File validation error for {file_path}: {e}")
            return False, f"File validation failed: {str(e)}"

    def transcribe_audio(self, file_path: Path, filename: str) -> TranscriptionResult:
        """
        Transcribe audio file and save to database
        Returns: TranscriptionResult with success/error information
        """
        try:
            # Validate file first
            is_valid, error_message = self.validate_audio_file(file_path)
            if not is_valid:
                return TranscriptionResult(
                    filename=filename,
                    transcript_preview="",
                    full_transcript="",
                    message="File validation failed",
                    success=False,
                    error=error_message
                )

            # Perform transcription
            logger.info(f"Starting transcription for {filename}")
            result = self.model.transcribe(
                str(file_path),
                language=settings.TRANSCRIPTION_LANGUAGE
            )
            transcript_text = result["text"]

            # Save to database
            transcription_id = self.db_repository.save_transcription(filename, transcript_text)
            logger.info(f"Transcription saved with ID: {transcription_id}")

            # Create preview (first 200 chars)
            transcript_preview = transcript_text[:200]
            if len(transcript_text) > 200:
                transcript_preview += "..."

            return TranscriptionResult(
                filename=filename,
                transcript_preview=transcript_preview,
                full_transcript=transcript_text,
                message="File processed and saved successfully",
                success=True
            )

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(f"Transcription error for {filename}: {e}")
            return TranscriptionResult(
                filename=filename,
                transcript_preview="",
                full_transcript="",
                message="Transcription failed",
                success=False,
                error=error_msg
            )

    def cleanup_file(self, file_path: Path) -> None:
        """Clean up uploaded file after processing"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")