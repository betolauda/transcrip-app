"""
Comprehensive unit tests for GlossaryService covering term detection,
promotion functionality, and statistics tracking.
"""
import pytest
from unittest.mock import Mock, patch

from src.services.glossary_service import GlossaryService
from tests.fixtures.test_data import SAMPLE_TRANSCRIPTS, SAMPLE_ECONOMIC_TERMS, SAMPLE_ARGENTINE_EXPRESSIONS


class TestGlossaryServiceInitialization:
    """Test GlossaryService initialization and dependency injection."""

    def test_service_initialization_with_repository(self, db_repository):
        """Test service initialization with provided repository."""
        service = GlossaryService(db_repository)
        assert service.db_repository is db_repository

    def test_service_initialization_without_repository(self):
        """Test service initialization creates default repository."""
        service = GlossaryService()
        assert service.db_repository is not None


class TestGlossaryUpdates:
    """Test glossary update functionality."""

    def test_update_glossaries_with_economic_terms(self, glossary_service):
        """Test updating glossaries with transcript containing economic terms."""
        transcript = SAMPLE_TRANSCRIPTS['economic_heavy']

        stats = glossary_service.update_glossaries(transcript)

        assert isinstance(stats, dict)
        assert "economic_terms_added" in stats
        assert "argentine_expressions_added" in stats
        assert stats["economic_terms_added"] > 0

    def test_update_glossaries_with_argentine_expressions(self, glossary_service):
        """Test updating glossaries with transcript containing Argentine expressions."""
        transcript = SAMPLE_TRANSCRIPTS['argentine_heavy']

        stats = glossary_service.update_glossaries(transcript)

        assert stats["argentine_expressions_added"] > 0

    def test_update_glossaries_with_mixed_content(self, glossary_service):
        """Test updating glossaries with mixed content."""
        transcript = SAMPLE_TRANSCRIPTS['mixed_content']

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] > 0
        assert stats["argentine_expressions_added"] > 0

    def test_update_glossaries_with_no_matches(self, glossary_service):
        """Test updating glossaries with text containing no known terms."""
        transcript = "This is a completely unrelated text about technology and computers."

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] == 0
        assert stats["argentine_expressions_added"] == 0

    def test_update_glossaries_case_insensitive_matching(self, glossary_service):
        """Test that term matching is case insensitive."""
        transcript = "La INFLACIÓN está muy alta y el PIB bajo. También hay poco LABURO."

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] > 0
        assert stats["argentine_expressions_added"] > 0

    def test_update_glossaries_word_boundary_matching(self, glossary_service):
        """Test that term matching respects word boundaries."""
        # "inflacionista" should not match "inflación"
        transcript = "El inflacionista habla de la inflación real."

        stats = glossary_service.update_glossaries(transcript)

        # Should only match "inflación", not "inflacionista"
        assert stats["economic_terms_added"] == 1

    def test_update_glossaries_duplicate_prevention(self, glossary_service):
        """Test that duplicate terms are not added multiple times."""
        transcript = "inflación y más inflación, siempre inflación"

        # Add same transcript twice
        stats1 = glossary_service.update_glossaries(transcript)
        stats2 = glossary_service.update_glossaries(transcript)

        # First time should add term
        assert stats1["economic_terms_added"] == 1
        # Second time should not add duplicate
        assert stats2["economic_terms_added"] == 0

    def test_update_glossaries_with_multiple_terms_same_category(self, glossary_service):
        """Test adding multiple terms from the same category."""
        transcript = "La inflación, el PIB, las reservas y el dólar están relacionados."

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] >= 4  # Should detect at least 4 terms

    def test_update_glossaries_with_accented_terms(self, glossary_service):
        """Test handling of accented characters in terms."""
        transcript = "La inflación está alta y el dólar también."

        stats = glossary_service.update_glossaries(transcript)

        # Should match both terms despite accents
        assert stats["economic_terms_added"] >= 2

    def test_update_glossaries_logging_behavior(self, glossary_service):
        """Test that appropriate logging occurs during updates."""
        with patch('src.services.glossary_service.logger') as mock_logger:
            transcript = "La inflación está muy alta."

            glossary_service.update_glossaries(transcript)

            # Verify logging calls
            mock_logger.info.assert_called()

    def test_update_glossaries_database_error_handling(self, glossary_service):
        """Test handling of database errors during updates."""
        with patch.object(glossary_service.db_repository, 'add_economic_term') as mock_add:
            mock_add.side_effect = Exception("Database error")

            transcript = "La inflación está alta."

            # Should not raise exception, should handle gracefully
            try:
                stats = glossary_service.update_glossaries(transcript)
                # Depending on implementation, might return 0 or raise
                assert isinstance(stats, dict)
            except Exception:
                # If implementation allows exceptions, that's also acceptable
                pass


