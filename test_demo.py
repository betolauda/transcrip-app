#!/usr/bin/env python3
"""
Demo test runner to showcase the testing framework without external dependencies.
This demonstrates the test structure and validates core functionality.
"""
import sys
import os
import sqlite3
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

def test_database_repository():
    """Test database repository basic functionality."""
    print("Testing DatabaseRepository...")

    try:
        from repositories.database_repository import DatabaseRepository

        # Test with in-memory database
        repo = DatabaseRepository(':memory:')

        # Test table creation
        with repo.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['transcriptions', 'economic_glossary', 'argentine_dictionary', 'candidate_terms']
        missing_tables = [t for t in expected_tables if t not in tables]

        if not missing_tables:
            print("✅ Database initialization: PASS")
        else:
            print(f"❌ Database initialization: FAIL - Missing tables: {missing_tables}")
            return False

        # Test basic operations
        success = repo.add_economic_term("inflación", "economic")
        if success:
            print("✅ Economic term addition: PASS")
        else:
            print("❌ Economic term addition: FAIL")
            return False

        # Test duplicate prevention
        duplicate = repo.add_economic_term("inflación", "economic")
        if not duplicate:
            print("✅ Duplicate prevention: PASS")
        else:
            print("❌ Duplicate prevention: FAIL")
            return False

        return True

    except Exception as e:
        print(f"❌ DatabaseRepository test failed: {str(e)}")
        return False

def test_glossary_service():
    """Test glossary service basic functionality."""
    print("\nTesting GlossaryService...")

    try:
        from repositories.database_repository import DatabaseRepository
        from services.glossary_service import GlossaryService

        repo = DatabaseRepository(':memory:')
        service = GlossaryService(repo)

        # Test glossary update
        transcript = "La inflación en Argentina afecta el PIB y genera preocupación sobre el laburo y la guita."
        stats = service.update_glossaries(transcript)

        if isinstance(stats, dict) and 'economic_terms_added' in stats and 'argentine_expressions_added' in stats:
            print("✅ Glossary update structure: PASS")
        else:
            print("❌ Glossary update structure: FAIL")
            return False

        if stats['economic_terms_added'] > 0:
            print("✅ Economic term detection: PASS")
        else:
            print("❌ Economic term detection: FAIL")
            return False

        if stats['argentine_expressions_added'] > 0:
            print("✅ Argentine expression detection: PASS")
        else:
            print("❌ Argentine expression detection: FAIL")
            return False

        # Test glossary retrieval
        glossaries = service.get_glossaries()
        if isinstance(glossaries, dict) and 'economic_glossary' in glossaries and 'argentine_dictionary' in glossaries:
            print("✅ Glossary retrieval: PASS")
        else:
            print("❌ Glossary retrieval: FAIL")
            return False

        return True

    except Exception as e:
        print(f"❌ GlossaryService test failed: {str(e)}")
        return False

def test_term_detection_service():
    """Test term detection service basic functionality."""
    print("\nTesting TermDetectionService...")

    try:
        from repositories.database_repository import DatabaseRepository
        from services.term_detection_service import TermDetectionService

        repo = DatabaseRepository(':memory:')
        service = TermDetectionService(repo)

        # Test candidate detection
        text = "Hoy discutimos sobre blockchain, fintech y las startups unicornio en Argentina."
        candidates = service.detect_candidate_terms(text)

        if isinstance(candidates, list):
            print("✅ Candidate detection structure: PASS")
        else:
            print("❌ Candidate detection structure: FAIL")
            return False

        if len(candidates) > 0:
            print(f"✅ Candidate detection found {len(candidates)} terms: PASS")
        else:
            print("❌ Candidate detection found no terms: FAIL")
            return False

        # Check candidate structure
        if hasattr(candidates[0], 'term') and hasattr(candidates[0], 'context'):
            print("✅ Candidate term structure: PASS")
        else:
            print("❌ Candidate term structure: FAIL")
            return False

        return True

    except Exception as e:
        print(f"❌ TermDetectionService test failed: {str(e)}")
        return False

