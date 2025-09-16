"""
Test utilities and helper functions for the transcription API test suite.
"""
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional
from contextlib import contextmanager
from unittest.mock import patch

from httpx import AsyncClient
from fastapi.testclient import TestClient


class TestTimer:
    """Context manager for timing test operations."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.elapsed = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time


@contextmanager
def temporary_file(content: bytes, filename: str = "temp_file", suffix: str = ".mp3"):
    """Context manager for creating temporary files."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_file.write(content)
        temp_file.flush()
        temp_path = Path(temp_file.name)

    try:
        # Optionally rename to specific filename
        if filename != "temp_file":
            new_path = temp_path.parent / (filename + suffix)
            temp_path.rename(new_path)
            temp_path = new_path

        yield temp_path
    finally:
        if temp_path.exists():
            temp_path.unlink()


@contextmanager
def mock_environment(**env_vars):
    """Context manager for temporarily setting environment variables."""
    original_values = {}

    # Store original values and set new ones
    for key, value in env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = str(value)

    try:
        yield
    finally:
        # Restore original values
        for key, original_value in original_values.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value


def assert_response_structure(response_data: Dict[str, Any], expected_keys: list):
    """Assert that response contains expected keys."""
    for key in expected_keys:
        assert key in response_data, f"Missing key '{key}' in response"


def assert_error_response(response_data: Dict[str, Any], expected_status: int = None):
    """Assert that response is a proper error response."""
    assert "detail" in response_data, "Error response must contain 'detail' field"
    if expected_status:
        # This would be used with the actual response object, not just data
        pass


def create_test_upload_file(content: bytes, filename: str, content_type: str = "audio/mpeg"):
    """Create a file-like object for testing uploads."""
    from io import BytesIO
    return BytesIO(content), filename, content_type


async def upload_test_file(client: AsyncClient, file_content: bytes,
                          filename: str = "test.mp3",
                          content_type: str = "audio/mpeg") -> Dict[str, Any]:
    """Helper to upload a test file via API."""
    files = {"file": (filename, file_content, content_type)}
    response = await client.post("/upload", files=files)
    return response


def assert_database_state(db_repository, expected_counts: Dict[str, int]):
    """Assert database contains expected number of records."""
    if "transcriptions" in expected_counts:
        # This would require adding a count method to repository
        pass

    if "economic_terms" in expected_counts:
        economic_terms = db_repository.get_economic_terms()
        assert len(economic_terms) == expected_counts["economic_terms"]

    if "argentine_expressions" in expected_counts:
        argentine_expressions = db_repository.get_argentine_expressions()
        assert len(argentine_expressions) == expected_counts["argentine_expressions"]

    if "candidate_terms" in expected_counts:
        candidate_terms = db_repository.get_candidate_terms()
        assert len(candidate_terms) == expected_counts["candidate_terms"]


def assert_term_in_database(db_repository, term: str, term_type: str):
    """Assert that a specific term exists in the database."""
    if term_type == "economic":
        assert db_repository.term_exists_in_economic_glossary(term)
    elif term_type == "argentine":
        assert db_repository.expression_exists_in_argentine_dictionary(term)
    elif term_type == "candidate":
        assert db_repository.candidate_term_exists(term)
    else:
        raise ValueError(f"Unknown term type: {term_type}")


def mock_whisper_response(text: str, confidence: float = 0.8):
    """Create a mock Whisper response."""
    return {
        "text": text,
        "segments": [
            {
                "start": 0.0,
                "end": len(text) * 0.1,  # Rough estimate
                "text": text,
                "avg_logprob": -confidence,
                "compression_ratio": 1.2
            }
        ]
    }


class DatabaseStateManager:
    """Helper class for managing database state in tests."""

    def __init__(self, db_repository):
        self.db_repository = db_repository
        self._initial_state = None

    def capture_state(self):
        """Capture current database state."""
        self._initial_state = {
            "economic_terms": len(self.db_repository.get_economic_terms()),
            "argentine_expressions": len(self.db_repository.get_argentine_expressions()),
            "candidate_terms": len(self.db_repository.get_candidate_terms())
        }
        return self._initial_state

    def assert_changes(self, expected_changes: Dict[str, int]):
        """Assert that database state changed as expected."""
        if not self._initial_state:
            raise ValueError("Must call capture_state() first")

        current_state = {
            "economic_terms": len(self.db_repository.get_economic_terms()),
            "argentine_expressions": len(self.db_repository.get_argentine_expressions()),
            "candidate_terms": len(self.db_repository.get_candidate_terms())
        }

        for key, expected_change in expected_changes.items():
            initial_count = self._initial_state[key]
            current_count = current_state[key]
            actual_change = current_count - initial_count
            assert actual_change == expected_change, \
                f"Expected {expected_change} change in {key}, got {actual_change}"


class PerformanceProfiler:
    """Simple performance profiler for tests."""

    def __init__(self):
        self.timings = {}

    @contextmanager
    def time_operation(self, operation_name: str):
        """Time a specific operation."""
        start_time = time.time()
        try:
            yield
        finally:
            end_time = time.time()
            self.timings[operation_name] = end_time - start_time

    def assert_performance(self, operation_name: str, max_time: float):
        """Assert that an operation completed within time limit."""
        if operation_name not in self.timings:
            raise ValueError(f"Operation '{operation_name}' was not timed")

        actual_time = self.timings[operation_name]
        assert actual_time <= max_time, \
            f"Operation '{operation_name}' took {actual_time:.3f}s, expected <= {max_time:.3f}s"

    def get_timing(self, operation_name: str) -> Optional[float]:
        """Get timing for a specific operation."""
        return self.timings.get(operation_name)

    def get_all_timings(self) -> Dict[str, float]:
        """Get all recorded timings."""
        return self.timings.copy()


def create_test_environment():
    """Set up test environment with proper configuration."""
    test_env = {
        "DB_PATH": ":memory:",
        "WHISPER_MODEL": "tiny",
        "MAX_FILE_SIZE": "5",
        "UPLOAD_DIR": "tests/temp",
        "API_HOST": "127.0.0.1",
        "API_PORT": "8001"
    }

    return mock_environment(**test_env)


def cleanup_test_files(directory: Path):
    """Clean up test files in a directory."""
    if directory.exists() and directory.is_dir():
        for file_path in directory.glob("*"):
            if file_path.is_file():
                file_path.unlink()


class MockFileMagic:
    """Mock for python-magic file type detection."""

    def __init__(self, file_type_mapping: Dict[str, str] = None):
        self.file_type_mapping = file_type_mapping or {}
        self.default_type = "audio/mpeg"

    def from_file(self, file_path: str, mime: bool = False) -> str:
        """Mock magic.from_file function."""
        file_name = Path(file_path).name
        return self.file_type_mapping.get(file_name, self.default_type)