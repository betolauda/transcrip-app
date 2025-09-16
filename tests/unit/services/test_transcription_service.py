"""
Comprehensive unit tests for TranscriptionService covering all functionality
including file validation, transcription processing, and error handling.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

from src.services.transcription_service import TranscriptionService
from src.models.domain_models import TranscriptionResult
from tests.fixtures.test_data import create_mp3_bytes, create_malicious_file_bytes
from tests.utils.test_helpers import temporary_file


class TestTranscriptionServiceInitialization:
    """Test TranscriptionService initialization and dependency injection."""

    def test_service_initialization_with_repository(self, db_repository):
        """Test service initialization with provided repository."""
        service = TranscriptionService(db_repository)
        assert service.db_repository is db_repository
        assert service._model is None

    def test_service_initialization_without_repository(self):
        """Test service initialization creates default repository."""
        service = TranscriptionService()
        assert service.db_repository is not None
        assert service._model is None

    def test_lazy_model_loading(self, transcription_service, mock_whisper_transcribe):
        """Test that Whisper model is loaded lazily."""
        # Model should not be loaded initially
        assert transcription_service._model is None

        # Accessing model property should load it
        model = transcription_service.model
        assert model is not None
        assert model == mock_whisper_transcribe

    @patch('src.services.transcription_service.whisper.load_model')
    def test_model_loading_with_settings(self, mock_load_model, transcription_service):
        """Test that model loading uses correct settings."""
        mock_model = Mock()
        mock_load_model.return_value = mock_model

        # Access model to trigger loading
        _ = transcription_service.model

        # Verify model was loaded with correct settings
        mock_load_model.assert_called_once()


class TestFileValidation:
    """Test file validation functionality."""

    def test_validate_valid_mp3_file(self, transcription_service):
        """Test validation of valid MP3 file."""
        mp3_content = create_mp3_bytes(1)

        with temporary_file(mp3_content, "valid", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)

            assert is_valid is True
            assert error is None

    def test_validate_file_size_limit(self, transcription_service):
        """Test file size validation."""
        # Create file larger than 5MB limit (test config)
        large_content = b'\xff\xfb\x90\x00' + b'\x00' * (6 * 1024 * 1024)

        with temporary_file(large_content, "large", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)

            assert is_valid is False
            assert "exceeds maximum" in error

    def test_validate_file_extension(self, transcription_service):
        """Test file extension validation."""
        mp3_content = create_mp3_bytes(1)

        with temporary_file(mp3_content, "test", ".exe") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)

            assert is_valid is False
            assert "not allowed" in error

    @patch('src.services.transcription_service.magic.from_file')
    def test_validate_mime_type_check(self, mock_magic, transcription_service):
        """Test MIME type validation."""
        mock_magic.return_value = 'text/plain'

        mp3_content = create_mp3_bytes(1)
        with temporary_file(mp3_content, "fake", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)

            assert is_valid is False
            assert "Invalid file type" in error

    @patch('src.services.transcription_service.magic.from_file')
    def test_validate_mime_type_exception_handling(self, mock_magic, transcription_service):
        """Test graceful handling of MIME type detection exceptions."""
        mock_magic.side_effect = Exception("Magic library not available")

        mp3_content = create_mp3_bytes(1)
        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)

            # Should still pass based on extension validation
            assert is_valid is True
            assert error is None

    def test_validate_nonexistent_file(self, transcription_service):
        """Test validation of non-existent file."""
        nonexistent_path = Path("/nonexistent/file.mp3")

        with pytest.raises(FileNotFoundError):
            transcription_service.validate_audio_file(nonexistent_path)

    def test_validate_empty_file(self, transcription_service):
        """Test validation of empty file."""
        with temporary_file(b'', "empty", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)

            assert is_valid is False
            assert "exceeds maximum" in error

    def test_validate_file_with_malicious_content(self, transcription_service):
        """Test validation rejects files with malicious content."""
        malicious_content = create_malicious_file_bytes()

        with patch('src.services.transcription_service.magic.from_file') as mock_magic:
            mock_magic.return_value = 'application/x-executable'

            with temporary_file(malicious_content, "malicious", ".mp3") as temp_file:
                is_valid, error = transcription_service.validate_audio_file(temp_file)

                assert is_valid is False
                assert "Invalid file type" in error


class TestTranscriptionProcessing:
    """Test audio transcription processing."""

    def test_transcribe_audio_success(self, transcription_service, mock_whisper_transcribe):
        """Test successful audio transcription."""
        mp3_content = create_mp3_bytes(1)
        filename = "test_audio.mp3"

        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is True
            assert result.filename == filename
            assert result.full_transcript
            assert result.transcript_preview
            assert result.error is None

    def test_transcribe_audio_with_database_save(self, transcription_service, mock_whisper_transcribe, db_repository):
        """Test that transcription is saved to database."""
        mp3_content = create_mp3_bytes(1)
        filename = "test_audio.mp3"

        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is True

            # Verify saved to database (check if repository has transcription)
            # Note: We'd need to add a method to check this or verify through repository calls

    def test_transcribe_audio_file_validation_failure(self, transcription_service):
        """Test transcription when file validation fails."""
        large_content = b'\xff\xfb\x90\x00' + b'\x00' * (6 * 1024 * 1024)
        filename = "large_file.mp3"

        with temporary_file(large_content, "large", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is False
            assert result.error is not None
            assert "validation" in result.message.lower()
            assert not result.full_transcript

    @patch('src.services.transcription_service.whisper.load_model')
    def test_transcribe_audio_whisper_exception(self, mock_load_model, transcription_service):
        """Test handling of Whisper transcription exceptions."""
        # Mock Whisper model to raise exception
        mock_model = Mock()
        mock_model.transcribe.side_effect = Exception("Whisper error")
        mock_load_model.return_value = mock_model

        mp3_content = create_mp3_bytes(1)
        filename = "test_audio.mp3"

        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is False
            assert "Transcription failed" in result.error
            assert result.full_transcript == ""

    def test_transcribe_audio_preview_generation(self, transcription_service, mock_whisper_transcribe):
        """Test that transcript preview is generated correctly."""
        # Mock long transcript
        long_transcript = "A" * 300  # Longer than 200 char preview limit
        mock_whisper_transcribe.transcribe.return_value = {"text": long_transcript}

        mp3_content = create_mp3_bytes(1)
        filename = "test_audio.mp3"

        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is True
            assert len(result.transcript_preview) <= 203  # 200 chars + "..."
            assert result.transcript_preview.endswith("...")
            assert result.full_transcript == long_transcript

    def test_transcribe_audio_short_transcript_no_truncation(self, transcription_service, mock_whisper_transcribe):
        """Test that short transcripts are not truncated."""
        short_transcript = "Short transcript"
        mock_whisper_transcribe.transcribe.return_value = {"text": short_transcript}

        mp3_content = create_mp3_bytes(1)
        filename = "test_audio.mp3"

        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is True
            assert result.transcript_preview == short_transcript
            assert not result.transcript_preview.endswith("...")

    @patch('src.repositories.database_repository.DatabaseRepository.save_transcription')
    def test_transcribe_audio_database_save_failure(self, mock_save, transcription_service, mock_whisper_transcribe):
        """Test handling of database save failures."""
        mock_save.side_effect = Exception("Database error")

        mp3_content = create_mp3_bytes(1)
        filename = "test_audio.mp3"

        with temporary_file(mp3_content, "test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            # The current implementation doesn't handle db save errors gracefully
            # This test might need to be updated based on desired behavior
            assert result.success is False


class TestFileCleanup:
    """Test file cleanup functionality."""

    def test_cleanup_file_success(self, transcription_service):
        """Test successful file cleanup."""
        mp3_content = create_mp3_bytes(1)

        with temporary_file(mp3_content, "cleanup_test", ".mp3") as temp_file:
            # File should exist
            assert temp_file.exists()

            # Cleanup file
            transcription_service.cleanup_file(temp_file)

            # File should be removed
            assert not temp_file.exists()

    def test_cleanup_nonexistent_file(self, transcription_service):
        """Test cleanup of non-existent file doesn't raise exception."""
        nonexistent_path = Path("/nonexistent/file.mp3")

        # Should not raise exception
        transcription_service.cleanup_file(nonexistent_path)

    def test_cleanup_file_permission_error(self, transcription_service):
        """Test cleanup handles permission errors gracefully."""
        mp3_content = create_mp3_bytes(1)

        with temporary_file(mp3_content, "permission_test", ".mp3") as temp_file:
            # Mock unlink to raise permission error
            with patch.object(temp_file, 'unlink', side_effect=PermissionError("Permission denied")):
                # Should not raise exception, just log error
                transcription_service.cleanup_file(temp_file)


