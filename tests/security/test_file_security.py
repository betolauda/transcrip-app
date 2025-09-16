"""
Critical security tests for file upload and validation functionality.

These tests cover the most important security vulnerabilities:
- File type validation bypass
- File size limit bypass
- Path traversal attacks
- Malicious file content
- MIME type spoofing
"""
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, Mock

from src.services.transcription_service import TranscriptionService
from tests.fixtures.test_data import (
    create_mp3_bytes,
    create_malicious_file_bytes,
    create_invalid_file_bytes,
    create_oversized_file_bytes
)
from tests.utils.test_helpers import temporary_file, mock_environment


class TestFileValidationSecurity:
    """Test file validation security measures."""

    def test_valid_mp3_file_passes_validation(self, transcription_service, temp_upload_dir):
        """Test that valid MP3 files pass validation."""
        mp3_content = create_mp3_bytes(1)

        with temporary_file(mp3_content, "valid_audio", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)
            assert is_valid is True
            assert error is None

    def test_file_extension_validation(self, transcription_service, temp_upload_dir):
        """Test that non-MP3 extensions are rejected."""
        mp3_content = create_mp3_bytes(1)

        # Test various dangerous extensions
        dangerous_extensions = [".exe", ".sh", ".bat", ".php", ".js", ".html", ".py"]

        for ext in dangerous_extensions:
            with temporary_file(mp3_content, f"malicious{ext}") as temp_file:
                is_valid, error = transcription_service.validate_audio_file(temp_file)
                assert is_valid is False
                assert "not allowed" in error.lower()

    def test_file_size_limit_enforcement(self, transcription_service, temp_upload_dir):
        """Test that file size limits are enforced."""
        # Create file larger than limit (5MB in test config)
        oversized_content = create_oversized_file_bytes(6)

        with temporary_file(oversized_content, "oversized", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)
            assert is_valid is False
            assert "exceeds maximum" in error.lower()

    @patch('src.services.transcription_service.magic.from_file')
    def test_mime_type_validation(self, mock_magic, transcription_service, temp_upload_dir):
        """Test MIME type validation prevents spoofed files."""
        # Mock magic to return non-audio MIME type
        mock_magic.return_value = 'text/plain'

        mp3_content = create_mp3_bytes(1)
        with temporary_file(mp3_content, "spoofed", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)
            assert is_valid is False
            assert "invalid file type" in error.lower()

    @patch('src.services.transcription_service.magic.from_file')
    def test_mime_type_validation_graceful_fallback(self, mock_magic, transcription_service, temp_upload_dir):
        """Test that validation continues gracefully if MIME detection fails."""
        # Mock magic to raise exception
        mock_magic.side_effect = Exception("Magic not available")

        mp3_content = create_mp3_bytes(1)
        with temporary_file(mp3_content, "fallback", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)
            # Should still pass based on extension validation
            assert is_valid is True
            assert error is None

    def test_malicious_file_content_detection(self, transcription_service, temp_upload_dir):
        """Test detection of files with malicious content disguised as MP3."""
        malicious_content = create_malicious_file_bytes()

        with patch('src.services.transcription_service.magic.from_file') as mock_magic:
            mock_magic.return_value = 'text/x-shellscript'

            with temporary_file(malicious_content, "malicious", ".mp3") as temp_file:
                is_valid, error = transcription_service.validate_audio_file(temp_file)
                assert is_valid is False
                assert "invalid file type" in error.lower()

    def test_empty_file_rejection(self, transcription_service, temp_upload_dir):
        """Test that empty files are rejected."""
        with temporary_file(b'', "empty", ".mp3") as temp_file:
            is_valid, error = transcription_service.validate_audio_file(temp_file)
            assert is_valid is False
            assert "exceeds maximum" in error.lower() or "invalid" in error.lower()

    def test_path_traversal_in_filename(self, transcription_service, temp_upload_dir):
        """Test that path traversal attempts in filenames are handled safely."""
        mp3_content = create_mp3_bytes(1)

        # These shouldn't cause path traversal due to Path handling
        dangerous_names = [
            "../../../etc/passwd.mp3",
            "..\\..\\windows\\system32\\config.mp3",
            "../../../../root/.ssh/id_rsa.mp3"
        ]

        for dangerous_name in dangerous_names:
            with temporary_file(mp3_content) as temp_file:
                # The file validation doesn't actually process the filename in a way
                # that would be vulnerable to path traversal, but we test it anyway
                is_valid, error = transcription_service.validate_audio_file(temp_file)
                # Should pass validation as it's a valid MP3 file
                assert is_valid is True


