"""
Comprehensive tests for DatabaseRepository covering all database operations,
connection management, and transaction safety.
"""
import pytest
import sqlite3
from datetime import datetime
from unittest.mock import patch, Mock

from src.repositories.database_repository import DatabaseRepository
from tests.fixtures.test_data import SAMPLE_ECONOMIC_TERMS, SAMPLE_ARGENTINE_EXPRESSIONS


class TestDatabaseInitialization:
    """Test database initialization and schema creation."""

    def test_database_initialization_creates_tables(self, db_repository):
        """Test that database initialization creates all required tables."""
        with db_repository.get_connection() as conn:
            cursor = conn.cursor()

            # Check that all tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]

            expected_tables = [
                'transcriptions',
                'economic_glossary',
                'argentine_dictionary',
                'candidate_terms'
            ]

            for table in expected_tables:
                assert table in tables, f"Table '{table}' was not created"

    def test_database_indexes_created(self, db_repository):
        """Test that performance indexes are created."""
        with db_repository.get_connection() as conn:
            cursor = conn.cursor()

            # Check that indexes exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
            indexes = [row[0] for row in cursor.fetchall()]

            expected_indexes = [
                'idx_transcriptions_created_at',
                'idx_economic_glossary_term',
                'idx_argentine_dictionary_expression',
                'idx_candidate_terms_term'
            ]

            for index in expected_indexes:
                assert index in indexes, f"Index '{index}' was not created"

    def test_database_schema_structure(self, db_repository):
        """Test that tables have correct schema structure."""
        with db_repository.get_connection() as conn:
            cursor = conn.cursor()

            # Test transcriptions table schema
            cursor.execute("PRAGMA table_info(transcriptions)")
            transcription_columns = {row[1]: row[2] for row in cursor.fetchall()}

            expected_transcription_columns = {
                'id': 'INTEGER',
                'filename': 'TEXT',
                'transcript': 'TEXT',
                'created_at': 'TEXT'
            }

            for col_name, col_type in expected_transcription_columns.items():
                assert col_name in transcription_columns
                assert transcription_columns[col_name] == col_type

            # Test economic_glossary table schema
            cursor.execute("PRAGMA table_info(economic_glossary)")
            economic_columns = {row[1]: row[2] for row in cursor.fetchall()}

            expected_economic_columns = {
                'id': 'INTEGER',
                'term': 'TEXT',
                'category': 'TEXT',
                'first_seen': 'TEXT'
            }

            for col_name, col_type in expected_economic_columns.items():
                assert col_name in economic_columns
                assert economic_columns[col_name] == col_type


class TestConnectionManagement:
    """Test database connection management and context manager behavior."""

    def test_connection_context_manager_success(self, db_repository):
        """Test that connection context manager works correctly on success."""
        with db_repository.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO transcriptions (filename, transcript, created_at) VALUES (?, ?, ?)",
                         ("test.mp3", "test transcript", datetime.utcnow().isoformat()))
            # Connection should auto-commit on successful exit

        # Verify data was committed
        with db_repository.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transcriptions")
            count = cursor.fetchone()[0]
            assert count == 1

    def test_connection_context_manager_rollback_on_exception(self, db_repository):
        """Test that connection context manager rolls back on exceptions."""
        try:
            with db_repository.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("INSERT INTO transcriptions (filename, transcript, created_at) VALUES (?, ?, ?)",
                             ("test.mp3", "test transcript", datetime.utcnow().isoformat()))
                raise ValueError("Intentional error")
        except ValueError:
            pass

        # Verify data was rolled back
        with db_repository.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM transcriptions")
            count = cursor.fetchone()[0]
            assert count == 0

    def test_connection_row_factory_enabled(self, db_repository):
        """Test that connections have row factory enabled for dict-like access."""
        db_repository.save_transcription("test.mp3", "test transcript")

        with db_repository.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT filename, transcript FROM transcriptions LIMIT 1")
            row = cursor.fetchone()

            # Should be able to access by column name
            assert row['filename'] == "test.mp3"
            assert row['transcript'] == "test transcript"

    @patch('src.repositories.database_repository.sqlite3.connect')
    def test_connection_error_handling(self, mock_connect, db_repository):
        """Test handling of connection errors."""
        mock_connect.side_effect = sqlite3.Error("Connection failed")

        with pytest.raises(sqlite3.Error):
            with db_repository.get_connection() as conn:
                pass


