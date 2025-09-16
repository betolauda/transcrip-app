"""
Shared test fixtures and configuration for the transcription API test suite.
"""
import os
import tempfile
import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch
from httpx import AsyncClient
from fastapi.testclient import TestClient

# Set test environment variables before importing application code
os.environ.update({
    "DB_PATH": ":memory:",
    "WHISPER_MODEL": "tiny",
    "MAX_FILE_SIZE": "5",
    "UPLOAD_DIR": "tests/temp",
    "API_HOST": "127.0.0.1",
    "API_PORT": "8001"
})

from main import app
from src.config.settings import settings
from src.repositories.database_repository import DatabaseRepository
from src.services.transcription_service import TranscriptionService
from src.services.glossary_service import GlossaryService
from src.services.term_detection_service import TermDetectionService

# ============================================================================
# Pytest Configuration
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def db_repository():
    """Create a fresh database repository with in-memory database for each test."""
    repo = DatabaseRepository(":memory:")
    return repo


@pytest.fixture
def populated_db_repository():
    """Database repository with sample test data."""
    repo = DatabaseRepository(":memory:")

    # Add sample economic terms
    repo.add_economic_term("inflación", "economic")
    repo.add_economic_term("PIB", "economic")

    # Add sample Argentine expressions
    repo.add_argentine_expression("laburo")
    repo.add_argentine_expression("guita")

    # Add sample candidate terms
    repo.add_candidate_term("blockchain", "el nuevo blockchain económico será revolucionario")
    repo.add_candidate_term("fintech", "las empresas fintech están creciendo rápidamente")

    # Add sample transcription
    repo.save_transcription("test_audio.mp3", "Hoy hablamos de inflación y laburo en Argentina")

    return repo


# ============================================================================
# Service Fixtures
# ============================================================================

@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model to avoid loading actual model in tests."""
    mock_model = Mock()
    mock_model.transcribe.return_value = {
        "text": "This is a test transcription with inflación and laburo mentioned.",
        "segments": [
            {
                "start": 0.0,
                "end": 5.0,
                "text": "This is a test transcription",
                "avg_logprob": -0.5,
                "compression_ratio": 1.2
            }
        ]
    }
    return mock_model


@pytest.fixture
def transcription_service(db_repository, mock_whisper_model):
    """Transcription service with mocked Whisper model."""
    service = TranscriptionService(db_repository)
    service._model = mock_whisper_model
    return service


@pytest.fixture
def glossary_service(db_repository):
    """Glossary service with test database."""
    return GlossaryService(db_repository)


@pytest.fixture
def term_detection_service(db_repository):
    """Term detection service with test database."""
    return TermDetectionService(db_repository)


# ============================================================================
# File and Upload Fixtures
# ============================================================================

@pytest.fixture
def temp_upload_dir():
    """Create temporary directory for file uploads during tests."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        # Update settings to use temp directory
        original_upload_dir = settings.UPLOAD_DIR
        settings.UPLOAD_DIR = temp_path
        yield temp_path
        settings.UPLOAD_DIR = original_upload_dir


@pytest.fixture
def sample_mp3_file():
    """Create a minimal MP3 file for testing."""
    # MP3 header bytes for a minimal valid MP3 file
    mp3_header = b'\xff\xfb\x90\x00' + b'\x00' * 100
    return ("test_audio.mp3", mp3_header, "audio/mpeg")


@pytest.fixture
def malicious_file():
    """Create a malicious file that appears to be MP3 but isn't."""
    malicious_content = b'#!/bin/bash\necho "malicious script"\n' + b'\x00' * 100
    return ("malicious.mp3", malicious_content, "text/plain")


@pytest.fixture
def oversized_file():
    """Create a file that exceeds size limits."""
    # Create file larger than MAX_FILE_SIZE (5MB in tests)
    large_content = b'\xff\xfb\x90\x00' + b'\x00' * (6 * 1024 * 1024)
    return ("large_file.mp3", large_content, "audio/mpeg")


# ============================================================================
# API Client Fixtures
# ============================================================================

@pytest.fixture
def test_client():
    """Synchronous test client for FastAPI application."""
    return TestClient(app)


@pytest.fixture
async def async_client():
    """Asynchronous test client for FastAPI application."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


# ============================================================================
# Mock Fixtures
# ============================================================================

@pytest.fixture
def mock_whisper_transcribe():
    """Mock the whisper.load_model function to avoid loading actual models."""
    with patch('src.services.transcription_service.whisper.load_model') as mock_load:
        mock_model = Mock()
        mock_model.transcribe.return_value = {
            "text": "Test transcription with economic terms like inflación and Argentine expressions like laburo.",
            "segments": [
                {
                    "start": 0.0,
                    "end": 10.0,
                    "text": "Test transcription with economic terms like inflación and Argentine expressions like laburo.",
                    "avg_logprob": -0.3,
                    "compression_ratio": 1.1
                }
            ]
        }
        mock_load.return_value = mock_model
        yield mock_model


@pytest.fixture
def mock_magic_from_file():
    """Mock python-magic file type detection."""
    with patch('src.services.transcription_service.magic.from_file') as mock_magic:
        mock_magic.return_value = 'audio/mpeg'
        yield mock_magic


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def sample_transcript_text():
    """Sample transcript text with various terms for testing."""
    return (
        "Hoy hablamos sobre la inflación en Argentina que ha subido mucho. "
        "El PIB ha caído y las reservas están bajas. "
        "La gente está preocupada por el laburo y la guita que necesita para vivir. "
        "Es un quilombo la situación económica actual. "
        "Blockchain y fintech son tecnologías emergentes interesantes."
    )


@pytest.fixture
def sample_economic_terms():
    """List of economic terms for testing."""
    return ["inflación", "PIB", "reservas", "dólar", "peso", "desempleo"]


@pytest.fixture
def sample_argentine_expressions():
    """List of Argentine expressions for testing."""
    return ["laburo", "guita", "quilombo", "bondi", "che", "posta"]


# ============================================================================
# Performance Testing Fixtures
# ============================================================================

@pytest.fixture
def performance_baseline():
    """Performance baseline metrics for comparison."""
    return {
        "transcription_time_per_minute": 2.0,  # seconds
        "database_query_time": 0.05,  # seconds
        "api_response_time": 0.2,  # seconds
        "memory_usage_mb": 500  # MB
    }


# ============================================================================
# Helper Functions
# ============================================================================

def create_test_audio_file(filename: str, content: bytes = None) -> Path:
    """Helper function to create test audio files."""
    if content is None:
        # Create minimal MP3 header
        content = b'\xff\xfb\x90\x00' + b'\x00' * 1000

    test_file = Path("tests/temp") / filename
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_bytes(content)
    return test_file


def assert_transcription_result(result, expected_success=True):
    """Helper function to validate TranscriptionResult objects."""
    assert result.success == expected_success
    if expected_success:
        assert result.full_transcript
        assert result.transcript_preview
        assert result.filename
        assert not result.error
    else:
        assert result.error
        assert not result.full_transcript