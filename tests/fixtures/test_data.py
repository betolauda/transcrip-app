"""
Test data factories and utilities for generating consistent test data.
"""
import factory
from datetime import datetime
from pathlib import Path

from src.models.domain_models import (
    Transcription,
    EconomicTerm,
    ArgentineTerm,
    CandidateTerm,
    TranscriptionResult
)


class TranscriptionFactory(factory.Factory):
    """Factory for creating Transcription test data."""

    class Meta:
        model = Transcription

    id = factory.Sequence(lambda n: n)
    filename = factory.Sequence(lambda n: f"audio_{n}.mp3")
    transcript = factory.Faker('text', max_nb_chars=500)
    created_at = factory.LazyFunction(datetime.utcnow)


class EconomicTermFactory(factory.Factory):
    """Factory for creating EconomicTerm test data."""

    class Meta:
        model = EconomicTerm

    id = factory.Sequence(lambda n: n)
    term = factory.Faker('word')
    category = factory.Iterator(['economic', 'manual'])
    first_seen = factory.LazyFunction(datetime.utcnow)


class ArgentineTermFactory(factory.Factory):
    """Factory for creating ArgentineTerm test data."""

    class Meta:
        model = ArgentineTerm

    id = factory.Sequence(lambda n: n)
    expression = factory.Faker('word')
    first_seen = factory.LazyFunction(datetime.utcnow)


class CandidateTermFactory(factory.Factory):
    """Factory for creating CandidateTerm test data."""

    class Meta:
        model = CandidateTerm

    id = factory.Sequence(lambda n: n)
    term = factory.Faker('word')
    first_seen = factory.LazyFunction(datetime.utcnow)
    context_snippet = factory.Faker('sentence')


class TranscriptionResultFactory(factory.Factory):
    """Factory for creating TranscriptionResult test data."""

    class Meta:
        model = TranscriptionResult

    filename = factory.Sequence(lambda n: f"test_{n}.mp3")
    transcript_preview = factory.Faker('text', max_nb_chars=200)
    full_transcript = factory.Faker('text', max_nb_chars=1000)
    message = "Test transcription completed successfully"
    success = True
    error = None


# Test data constants
SAMPLE_ECONOMIC_TERMS = [
    "inflación", "PIB", "PBI", "dólar", "peso", "reservas",
    "desempleo", "pobreza", "déficit", "superávit", "tarifas",
    "subsidios", "impuestos", "inversión", "exportaciones"
]

SAMPLE_ARGENTINE_EXPRESSIONS = [
    "laburo", "guita", "quilombo", "bondi", "mango", "fiaca",
    "che", "posta", "macana", "changas", "boludo", "pibe",
    "flaca", "loco", "bárbaro", "genial"
]

SAMPLE_TRANSCRIPTS = {
    'economic_heavy': (
        "Hoy analizamos la inflación que ha subido un 15% este mes. "
        "El PIB cayó 3.2% y las reservas del banco central están en mínimos históricos. "
        "El dólar blue subió mientras que el peso se devalúa constantemente. "
        "Las exportaciones de carne han bajado y los subsidios a los combustibles aumentaron. "
        "El déficit fiscal preocupa a los inversores internacionales."
    ),
    'argentine_heavy': (
        "Che, qué quilombo está todo con el laburo. "
        "No hay mango para nada y la gente anda con mucha fiaca. "
        "El bondi está carísimo y las changas no alcanzan. "
        "Es una macana pero hay que seguir, boludo. "
        "Los pibes están preocupados por el futuro."
    ),
    'mixed_content': (
        "Che, hablando en serio del tema económico, la inflación está terrible. "
        "Mi laburo en el banco me permite ver cómo la guita no alcanza. "
        "El PIB bajó y es un quilombo para todos. "
        "Las reservas están bajas y el dólar sube como loco. "
        "Blockchain y fintech pueden ser soluciones, pero hay que ver."
    ),
    'candidate_rich': (
        "El tema de las criptomonedas y la tokenización está muy candente. "
        "Los unicornios tecnológicos argentinos están expandiéndose. "
        "La gamificación de las finanzas es una tendencia emergente. "
        "El metaverso puede revolucionar las transacciones económicas. "
        "Los algoritmos de machine learning predicen volatilidad."
    )
}

def create_mp3_bytes(size_kb: int = 1) -> bytes:
    """Create fake MP3 file bytes for testing."""
    # MP3 frame header (basic pattern)
    mp3_header = b'\xff\xfb\x90\x00'
    # Pad to desired size
    padding = b'\x00' * (size_kb * 1024 - len(mp3_header))
    return mp3_header + padding

def create_malicious_file_bytes() -> bytes:
    """Create bytes that look like MP3 but contain malicious content."""
    # Start with MP3-like header but add script content
    fake_header = b'\xff\xfb\x90\x00'
    script_content = b'#!/bin/bash\nrm -rf /\n'
    padding = b'\x00' * 500
    return fake_header + script_content + padding

def create_invalid_file_bytes() -> bytes:
    """Create completely invalid file bytes."""
    return b'This is not an audio file at all, just plain text content.'

def create_oversized_file_bytes(size_mb: int = 10) -> bytes:
    """Create file bytes that exceed size limits."""
    mp3_header = b'\xff\xfb\x90\x00'
    padding = b'\x00' * (size_mb * 1024 * 1024 - len(mp3_header))
    return mp3_header + padding