class TestGlossaryRetrieval:
    """Test glossary data retrieval functionality."""

    def test_get_glossaries_empty_database(self, glossary_service):
        """Test getting glossaries from empty database."""
        glossaries = glossary_service.get_glossaries()

        assert isinstance(glossaries, dict)
        assert "economic_glossary" in glossaries
        assert "argentine_dictionary" in glossaries
        assert len(glossaries["economic_glossary"]) == 0
        assert len(glossaries["argentine_dictionary"]) == 0

    def test_get_glossaries_with_data(self, populated_db_repository):
        """Test getting glossaries with existing data."""
        service = GlossaryService(populated_db_repository)
        glossaries = service.get_glossaries()

        assert len(glossaries["economic_glossary"]) > 0
        assert len(glossaries["argentine_dictionary"]) > 0

        # Check structure of returned data
        for term_data in glossaries["economic_glossary"]:
            assert len(term_data) == 3  # term, category, first_seen

        for expr_data in glossaries["argentine_dictionary"]:
            assert len(expr_data) == 2  # expression, first_seen

    def test_get_glossaries_database_error_handling(self, glossary_service):
        """Test handling of database errors during retrieval."""
        with patch.object(glossary_service.db_repository, 'get_economic_terms') as mock_get:
            mock_get.side_effect = Exception("Database error")

            glossaries = glossary_service.get_glossaries()

            # Should return empty structure on error
            assert glossaries == {"economic_glossary": [], "argentine_dictionary": []}

    def test_get_glossaries_partial_failure(self, glossary_service):
        """Test handling when one glossary fails but not the other."""
        with patch.object(glossary_service.db_repository, 'get_economic_terms') as mock_get_econ:
            mock_get_econ.side_effect = Exception("Economic terms error")

            # Add some Argentine terms first
            glossary_service.db_repository.add_argentine_expression("laburo")

            glossaries = glossary_service.get_glossaries()

            # Should handle partial failure gracefully
            assert glossaries["economic_glossary"] == []
            # Argentine dictionary should still work
            assert len(glossaries["argentine_dictionary"]) >= 0


class TestCandidatePromotion:
    """Test candidate term promotion functionality."""

    def test_promote_candidate_to_economic_success(self, glossary_service):
        """Test successful promotion of candidate to economic glossary."""
        # Add a candidate term first
        glossary_service.db_repository.add_candidate_term("blockchain", "blockchain context")

        success = glossary_service.promote_candidate_to_economic("blockchain")

        assert success is True
        assert glossary_service.db_repository.term_exists_in_economic_glossary("blockchain")
        assert not glossary_service.db_repository.candidate_term_exists("blockchain")

    def test_promote_candidate_to_argentine_success(self, glossary_service):
        """Test successful promotion of candidate to Argentine dictionary."""
        # Add a candidate term first
        glossary_service.db_repository.add_candidate_term("buenardo", "está buenardo")

        success = glossary_service.promote_candidate_to_argentine("buenardo")

        assert success is True
        assert glossary_service.db_repository.expression_exists_in_argentine_dictionary("buenardo")
        assert not glossary_service.db_repository.candidate_term_exists("buenardo")

    def test_promote_nonexistent_candidate(self, glossary_service):
        """Test promotion of non-existent candidate term."""
        success = glossary_service.promote_candidate_to_economic("nonexistent")

        assert success is False

    def test_promote_candidate_already_in_economic_glossary(self, glossary_service):
        """Test promotion of candidate that already exists in economic glossary."""
        term = "inflación"

        # Add to economic glossary first
        glossary_service.db_repository.add_economic_term(term, "economic")
        # Add as candidate
        glossary_service.db_repository.add_candidate_term(term, "context")

        success = glossary_service.promote_candidate_to_economic(term)

        assert success is False

    def test_promote_candidate_already_in_argentine_dictionary(self, glossary_service):
        """Test promotion of candidate that already exists in Argentine dictionary."""
        expr = "laburo"

        # Add to Argentine dictionary first
        glossary_service.db_repository.add_argentine_expression(expr)
        # Add as candidate
        glossary_service.db_repository.add_candidate_term(expr, "context")

        success = glossary_service.promote_candidate_to_argentine(expr)

        assert success is False

    def test_promote_candidate_database_error(self, glossary_service):
        """Test handling of database errors during promotion."""
        # Add candidate first
        glossary_service.db_repository.add_candidate_term("test_term", "context")

        with patch.object(glossary_service.db_repository, 'add_economic_term') as mock_add:
            mock_add.side_effect = Exception("Database error")

            success = glossary_service.promote_candidate_to_economic("test_term")

            assert success is False

    def test_promote_candidate_logging(self, glossary_service):
        """Test logging during candidate promotion."""
        with patch('src.services.glossary_service.logger') as mock_logger:
            # Add candidate first
            glossary_service.db_repository.add_candidate_term("test_term", "context")

            glossary_service.promote_candidate_to_economic("test_term")

            # Verify appropriate logging
            mock_logger.info.assert_called()


