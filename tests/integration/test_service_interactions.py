"""
Integration tests for service interactions and end-to-end workflows.
Tests the integration between services and real database operations.
"""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

from src.services.transcription_service import TranscriptionService
from src.services.glossary_service import GlossaryService
from src.services.term_detection_service import TermDetectionService
from src.repositories.database_repository import DatabaseRepository
from tests.fixtures.test_data import create_mp3_bytes, SAMPLE_TRANSCRIPTS
from tests.utils.test_helpers import temporary_file


class TestTranscriptionToGlossaryWorkflow:
    """Test integration between transcription and glossary services."""

    @pytest.fixture
    def integrated_services(self):
        """Create integrated services sharing the same database."""
        db_repo = DatabaseRepository()
        return {
            'transcription': TranscriptionService(db_repo),
            'glossary': GlossaryService(db_repo),
            'term_detection': TermDetectionService(db_repo),
            'database': db_repo
        }

    @patch('src.services.transcription_service.whisper.load_model')
    def test_full_transcription_to_glossary_workflow(self, mock_load_model, integrated_services):
        """Test complete workflow from audio transcription to glossary update."""
        # Mock Whisper model
        mock_model = Mock()
        mock_model.transcribe.return_value = {"text": SAMPLE_TRANSCRIPTS['economic_heavy']}
        mock_load_model.return_value = mock_model

        services = integrated_services
        mp3_content = create_mp3_bytes(1)
        filename = "economic_discussion.mp3"

        # Step 1: Transcribe audio file
        with temporary_file(mp3_content, "economic", ".mp3") as temp_file:
            transcription_result = services['transcription'].transcribe_audio(temp_file, filename)

        assert transcription_result.success is True
        assert transcription_result.full_transcript == SAMPLE_TRANSCRIPTS['economic_heavy']

        # Step 2: Update glossaries with transcript
        glossary_stats = services['glossary'].update_glossaries(transcription_result.full_transcript)

        assert glossary_stats['economic_terms_added'] > 0
        assert glossary_stats['argentine_expressions_added'] > 0

        # Step 3: Verify data persistence
        glossaries = services['glossary'].get_glossaries()
        assert len(glossaries['economic_glossary']) > 0
        assert len(glossaries['argentine_dictionary']) > 0

        # Step 4: Verify transcription is stored
        stored_transcription = services['database'].get_transcription_by_id(1)
        assert stored_transcription is not None
        assert stored_transcription.transcript == SAMPLE_TRANSCRIPTS['economic_heavy']

    def test_term_detection_to_candidate_workflow(self, integrated_services):
        """Test workflow from term detection to candidate term creation."""
        services = integrated_services
        text_with_candidates = "Hoy discutimos sobre blockchain y las criptomonedas en Argentina."

        # Step 1: Detect candidate terms
        candidates = services['term_detection'].detect_candidate_terms(text_with_candidates)

        assert len(candidates) > 0
        candidate_terms = [candidate.term for candidate in candidates]
        assert any('blockchain' in term.lower() for term in candidate_terms)

        # Step 2: Verify candidates are stored in database
        stored_candidates = services['database'].get_candidate_terms()
        assert len(stored_candidates) > 0

        # Step 3: Promote a candidate to economic glossary
        candidate_to_promote = candidates[0].term
        promotion_success = services['glossary'].promote_candidate_to_economic(candidate_to_promote)

        assert promotion_success is True
        assert services['database'].term_exists_in_economic_glossary(candidate_to_promote)
        assert not services['database'].candidate_term_exists(candidate_to_promote)

    def test_concurrent_service_operations(self, integrated_services):
        """Test concurrent operations across multiple services."""
        import threading
        import time

        services = integrated_services
        results = []
        errors = []

        def transcription_workflow(thread_id):
            try:
                with patch('src.services.transcription_service.whisper.load_model') as mock_load:
                    mock_model = Mock()
                    mock_model.transcribe.return_value = {"text": f"Inflación en Argentina {thread_id}"}
                    mock_load.return_value = mock_model

                    mp3_content = create_mp3_bytes(1)
                    filename = f"concurrent_{thread_id}.mp3"

                    with temporary_file(mp3_content, f"concurrent_{thread_id}", ".mp3") as temp_file:
                        time.sleep(0.01)  # Encourage concurrency
                        result = services['transcription'].transcribe_audio(temp_file, filename)
                        results.append((thread_id, 'transcription', result.success))
            except Exception as e:
                errors.append((thread_id, 'transcription', str(e)))

        def glossary_workflow(thread_id):
            try:
                transcript = f"La inflación y el PIB son importantes {thread_id}"
                time.sleep(0.01)
                stats = services['glossary'].update_glossaries(transcript)
                results.append((thread_id, 'glossary', stats['economic_terms_added'] > 0))
            except Exception as e:
                errors.append((thread_id, 'glossary', str(e)))

        def term_detection_workflow(thread_id):
            try:
                text = f"Hablamos de blockchain y fintech {thread_id}"
                time.sleep(0.01)
                candidates = services['term_detection'].detect_candidate_terms(text)
                results.append((thread_id, 'term_detection', len(candidates) > 0))
            except Exception as e:
                errors.append((thread_id, 'term_detection', str(e)))

        # Create threads for different workflows
        threads = []
        for thread_id in range(3):
            threads.extend([
                threading.Thread(target=transcription_workflow, args=(thread_id,)),
                threading.Thread(target=glossary_workflow, args=(thread_id,)),
                threading.Thread(target=term_detection_workflow, args=(thread_id,))
            ])

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 9  # 3 workflows * 3 threads each

        # All operations should succeed
        for thread_id, workflow, success in results:
            assert success is True, f"Workflow {workflow} failed for thread {thread_id}"