def test_file_validation():
    """Test file validation functionality."""
    print("\nTesting File Validation...")

    try:
        from services.transcription_service import TranscriptionService
        from repositories.database_repository import DatabaseRepository

        repo = DatabaseRepository(':memory:')
        service = TranscriptionService(repo)

        # Create a temporary test file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            # Write minimal MP3 header
            temp_file.write(b'\xff\xfb\x90\x00' + b'\x00' * 1000)  # Small MP3-like file
            temp_file_path = Path(temp_file.name)

        try:
            # Test file validation
            is_valid, error = service.validate_audio_file(temp_file_path)

            if is_valid:
                print("✅ File validation for valid MP3: PASS")
            else:
                print(f"⚠️  File validation: {error}")

            # Test invalid extension
            invalid_file = temp_file_path.with_suffix('.exe')
            temp_file_path.rename(invalid_file)

            is_valid, error = service.validate_audio_file(invalid_file)
            if not is_valid and "not allowed" in error:
                print("✅ File extension validation: PASS")
            else:
                print("❌ File extension validation: FAIL")
                return False

        finally:
            # Cleanup
            for file_path in [temp_file_path, invalid_file]:
                if file_path.exists():
                    file_path.unlink()

        return True

    except Exception as e:
        print(f"❌ File validation test failed: {str(e)}")
        return False

def test_configuration():
    """Test configuration loading."""
    print("\nTesting Configuration...")

    try:
        from config import settings

        # Check that required settings exist
        required_settings = ['ECONOMIC_TERMS', 'ARGENTINE_EXPRESSIONS', 'MAX_FILE_SIZE_MB']
        for setting in required_settings:
            if hasattr(settings, setting):
                print(f"✅ Setting {setting}: PASS")
            else:
                print(f"❌ Setting {setting}: FAIL")
                return False

        # Check economic terms are loaded
        if len(settings.ECONOMIC_TERMS) > 0:
            print(f"✅ Economic terms loaded ({len(settings.ECONOMIC_TERMS)} terms): PASS")
        else:
            print("❌ Economic terms not loaded: FAIL")
            return False

        # Check Argentine expressions are loaded
        if len(settings.ARGENTINE_EXPRESSIONS) > 0:
            print(f"✅ Argentine expressions loaded ({len(settings.ARGENTINE_EXPRESSIONS)} expressions): PASS")
        else:
            print("❌ Argentine expressions not loaded: FAIL")
            return False

        return True

    except Exception as e:
        print(f"❌ Configuration test failed: {str(e)}")
        return False

def run_demo_tests():
    """Run demonstration tests."""
    print("="*80)
    print("SPANISH TRANSCRIPTION API - TESTING FRAMEWORK DEMO")
    print("="*80)
    print(f"Project Root: {Path.cwd()}")
    print(f"Python Version: {sys.version}")
    print("="*80)

    tests = [
        test_configuration,
        test_database_repository,
        test_glossary_service,
        test_term_detection_service,
        test_file_validation
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {str(e)}")
            results.append(False)

    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)

    passed = sum(results)
    total = len(results)
    success_rate = (passed / total) * 100

    print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")

    if passed == total:
        print("✅ ALL TESTS PASSED - Framework is working correctly!")
        print("\nNext Steps:")
        print("1. Install development dependencies: pip install -r requirements-dev.txt")
        print("2. Run full test suite: make test")
        print("3. Run specific test categories: make test-unit, make test-integration, etc.")
        print("4. Generate coverage report: make coverage")
    else:
        print("❌ SOME TESTS FAILED - Check the output above for details")

    print("="*80)
    return passed == total

if __name__ == '__main__':
    success = run_demo_tests()
    sys.exit(0 if success else 1)