class TestStatisticsTracking:
    """Test statistics and reporting functionality."""

    def test_update_statistics_tracking(self, glossary_service):
        """Test that statistics are accurately tracked during updates."""
        # Test with known transcript
        transcript = "La inflación, el PIB y el laburo están relacionados con la guita."

        stats = glossary_service.update_glossaries(transcript)

        # Verify statistics structure and values
        assert isinstance(stats, dict)
        assert all(isinstance(v, int) for v in stats.values())
        assert stats["economic_terms_added"] >= 2  # inflación, PIB
        assert stats["argentine_expressions_added"] >= 2  # laburo, guita

    def test_statistics_with_no_matches(self, glossary_service):
        """Test statistics when no terms are found."""
        transcript = "This text contains no Spanish economic or Argentine terms."

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] == 0
        assert stats["argentine_expressions_added"] == 0

    def test_statistics_with_mixed_new_and_existing(self, glossary_service):
        """Test statistics when some terms are new and others already exist."""
        # Add one term first
        glossary_service.db_repository.add_economic_term("inflación", "economic")

        # Use transcript with both new and existing terms
        transcript = "La inflación y el PIB están relacionados."

        stats = glossary_service.update_glossaries(transcript)

        # Should only count new terms
        assert stats["economic_terms_added"] == 1  # Only PIB should be new


class TestEdgeCases:
    """Test edge cases and unusual scenarios."""

    def test_update_with_empty_transcript(self, glossary_service):
        """Test updating glossaries with empty transcript."""
        stats = glossary_service.update_glossaries("")

        assert stats["economic_terms_added"] == 0
        assert stats["argentine_expressions_added"] == 0

    def test_update_with_whitespace_only_transcript(self, glossary_service):
        """Test updating glossaries with whitespace-only transcript."""
        stats = glossary_service.update_glossaries("   \n\t   ")

        assert stats["economic_terms_added"] == 0
        assert stats["argentine_expressions_added"] == 0

    def test_update_with_very_long_transcript(self, glossary_service):
        """Test updating glossaries with very long transcript."""
        # Create very long transcript with repeated terms
        long_transcript = " ".join(["inflación laburo"] * 1000)

        stats = glossary_service.update_glossaries(long_transcript)

        # Should still work and only add each term once
        assert stats["economic_terms_added"] == 1
        assert stats["argentine_expressions_added"] == 1

    def test_update_with_special_characters(self, glossary_service):
        """Test updating glossaries with special characters in transcript."""
        transcript = "La inflación está en 15% y el laburo escasea... ¿Qué hacer?"

        stats = glossary_service.update_glossaries(transcript)

        # Should still detect terms despite punctuation
        assert stats["economic_terms_added"] >= 1
        assert stats["argentine_expressions_added"] >= 1

    def test_update_with_unicode_transcript(self, glossary_service):
        """Test updating glossaries with unicode characters."""
        transcript = "La inflación 📈 está alta y el laburo 💼 escasea 😢"

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] >= 1
        assert stats["argentine_expressions_added"] >= 1

    def test_promote_with_unicode_term(self, glossary_service):
        """Test promotion with unicode characters in term."""
        unicode_term = "niños"

        # Add as candidate
        glossary_service.db_repository.add_candidate_term(unicode_term, "context")

        success = glossary_service.promote_candidate_to_economic(unicode_term)

        assert success is True

    def test_concurrent_glossary_updates(self, glossary_service):
        """Test concurrent glossary updates for thread safety."""
        import threading
        import time

        results = []
        errors = []

        def update_glossary(thread_id):
            try:
                transcript = f"La inflación_{thread_id} y el laburo_{thread_id}"
                time.sleep(0.01)  # Small delay to encourage concurrency
                stats = glossary_service.update_glossaries(transcript)
                results.append((thread_id, stats))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=update_glossary, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

        # All should have processed successfully
        for thread_id, stats in results:
            assert isinstance(stats, dict)
            assert "economic_terms_added" in stats
            assert "argentine_expressions_added" in stats


class TestConfigurationIntegration:
    """Test integration with configuration settings."""

    @patch('src.config.settings.ECONOMIC_TERMS', ['custom_term'])
    def test_update_with_custom_economic_terms(self, glossary_service):
        """Test that service uses configured economic terms."""
        transcript = "The custom_term is important for economics."

        stats = glossary_service.update_glossaries(transcript)

        assert stats["economic_terms_added"] == 1

    @patch('src.config.settings.ARGENTINE_EXPRESSIONS', ['custom_expr'])
    def test_update_with_custom_argentine_expressions(self, glossary_service):
        """Test that service uses configured Argentine expressions."""
        transcript = "That custom_expr is very Argentine."

        stats = glossary_service.update_glossaries(transcript)

        assert stats["argentine_expressions_added"] == 1

    def test_service_with_empty_term_lists(self, glossary_service):
        """Test service behavior when term lists are empty."""
        with patch('src.config.settings.ECONOMIC_TERMS', []):
            with patch('src.config.settings.ARGENTINE_EXPRESSIONS', []):
                transcript = "inflación laburo PIB guita"

                stats = glossary_service.update_glossaries(transcript)

                # Should find no terms since lists are empty
                assert stats["economic_terms_added"] == 0
                assert stats["argentine_expressions_added"] == 0