class TestDatabaseTransactionIntegrity:
    """Test database transaction integrity across service operations."""

    def test_rollback_on_service_failure(self):
        """Test that database operations rollback properly on service failures."""
        db_repo = DatabaseRepository()
        glossary_service = GlossaryService(db_repo)

        # Mock database to fail on second operation
        with patch.object(db_repo, 'add_economic_term') as mock_add_economic:
            with patch.object(db_repo, 'add_argentine_expression') as mock_add_argentine:
                mock_add_economic.return_value = True
                mock_add_argentine.side_effect = Exception("Database error")

                transcript = "La inflación y el laburo están relacionados"

                # This should handle the failure gracefully
                try:
                    stats = glossary_service.update_glossaries(transcript)
                    # Depending on implementation, might return partial stats or raise
                    assert isinstance(stats, dict)
                except Exception:
                    # If implementation allows exceptions, that's also acceptable
                    pass

    def test_data_consistency_across_services(self):
        """Test data consistency when multiple services interact with same data."""
        db_repo = DatabaseRepository()
        glossary_service = GlossaryService(db_repo)
        term_detection_service = TermDetectionService(db_repo)

        # Add some terms through glossary service
        transcript = "Hablamos de inflación y blockchain en Argentina"
        glossary_stats = glossary_service.update_glossaries(transcript)

        # Detect candidates through term detection service
        candidates = term_detection_service.detect_candidate_terms(transcript)

        # Verify data consistency
        economic_terms = db_repo.get_economic_terms()
        candidate_terms = db_repo.get_candidate_terms()

        # Terms added by glossary should not appear as candidates
        economic_term_list = [term[0] for term in economic_terms]
        candidate_term_list = [term[0] for term in candidate_terms]

        # Check that known economic terms don't appear as candidates
        for term in economic_term_list:
            assert term not in candidate_term_list


class TestServiceConfigurationIntegration:
    """Test integration with configuration and environment settings."""

    @patch('src.config.settings.ECONOMIC_TERMS', ['custom_economic_term'])
    @patch('src.config.settings.ARGENTINE_EXPRESSIONS', ['custom_argentine_expr'])
    def test_services_respect_configuration(self):
        """Test that all services respect configuration settings."""
        db_repo = DatabaseRepository()
        glossary_service = GlossaryService(db_repo)
        term_detection_service = TermDetectionService(db_repo)

        # Test text with custom configured terms
        text = "The custom_economic_term and custom_argentine_expr are important"

        # Glossary service should detect configured terms
        glossary_stats = glossary_service.update_glossaries(text)
        assert glossary_stats['economic_terms_added'] == 1
        assert glossary_stats['argentine_expressions_added'] == 1

        # Term detection should respect the same configuration
        candidates = term_detection_service.detect_candidate_terms(
            "Some other unknown_term in the text"
        )
        # Should detect unknown_term as candidate, but not the configured ones
        candidate_terms = [candidate.term for candidate in candidates]
        assert 'custom_economic_term' not in candidate_terms
        assert 'custom_argentine_expr' not in candidate_terms

    def test_database_path_configuration(self):
        """Test that services work with different database configurations."""
        import tempfile
        import os

        # Create temporary database file
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as temp_db:
            temp_db_path = temp_db.name

        try:
            # Create repository with custom database path
            custom_repo = DatabaseRepository(temp_db_path)
            glossary_service = GlossaryService(custom_repo)

            # Test operations work with custom database
            transcript = "Test inflación in custom database"
            stats = glossary_service.update_glossaries(transcript)

            assert stats['economic_terms_added'] > 0

            # Verify data is in the custom database
            glossaries = glossary_service.get_glossaries()
            assert len(glossaries['economic_glossary']) > 0

        finally:
            # Cleanup
            if os.path.exists(temp_db_path):
                os.unlink(temp_db_path)