class TestTranscriptionOperations:
    """Test transcription-related database operations."""

    def test_save_transcription_success(self, db_repository):
        """Test successful transcription saving."""
        filename = "test_audio.mp3"
        transcript = "This is a test transcription"

        transcription_id = db_repository.save_transcription(filename, transcript)

        assert isinstance(transcription_id, int)
        assert transcription_id > 0

    def test_save_transcription_returns_correct_id(self, db_repository):
        """Test that save_transcription returns the correct ID."""
        id1 = db_repository.save_transcription("audio1.mp3", "transcript1")
        id2 = db_repository.save_transcription("audio2.mp3", "transcript2")

        assert id2 == id1 + 1

    def test_get_transcription_by_id_success(self, db_repository):
        """Test successful retrieval of transcription by ID."""
        filename = "test_audio.mp3"
        transcript = "This is a test transcription"

        transcription_id = db_repository.save_transcription(filename, transcript)
        result = db_repository.get_transcription_by_id(transcription_id)

        assert result is not None
        assert result.id == transcription_id
        assert result.filename == filename
        assert result.transcript == transcript
        assert isinstance(result.created_at, datetime)

    def test_get_transcription_by_id_not_found(self, db_repository):
        """Test retrieval of non-existent transcription."""
        result = db_repository.get_transcription_by_id(999)
        assert result is None

    def test_save_transcription_with_unicode(self, db_repository):
        """Test saving transcriptions with unicode characters."""
        filename = "audio_español.mp3"
        transcript = "Hoy hablamos de inflación, niños y corazón en Argentina"

        transcription_id = db_repository.save_transcription(filename, transcript)
        result = db_repository.get_transcription_by_id(transcription_id)

        assert result.transcript == transcript
        assert result.filename == filename


class TestEconomicGlossaryOperations:
    """Test economic glossary database operations."""

    def test_add_economic_term_success(self, db_repository):
        """Test successful addition of economic term."""
        result = db_repository.add_economic_term("inflación", "economic")
        assert result is True

    def test_add_economic_term_duplicate(self, db_repository):
        """Test that duplicate economic terms are handled correctly."""
        # Add term first time
        result1 = db_repository.add_economic_term("inflación", "economic")
        assert result1 is True

        # Add same term again
        result2 = db_repository.add_economic_term("inflación", "economic")
        assert result2 is False

    def test_get_economic_terms(self, db_repository):
        """Test retrieval of all economic terms."""
        # Add some terms
        test_terms = ["inflación", "PIB", "dólar"]
        for term in test_terms:
            db_repository.add_economic_term(term, "economic")

        result = db_repository.get_economic_terms()

        assert len(result) == len(test_terms)
        retrieved_terms = [row[0] for row in result]
        for term in test_terms:
            assert term in retrieved_terms

    def test_term_exists_in_economic_glossary(self, db_repository):
        """Test checking existence of terms in economic glossary."""
        term = "inflación"

        # Should not exist initially
        assert db_repository.term_exists_in_economic_glossary(term) is False

        # Add term
        db_repository.add_economic_term(term, "economic")

        # Should exist now
        assert db_repository.term_exists_in_economic_glossary(term) is True

    def test_economic_term_categories(self, db_repository):
        """Test that economic terms can have different categories."""
        db_repository.add_economic_term("inflación", "economic")
        db_repository.add_economic_term("blockchain", "manual")

        terms = db_repository.get_economic_terms()
        term_dict = {row[0]: row[1] for row in terms}

        assert term_dict["inflación"] == "economic"
        assert term_dict["blockchain"] == "manual"


class TestArgentineDictionaryOperations:
    """Test Argentine dictionary database operations."""

    def test_add_argentine_expression_success(self, db_repository):
        """Test successful addition of Argentine expression."""
        result = db_repository.add_argentine_expression("laburo")
        assert result is True

    def test_add_argentine_expression_duplicate(self, db_repository):
        """Test that duplicate Argentine expressions are handled correctly."""
        # Add expression first time
        result1 = db_repository.add_argentine_expression("laburo")
        assert result1 is True

        # Add same expression again
        result2 = db_repository.add_argentine_expression("laburo")
        assert result2 is False

    def test_get_argentine_expressions(self, db_repository):
        """Test retrieval of all Argentine expressions."""
        test_expressions = ["laburo", "guita", "quilombo"]
        for expr in test_expressions:
            db_repository.add_argentine_expression(expr)

        result = db_repository.get_argentine_expressions()

        assert len(result) == len(test_expressions)
        retrieved_expressions = [row[0] for row in result]
        for expr in test_expressions:
            assert expr in retrieved_expressions

    def test_expression_exists_in_argentine_dictionary(self, db_repository):
        """Test checking existence of expressions in Argentine dictionary."""
        expression = "laburo"

        # Should not exist initially
        assert db_repository.expression_exists_in_argentine_dictionary(expression) is False

        # Add expression
        db_repository.add_argentine_expression(expression)

        # Should exist now
        assert db_repository.expression_exists_in_argentine_dictionary(expression) is True