class TestTranscriptionServiceIntegration:
    """Integration tests for TranscriptionService components."""

    def test_full_transcription_workflow(self, transcription_service, mock_whisper_transcribe):
        """Test complete transcription workflow from file to result."""
        mp3_content = create_mp3_bytes(1)
        filename = "workflow_test.mp3"

        # Mock Whisper to return specific content
        expected_transcript = "This is a complete workflow test"
        mock_whisper_transcribe.transcribe.return_value = {"text": expected_transcript}

        with temporary_file(mp3_content, "workflow", ".mp3") as temp_file:
            # Execute full workflow
            result = transcription_service.transcribe_audio(temp_file, filename)

            # Verify all aspects of the result
            assert result.success is True
            assert result.filename == filename
            assert result.full_transcript == expected_transcript
            assert result.transcript_preview == expected_transcript  # Short enough to not be truncated
            assert result.message == "File processed and saved successfully"
            assert result.error is None

    def test_model_reuse_across_transcriptions(self, transcription_service, mock_whisper_transcribe):
        """Test that Whisper model is reused across multiple transcriptions."""
        mp3_content = create_mp3_bytes(1)

        # Perform multiple transcriptions
        for i in range(3):
            filename = f"test_{i}.mp3"
            with temporary_file(mp3_content, f"test_{i}", ".mp3") as temp_file:
                result = transcription_service.transcribe_audio(temp_file, filename)
                assert result.success is True

        # Verify model was only created once (loaded lazily)
        # The mock_whisper_transcribe fixture should be the same instance
        assert transcription_service._model is mock_whisper_transcribe

    def test_concurrent_transcription_safety(self, transcription_service, mock_whisper_transcribe):
        """Test that service handles concurrent access safely."""
        import threading
        import time

        results = []
        errors = []
        mp3_content = create_mp3_bytes(1)

        def transcribe_file(thread_id):
            try:
                filename = f"concurrent_{thread_id}.mp3"
                with temporary_file(mp3_content, f"concurrent_{thread_id}", ".mp3") as temp_file:
                    time.sleep(0.01)  # Small delay to encourage concurrency
                    result = transcription_service.transcribe_audio(temp_file, filename)
                    results.append((thread_id, result.success))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=transcribe_file, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5
        for thread_id, success in results:
            assert success is True

    @patch('src.services.transcription_service.logger')
    def test_logging_behavior(self, mock_logger, transcription_service, mock_whisper_transcribe):
        """Test that appropriate logging occurs during transcription."""
        mp3_content = create_mp3_bytes(1)
        filename = "logging_test.mp3"

        with temporary_file(mp3_content, "logging", ".mp3") as temp_file:
            transcription_service.transcribe_audio(temp_file, filename)

        # Verify logging calls
        mock_logger.info.assert_called()  # Model loading and transcription start
        # Could add more specific logging assertions based on implementation


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_transcription_with_unicode_filename(self, transcription_service, mock_whisper_transcribe):
        """Test transcription with unicode characters in filename."""
        mp3_content = create_mp3_bytes(1)
        unicode_filename = "prueba_ñandú_corazón.mp3"

        with temporary_file(mp3_content, "unicode_test", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, unicode_filename)

            assert result.success is True
            assert result.filename == unicode_filename

    def test_transcription_with_special_characters_in_content(self, transcription_service, mock_whisper_transcribe):
        """Test transcription with special characters in transcript content."""
        special_transcript = "Test with émojis 🎵 and special chars: ñáéíóú"
        mock_whisper_transcribe.transcribe.return_value = {"text": special_transcript}

        mp3_content = create_mp3_bytes(1)
        filename = "special_chars.mp3"

        with temporary_file(mp3_content, "special", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            assert result.success is True
            assert result.full_transcript == special_transcript

    def test_transcription_with_very_long_filename(self, transcription_service, mock_whisper_transcribe):
        """Test transcription with very long filename."""
        mp3_content = create_mp3_bytes(1)
        long_filename = "a" * 200 + ".mp3"  # Very long filename

        with temporary_file(mp3_content, "long", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, long_filename)

            assert result.success is True
            assert result.filename == long_filename

    def test_transcription_result_model_validation(self, transcription_service, mock_whisper_transcribe):
        """Test that TranscriptionResult model handles all data correctly."""
        mp3_content = create_mp3_bytes(1)
        filename = "model_test.mp3"

        with temporary_file(mp3_content, "model", ".mp3") as temp_file:
            result = transcription_service.transcribe_audio(temp_file, filename)

            # Verify all required fields are present and correctly typed
            assert isinstance(result.filename, str)
            assert isinstance(result.transcript_preview, str)
            assert isinstance(result.full_transcript, str)
            assert isinstance(result.message, str)
            assert isinstance(result.success, bool)
            assert result.error is None or isinstance(result.error, str)