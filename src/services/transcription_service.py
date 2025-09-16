import whisper
import logging
import os
import magic
import time
from pathlib import Path
from typing import Optional, Dict, Any

from ..config.settings import settings
from ..models.domain_models import TranscriptionResult
from ..repositories.database_repository import DatabaseRepository
from .audio_processor import OptimizedAudioProcessor, AudioMetadata

logger = logging.getLogger(__name__)

class TranscriptionService:
    """Service for handling audio transcription operations"""

    def __init__(self, db_repository: DatabaseRepository = None):
        self.db_repository = db_repository or DatabaseRepository()
        self._model = None
        self.audio_processor = OptimizedAudioProcessor()
        self.enable_audio_optimization = True

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
        Transcribe audio file with optimization and save to database
        Returns: TranscriptionResult with success/error information
        """
        processing_start_time = time.time()
        processed_file_path = file_path
        audio_metadata = None
        processing_stats = {}

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

            # Audio analysis and optimization
            if self.enable_audio_optimization:
                logger.info(f"Analyzing audio quality for {filename}")

                # Analyze audio metadata
                audio_metadata = self.audio_processor.analyze_audio_file(file_path)
                processing_stats["original_quality_score"] = audio_metadata.quality_score
                processing_stats["original_duration"] = audio_metadata.duration_seconds
                processing_stats["noise_level"] = audio_metadata.noise_level

                # Get optimization recommendations
                recommendations = self.audio_processor.get_optimization_recommendations(audio_metadata)
                if recommendations:
                    logger.info(f"Audio optimization recommendations for {filename}: {recommendations}")

                # Process audio if quality is poor or file is large
                should_enhance = (
                    audio_metadata.quality_score < 0.6 or
                    audio_metadata.noise_level > 0.3 or
                    audio_metadata.duration_seconds > 300
                )

                if should_enhance:
                    logger.info(f"Optimizing audio for {filename}")

                    optimization_start = time.time()
                    processing_result = self.audio_processor.process_audio_sync(
                        file_path,
                        enhance_quality=True,
                        chunk_large_files=audio_metadata.duration_seconds > 300
                    )

                    if processing_result.success and processing_result.processed_file:
                        processed_file_path = processing_result.processed_file
                        processing_stats["optimization_time"] = time.time() - optimization_start
                        processing_stats["quality_improvements"] = processing_result.quality_improvements
                        processing_stats["chunks_processed"] = processing_result.chunks_processed
                        logger.info(f"Audio optimization completed for {filename} in {processing_stats['optimization_time']:.2f}s")
                    else:
                        logger.warning(f"Audio optimization failed for {filename}: {processing_result.error_message}")
                        # Continue with original file
                        processing_stats["optimization_failed"] = processing_result.error_message

            # Perform transcription
            logger.info(f"Starting Whisper transcription for {filename}")
            transcription_start = time.time()

            result = self.model.transcribe(
                str(processed_file_path),
                language=settings.TRANSCRIPTION_LANGUAGE,
                # Optimize Whisper parameters based on audio characteristics
                **self._get_whisper_params(audio_metadata)
            )

            transcript_text = result["text"]
            transcription_time = time.time() - transcription_start
            processing_stats["transcription_time"] = transcription_time

            # Enhanced transcription metadata
            segments = result.get("segments", [])
            processing_stats["segments_count"] = len(segments)
            processing_stats["average_confidence"] = self._calculate_average_confidence(segments)
            processing_stats["speaking_rate"] = self._calculate_speaking_rate(transcript_text, audio_metadata)

            # Save to database with enhanced metadata
            save_start = time.time()
            transcription_id = self.db_repository.save_transcription(
                filename,
                transcript_text,
                file_size=audio_metadata.file_size_bytes if audio_metadata else 0,
                duration_seconds=audio_metadata.duration_seconds if audio_metadata else 0,
                language=settings.TRANSCRIPTION_LANGUAGE
            )
            processing_stats["database_save_time"] = time.time() - save_start

            logger.info(f"Enhanced transcription saved with ID: {transcription_id}")

            # Create preview (first 200 chars)
            transcript_preview = transcript_text[:200]
            if len(transcript_text) > 200:
                transcript_preview += "..."

            # Calculate total processing time
            total_processing_time = time.time() - processing_start_time
            processing_stats["total_processing_time"] = total_processing_time

            # Clean up processed file if it's different from original
            if processed_file_path != file_path:
                try:
                    processed_file_path.unlink()
                except Exception as e:
                    logger.warning(f"Failed to clean up processed file {processed_file_path}: {e}")

            # Log performance metrics
            logger.info(f"Transcription completed for {filename}: "
                       f"Total time: {total_processing_time:.2f}s, "
                       f"Quality score: {processing_stats.get('original_quality_score', 'N/A')}, "
                       f"Confidence: {processing_stats.get('average_confidence', 'N/A')}")

            return TranscriptionResult(
                filename=filename,
                transcript_preview=transcript_preview,
                full_transcript=transcript_text,
                message="File processed and saved successfully with optimizations",
                success=True,
                processing_stats=processing_stats
            )

        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            logger.error(f"Transcription error for {filename}: {e}")

            # Clean up processed file on error
            if processed_file_path != file_path and processed_file_path.exists():
                try:
                    processed_file_path.unlink()
                except Exception:
                    pass

            return TranscriptionResult(
                filename=filename,
                transcript_preview="",
                full_transcript="",
                message="Transcription failed",
                success=False,
                error=error_msg,
                processing_stats=processing_stats
            )

    def _get_whisper_params(self, metadata: Optional[AudioMetadata]) -> Dict[str, Any]:
        """Get optimized Whisper parameters based on audio characteristics."""
        params = {}

        if metadata:
            # Adjust parameters based on audio quality
            if metadata.quality_score < 0.4:
                # For poor quality audio, use more conservative settings
                params.update({
                    "temperature": 0.0,  # More deterministic
                    "compression_ratio_threshold": 2.4,  # More strict
                    "logprob_threshold": -1.0,  # More strict
                    "no_speech_threshold": 0.6  # Higher threshold
                })
            elif metadata.quality_score > 0.8:
                # For high quality audio, can use faster settings
                params.update({
                    "temperature": 0.2,  # Allow some randomness
                    "compression_ratio_threshold": 2.6,
                    "logprob_threshold": -0.8,
                    "no_speech_threshold": 0.4
                })

            # Adjust for noise level
            if metadata.noise_level > 0.5:
                params["temperature"] = 0.0  # More deterministic for noisy audio

            # Adjust for duration
            if metadata.duration_seconds > 600:  # 10 minutes
                params["verbose"] = False  # Reduce logging for long files

        return params

    def _calculate_average_confidence(self, segments: list) -> float:
        """Calculate average confidence from Whisper segments."""
        if not segments:
            return 0.0

        confidences = []
        for segment in segments:
            # Whisper doesn't directly provide confidence, but we can estimate
            # from the log probability and other features
            if "avg_logprob" in segment:
                # Convert log probability to approximate confidence
                confidence = max(0.0, min(1.0, (segment["avg_logprob"] + 1.0)))
                confidences.append(confidence)

        return sum(confidences) / len(confidences) if confidences else 0.0

    def _calculate_speaking_rate(self, transcript: str, metadata: Optional[AudioMetadata]) -> float:
        """Calculate speaking rate (words per minute)."""
        if not metadata or metadata.duration_seconds == 0:
            return 0.0

        word_count = len(transcript.split())
        duration_minutes = metadata.duration_seconds / 60
        return word_count / duration_minutes if duration_minutes > 0 else 0.0

    def cleanup_file(self, file_path: Path) -> None:
        """Clean up uploaded file after processing"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.error(f"Failed to cleanup file {file_path}: {e}")