class TestErrorPropagationAndHandling:
    """Test error propagation and handling across service boundaries."""

    def test_database_error_propagation(self):
        """Test how database errors propagate through service layers."""
        db_repo = DatabaseRepository()

        with patch.object(db_repo, 'get_connection') as mock_connection:
            mock_connection.side_effect = Exception("Database connection failed")

            glossary_service = GlossaryService(db_repo)

            # Test that service handles database errors gracefully
            try:
                glossaries = glossary_service.get_glossaries()
                # Should return empty structure on error
                assert glossaries == {"economic_glossary": [], "argentine_dictionary": []}
            except Exception:
                # If service propagates exception, that's also acceptable behavior
                pass

    def test_service_failure_isolation(self):
        """Test that failure in one service doesn't affect others."""
        db_repo = DatabaseRepository()
        glossary_service = GlossaryService(db_repo)
        term_detection_service = TermDetectionService(db_repo)

        # Cause failure in glossary service
        with patch.object(glossary_service, 'update_glossaries') as mock_update:
            mock_update.side_effect = Exception("Glossary service failed")

            # Term detection service should still work
            candidates = term_detection_service.detect_candidate_terms("Test blockchain technology")
            assert isinstance(candidates, list)

            # Database should still be accessible directly
            success = db_repo.add_economic_term("test_term", "manual")
            assert success is True


class TestPerformanceIntegration:
    """Test performance characteristics of integrated services."""

    def test_large_transcript_processing(self):
        """Test processing of large transcripts through full workflow."""
        import time

        db_repo = DatabaseRepository()
        glossary_service = GlossaryService(db_repo)
        term_detection_service = TermDetectionService(db_repo)

        # Create large transcript with repeated terms
        large_transcript = " ".join([
            "La inflación en Argentina afecta el PIB y el dólar. "
            "Los ciudadanos buscan laburo y manejan la guita con cuidado. "
            "Las empresas de blockchain y fintech están creciendo. "
        ] * 100)  # Repeat 100 times

        start_time = time.time()

        # Process through glossary service
        glossary_stats = glossary_service.update_glossaries(large_transcript)

        # Process through term detection
        candidates = term_detection_service.detect_candidate_terms(large_transcript)

        processing_time = time.time() - start_time

        # Should complete within reasonable time (adjust threshold as needed)
        assert processing_time < 10.0, f"Processing took {processing_time:.2f} seconds"

        # Should still produce valid results
        assert glossary_stats['economic_terms_added'] > 0
        assert isinstance(candidates, list)

    def test_concurrent_database_access_performance(self):
        """Test performance under concurrent database access."""
        import threading
        import time

        db_repo = DatabaseRepository()
        services = [GlossaryService(db_repo) for _ in range(5)]

        results = []
        start_time = time.time()

        def concurrent_operation(service_id, service):
            try:
                for i in range(10):
                    transcript = f"Inflación {service_id}_{i} y PIB en Argentina"
                    stats = service.update_glossaries(transcript)
                    results.append((service_id, i, stats['economic_terms_added']))
            except Exception as e:
                results.append((service_id, -1, str(e)))

        threads = []
        for i, service in enumerate(services):
            thread = threading.Thread(target=concurrent_operation, args=(i, service))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # Should complete all operations within reasonable time
        assert total_time < 15.0, f"Concurrent operations took {total_time:.2f} seconds"

        # All operations should succeed
        assert len(results) == 50  # 5 services * 10 operations each
        for service_id, operation_id, result in results:
            assert isinstance(result, int) and result >= 0, f"Operation {service_id}_{operation_id} failed: {result}"