class TestCandidateTermOperations:
    """Test candidate term database operations."""

    def test_add_candidate_term_success(self, db_repository):
        """Test successful addition of candidate term."""
        result = db_repository.add_candidate_term("blockchain", "el blockchain es innovador")
        assert result is True

    def test_add_candidate_term_duplicate(self, db_repository):
        """Test that duplicate candidate terms are handled correctly."""
        term = "blockchain"
        context = "el blockchain es innovador"

        # Add term first time
        result1 = db_repository.add_candidate_term(term, context)
        assert result1 is True

        # Add same term again
        result2 = db_repository.add_candidate_term(term, "different context")
        assert result2 is False

    def test_get_candidate_terms(self, db_repository):
        """Test retrieval of all candidate terms."""
        test_terms = [
            ("blockchain", "el blockchain es innovador"),
            ("fintech", "las fintech están creciendo"),
            ("startup", "mi startup favorita")
        ]

        for term, context in test_terms:
            db_repository.add_candidate_term(term, context)

        result = db_repository.get_candidate_terms()

        assert len(result) == len(test_terms)
        retrieved_data = [(row[0], row[2]) for row in result]  # term, context
        for term, context in test_terms:
            assert (term, context) in retrieved_data

    def test_candidate_term_exists(self, db_repository):
        """Test checking existence of candidate terms."""
        term = "blockchain"

        # Should not exist initially
        assert db_repository.candidate_term_exists(term) is False

        # Add term
        db_repository.add_candidate_term(term, "context")

        # Should exist now
        assert db_repository.candidate_term_exists(term) is True

    def test_remove_candidate_term_success(self, db_repository):
        """Test successful removal of candidate term."""
        term = "blockchain"

        # Add term
        db_repository.add_candidate_term(term, "context")
        assert db_repository.candidate_term_exists(term) is True

        # Remove term
        result = db_repository.remove_candidate_term(term)
        assert result is True
        assert db_repository.candidate_term_exists(term) is False

    def test_remove_candidate_term_not_found(self, db_repository):
        """Test removal of non-existent candidate term."""
        result = db_repository.remove_candidate_term("nonexistent")
        assert result is False


class TestDatabaseConcurrency:
    """Test database operations under concurrent access."""

    def test_concurrent_inserts(self, db_repository):
        """Test concurrent database inserts."""
        import threading
        import time

        results = []
        errors = []

        def add_terms(thread_id):
            try:
                for i in range(10):
                    term = f"term_{thread_id}_{i}"
                    success = db_repository.add_economic_term(term, "economic")
                    results.append((thread_id, i, success))
                    time.sleep(0.01)  # Small delay to encourage concurrency
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads
        threads = []
        for thread_id in range(3):
            thread = threading.Thread(target=add_terms, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Check results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 30  # 3 threads * 10 operations each

        # Verify all terms were added
        all_terms = db_repository.get_economic_terms()
        assert len(all_terms) == 30

    def test_transaction_isolation(self, db_repository):
        """Test that transactions are properly isolated."""
        # This is a basic test - SQLite's isolation is limited
        term1 = "isolation_test_1"
        term2 = "isolation_test_2"

        with db_repository.get_connection() as conn1:
            cursor1 = conn1.cursor()
            cursor1.execute(
                "INSERT INTO economic_glossary (term, category, first_seen) VALUES (?, ?, ?)",
                (term1, "economic", datetime.utcnow().isoformat())
            )

            # This should be visible within the same connection
            cursor1.execute("SELECT COUNT(*) FROM economic_glossary WHERE term = ?", (term1,))
            count1 = cursor1.fetchone()[0]
            assert count1 == 1

        # After committing, should be visible in new connection
        with db_repository.get_connection() as conn2:
            cursor2 = conn2.cursor()
            cursor2.execute("SELECT COUNT(*) FROM economic_glossary WHERE term = ?", (term1,))
            count2 = cursor2.fetchone()[0]
            assert count2 == 1


class TestDatabaseErrorHandling:
    """Test database error handling and edge cases."""

    def test_database_constraint_violations(self, db_repository):
        """Test handling of database constraint violations."""
        term = "duplicate_test"

        # Add term first time
        success1 = db_repository.add_economic_term(term, "economic")
        assert success1 is True

        # Add same term again - should handle IntegrityError gracefully
        success2 = db_repository.add_economic_term(term, "manual")
        assert success2 is False

    def test_malformed_data_handling(self, db_repository):
        """Test handling of malformed or edge case data."""
        edge_cases = [
            ("", "empty_string"),  # Empty string
            ("a" * 1000, "long_string"),  # Very long string
            ("term\nwith\nnewlines", "newlines"),  # String with newlines
            ("term\x00with\x00nulls", "nulls"),  # String with null bytes
        ]

        for term, description in edge_cases:
            try:
                result = db_repository.add_economic_term(term, "economic")
                # Should either succeed or fail gracefully
                assert isinstance(result, bool)
            except Exception as e:
                pytest.fail(f"Unexpected exception for {description}: {e}")

    @patch('src.repositories.database_repository.sqlite3.connect')
    def test_database_unavailable_error_handling(self, mock_connect):
        """Test handling when database is unavailable."""
        mock_connect.side_effect = sqlite3.OperationalError("Database locked")

        # Repository should be created but operations should fail gracefully
        repo = DatabaseRepository()

        with pytest.raises(sqlite3.OperationalError):
            with repo.get_connection() as conn:
                pass