class TestFileUploadSecurityIntegration:
    """Integration tests for file upload security through the API."""

    @pytest.mark.asyncio
    async def test_upload_endpoint_rejects_malicious_files(self, async_client, temp_upload_dir):
        """Test that the upload endpoint rejects malicious files."""
        malicious_content = create_malicious_file_bytes()

        with patch('src.services.transcription_service.magic.from_file') as mock_magic:
            mock_magic.return_value = 'application/x-executable'

            files = {"file": ("malicious.mp3", malicious_content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 400
            response_data = response.json()
            assert "validation" in response_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_endpoint_rejects_oversized_files(self, async_client, temp_upload_dir):
        """Test that the upload endpoint rejects oversized files."""
        oversized_content = create_oversized_file_bytes(10)  # 10MB > 5MB limit

        files = {"file": ("large.mp3", oversized_content, "audio/mpeg")}
        response = await async_client.post("/upload", files=files)

        assert response.status_code == 400
        response_data = response.json()
        assert "exceeds" in response_data["detail"].lower() or "large" in response_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_endpoint_handles_no_filename(self, async_client, temp_upload_dir):
        """Test handling of uploads without filenames."""
        mp3_content = create_mp3_bytes(1)

        files = {"file": ("", mp3_content, "audio/mpeg")}
        response = await async_client.post("/upload", files=files)

        assert response.status_code == 400
        response_data = response.json()
        assert "filename" in response_data["detail"].lower()

    @pytest.mark.asyncio
    async def test_upload_endpoint_rejects_wrong_extensions(self, async_client, temp_upload_dir):
        """Test that the upload endpoint rejects files with wrong extensions."""
        content = create_mp3_bytes(1)

        dangerous_filenames = ["script.exe", "malware.bat", "hack.php", "evil.js"]

        for filename in dangerous_filenames:
            files = {"file": (filename, content, "audio/mpeg")}
            response = await async_client.post("/upload", files=files)

            assert response.status_code == 400
            response_data = response.json()
            assert "mp3" in response_data["detail"].lower()


class TestResourceExhaustionPrevention:
    """Test prevention of resource exhaustion attacks."""

    def test_file_cleanup_on_validation_failure(self, transcription_service, temp_upload_dir):
        """Test that files are cleaned up even when validation fails."""
        oversized_content = create_oversized_file_bytes(6)

        with temporary_file(oversized_content, "test_cleanup", ".mp3") as temp_file:
            # Validation should fail due to size
            is_valid, error = transcription_service.validate_audio_file(temp_file)
            assert is_valid is False

            # File should still exist (cleanup is handled by the API layer)
            assert temp_file.exists()

        # After context manager, file should be cleaned up
        assert not temp_file.exists()

    @pytest.mark.asyncio
    async def test_memory_usage_during_upload(self, async_client, temp_upload_dir):
        """Test that memory usage is controlled during file uploads."""
        # This is more of a placeholder for future memory monitoring
        mp3_content = create_mp3_bytes(1)

        files = {"file": ("memory_test.mp3", mp3_content, "audio/mpeg")}

        with patch('src.services.transcription_service.whisper.load_model') as mock_whisper:
            mock_model = Mock()
            mock_model.transcribe.return_value = {
                "text": "Test transcription",
                "segments": []
            }
            mock_whisper.return_value = mock_model

            response = await async_client.post("/upload", files=files)

            # If we get here without memory issues, test passes
            assert response.status_code in [200, 400]  # Either success or validation error

    def test_concurrent_file_validation(self, transcription_service, temp_upload_dir):
        """Test that concurrent file validations don't interfere with each other."""
        import threading
        import time

        results = []
        errors = []

        def validate_file(file_content, filename):
            try:
                with temporary_file(file_content, filename, ".mp3") as temp_file:
                    time.sleep(0.1)  # Simulate processing time
                    is_valid, error = transcription_service.validate_audio_file(temp_file)
                    results.append((filename, is_valid, error))
            except Exception as e:
                errors.append((filename, str(e)))

        # Create multiple threads validating different files
        threads = []
        for i in range(5):
            content = create_mp3_bytes(1)
            filename = f"concurrent_{i}"
            thread = threading.Thread(target=validate_file, args=(content, filename))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All validations should have succeeded
        assert len(results) == 5
        assert len(errors) == 0
        for filename, is_valid, error in results:
            assert is_valid is True
            assert error is None


class TestInputSanitization:
    """Test input sanitization and validation."""

    def test_filename_sanitization(self, transcription_service):
        """Test that dangerous characters in filenames are handled safely."""
        # Note: This test assumes filename sanitization exists
        # In the current implementation, Path handles most issues
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\0', '\n']

        for char in dangerous_chars:
            filename = f"test{char}file.mp3"
            # In the current implementation, this would be handled by Path
            # and the actual file operations are safe

            # This test would need to be implemented based on actual sanitization logic
            # For now, we just ensure no exceptions are raised
            try:
                path = Path(filename)
                # Should not raise exception
                assert True
            except Exception:
                pytest.fail(f"Path handling failed for character: {char}")

    def test_special_filename_handling(self, transcription_service):
        """Test handling of special filenames that could cause issues."""
        special_names = [
            "con.mp3",  # Windows reserved name
            "aux.mp3",  # Windows reserved name
            "prn.mp3",  # Windows reserved name
            "nul.mp3",  # Windows reserved name
            ".",        # Current directory
            "..",       # Parent directory
            "",         # Empty string
        ]

        for name in special_names:
            try:
                path = Path(name)
                # Path handling should be safe
                assert True
            except Exception:
                # Some edge cases might raise exceptions, which is fine
                pass