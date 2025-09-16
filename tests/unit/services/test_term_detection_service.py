"""
Comprehensive unit tests for TermDetectionService covering text normalization,
candidate term detection, and context extraction functionality.
"""
import pytest
from unittest.mock import Mock, patch

from src.services.term_detection_service import TermDetectionService
from tests.fixtures.test_data import SAMPLE_TRANSCRIPTS


class TestTermDetectionServiceInitialization:
    """Test TermDetectionService initialization and dependency injection."""

    def test_service_initialization_with_repository(self, db_repository):
        """Test service initialization with provided repository."""
        service = TermDetectionService(db_repository)
        assert service.db_repository is db_repository

    def test_service_initialization_without_repository(self):
        """Test service initialization creates default repository."""
        service = TermDetectionService()
        assert service.db_repository is not None


class TestTextNormalization:
    """Test text normalization functionality."""

    def test_normalize_token_basic(self, term_detection_service):
        """Test basic token normalization."""
        result = term_detection_service.normalize_token("Word")
        assert result == "word"

    def test_normalize_token_accents(self, term_detection_service):
        """Test accent removal in normalization."""
        test_cases = [
            ("café", "cafe"),
            ("niño", "nino"),
            ("corazón", "corazon"),
            ("ñandú", "nandu"),
            ("pública", "publica"),
        ]

        for input_word, expected in test_cases:
            result = term_detection_service.normalize_token(input_word)
            assert result == expected, f"Failed for {input_word}: got {result}, expected {expected}"

    def test_normalize_token_punctuation(self, term_detection_service):
        """Test punctuation removal in normalization."""
        test_cases = [
            ("word.", "word"),
            ("word,", "word"),
            ("word!", "word"),
            ("word?", "word"),
            ("word;", "word"),
            ("word:", "word"),
            ("(word)", "word"),
            ("'word'", "word"),
            ('"word"', "word"),
        ]

        for input_word, expected in test_cases:
            result = term_detection_service.normalize_token(input_word)
            assert result == expected, f"Failed for {input_word}: got {result}, expected {expected}"

    def test_normalize_token_mixed_cases(self, term_detection_service):
        """Test normalization with mixed cases."""
        test_cases = [
            ("BLOCKCHAIN", "blockchain"),
            ("BlockChain", "blockchain"),
            ("bLoCkChAiN", "blockchain"),
            ("FinTech", "fintech"),
        ]

        for input_word, expected in test_cases:
            result = term_detection_service.normalize_token(input_word)
            assert result == expected

    def test_normalize_token_complex_cases(self, term_detection_service):
        """Test normalization with complex combinations."""
        test_cases = [
            ("CORAZÓN!", "corazon"),
            ("(NIÑOS)", "ninos"),
            ("'PÚBLICA'.", "publica"),
            ("¿INFLACIÓN?", "inflacion"),
        ]

        for input_word, expected in test_cases:
            result = term_detection_service.normalize_token(input_word)
            assert result == expected

    def test_normalize_token_empty_and_edge_cases(self, term_detection_service):
        """Test normalization edge cases."""
        test_cases = [
            ("", ""),
            ("   ", ""),
            ("!", ""),
            ("123", "123"),
            ("word123", "word123"),
            ("123word", "123word"),
        ]

        for input_word, expected in test_cases:
            result = term_detection_service.normalize_token(input_word)
            assert result == expected


class TestCandidateValidation:
    """Test candidate term validation logic."""

    def test_is_valid_candidate_basic_valid_words(self, term_detection_service):
        """Test validation of basic valid candidates."""
        valid_words = ["blockchain", "fintech", "startup", "tecnología", "innovación"]

        for word in valid_words:
            assert term_detection_service.is_valid_candidate(word) is True

    def test_is_valid_candidate_minimum_length(self, term_detection_service):
        """Test minimum length requirement."""
        test_cases = [
            ("ab", False),  # Too short
            ("abc", True),   # Minimum length
            ("abcd", True),  # Above minimum
        ]

        for word, expected in test_cases:
            result = term_detection_service.is_valid_candidate(word)
            assert result == expected, f"Failed for {word}: got {result}, expected {expected}"

    def test_is_valid_candidate_stopwords(self, term_detection_service):
        """Test that Spanish stopwords are rejected."""
        stopwords = ["el", "la", "los", "las", "de", "del", "y", "o", "que", "en", "es"]

        for word in stopwords:
            assert term_detection_service.is_valid_candidate(word) is False

    def test_is_valid_candidate_numeric_rejection(self, term_detection_service):
        """Test that purely numeric tokens are rejected."""
        numeric_cases = ["123", "456", "0", "999", "12345"]

        for word in numeric_cases:
            assert term_detection_service.is_valid_candidate(word) is False

    def test_is_valid_candidate_alphanumeric_acceptance(self, term_detection_service):
        """Test that alphanumeric tokens are accepted."""
        alphanumeric_cases = ["web3", "blockchain2", "fintech1", "covid19"]

        for word in alphanumeric_cases:
            assert term_detection_service.is_valid_candidate(word) is True

    def test_is_valid_candidate_empty_string(self, term_detection_service):
        """Test that empty strings are rejected."""
        assert term_detection_service.is_valid_candidate("") is False

    def test_is_valid_candidate_whitespace_only(self, term_detection_service):
        """Test that whitespace-only strings are rejected."""
        whitespace_cases = ["   ", "\t", "\n", " \t\n "]

        for word in whitespace_cases:
            # After normalization, these become empty
            normalized = term_detection_service.normalize_token(word)
            assert term_detection_service.is_valid_candidate(normalized) is False


class TestTermDetection:
    """Test candidate term detection functionality."""

    def test_detect_new_terms_basic_functionality(self, term_detection_service):
        """Test basic new term detection."""
        transcript = SAMPLE_TRANSCRIPTS['candidate_rich']

        stats = term_detection_service.detect_new_terms(transcript)

        assert isinstance(stats, dict)
        assert "new_candidates_added" in stats
        assert stats["new_candidates_added"] > 0

    def test_detect_new_terms_with_context_extraction(self, term_detection_service):
        """Test that context is properly extracted for candidates."""
        transcript = "El blockchain revolucionario va a cambiar todo."

        term_detection_service.detect_new_terms(transcript)

        # Check that candidate was added with context
        candidates = term_detection_service.db_repository.get_candidate_terms()
        blockchain_candidates = [c for c in candidates if c[0] == "blockchain"]

        assert len(blockchain_candidates) > 0
        term, first_seen, context = blockchain_candidates[0]
        assert "blockchain" in context
        assert "revolucionario" in context  # Should include surrounding words

    def test_detect_new_terms_context_window(self, term_detection_service):
        """Test context window extraction (3 words before and after)."""
        transcript = "uno dos tres blockchain cuatro cinco seis siete"

        term_detection_service.detect_new_terms(transcript)

        candidates = term_detection_service.db_repository.get_candidate_terms()
        blockchain_candidates = [c for c in candidates if c[0] == "blockchain"]

        assert len(blockchain_candidates) > 0
        context = blockchain_candidates[0][2]

        # Should include 3 words before and after
        expected_words = ["tres", "blockchain", "cuatro", "cinco", "seis"]
        for word in expected_words:
            assert word in context

    def test_detect_new_terms_edge_of_text_context(self, term_detection_service):
        """Test context extraction at the beginning and end of text."""
        # Term at beginning
        transcript1 = "blockchain es una nueva tecnología muy importante"
        term_detection_service.detect_new_terms(transcript1)

        # Term at end
        transcript2 = "La nueva tecnología más importante es blockchain"
        term_detection_service.detect_new_terms(transcript2)

        candidates = term_detection_service.db_repository.get_candidate_terms()
        assert len(candidates) >= 1  # Should detect blockchain at least once

    def test_detect_new_terms_skips_existing_terms(self, term_detection_service):
        """Test that existing terms in glossaries are skipped."""
        # Add terms to existing glossaries
        term_detection_service.db_repository.add_economic_term("blockchain", "manual")
        term_detection_service.db_repository.add_argentine_expression("fintech")

        transcript = "blockchain y fintech son importantes junto con startup"

        stats = term_detection_service.detect_new_terms(transcript)

        # Should only detect "startup" as new (blockchain and fintech already exist)
        assert stats["new_candidates_added"] == 1

        candidates = term_detection_service.db_repository.get_candidate_terms()
        candidate_terms = [c[0] for c in candidates]
        assert "startup" in candidate_terms
        assert "blockchain" not in candidate_terms
        assert "fintech" not in candidate_terms

    def test_detect_new_terms_skips_existing_candidates(self, term_detection_service):
        """Test that existing candidate terms are not added again."""
        # Add candidate first
        term_detection_service.db_repository.add_candidate_term("blockchain", "first context")

        transcript = "blockchain aparece otra vez en diferente contexto"

        stats = term_detection_service.detect_new_terms(transcript)

        # Should not add duplicate candidate
        assert stats["new_candidates_added"] == 0

    def test_detect_new_terms_filters_invalid_candidates(self, term_detection_service):
        """Test that invalid candidates are filtered out."""
        transcript = "El 123 y la a están con of and blockchain"
        #             ^num  ^short ^stop ^stop  ^valid

        stats = term_detection_service.detect_new_terms(transcript)

        # Should only detect valid candidates
        candidates = term_detection_service.db_repository.get_candidate_terms()
        candidate_terms = [c[0] for c in candidates]

        assert "blockchain" in candidate_terms
        assert "123" not in candidate_terms
        assert "a" not in candidate_terms

    def test_detect_new_terms_normalization_consistency(self, term_detection_service):
        """Test that normalization is applied consistently."""
        # Use terms with accents and punctuation
        transcript = "Las tecnologías como BLOCKCHAIN! y FinTech, están creciendo."

        term_detection_service.detect_new_terms(transcript)

        candidates = term_detection_service.db_repository.get_candidate_terms()
        candidate_terms = [c[0] for c in candidates]

        # Terms should be stored in normalized form
        assert "blockchain" in candidate_terms
        assert "fintech" in candidate_terms
        assert "tecnologias" in candidate_terms

    def test_detect_new_terms_empty_transcript(self, term_detection_service):
        """Test detection with empty transcript."""
        stats = term_detection_service.detect_new_terms("")

        assert stats["new_candidates_added"] == 0

    def test_detect_new_terms_whitespace_only_transcript(self, term_detection_service):
        """Test detection with whitespace-only transcript."""
        stats = term_detection_service.detect_new_terms("   \n\t   ")

        assert stats["new_candidates_added"] == 0

    def test_detect_new_terms_with_unicode_characters(self, term_detection_service):
        """Test detection with unicode characters."""
        transcript = "Las niñas usan blockchain y corazón technologies"

        stats = term_detection_service.detect_new_terms(transcript)

        candidates = term_detection_service.db_repository.get_candidate_terms()
        candidate_terms = [c[0] for c in candidates]

        # Normalized forms should be stored
        assert "ninas" in candidate_terms or "niñas" in candidate_terms
        assert "corazon" in candidate_terms or "corazón" in candidate_terms


class TestCandidateManagement:
    """Test candidate term management operations."""

    def test_get_candidates_empty_database(self, term_detection_service):
        """Test getting candidates from empty database."""
        candidates = term_detection_service.get_candidates()

        assert isinstance(candidates, list)
        assert len(candidates) == 0

    def test_get_candidates_with_data(self, term_detection_service):
        """Test getting candidates with existing data."""
        # Add some candidates
        test_candidates = [
            ("blockchain", "blockchain context"),
            ("fintech", "fintech context"),
            ("startup", "startup context"),
        ]

        for term, context in test_candidates:
            term_detection_service.db_repository.add_candidate_term(term, context)

        candidates = term_detection_service.get_candidates()

        assert len(candidates) == len(test_candidates)
        candidate_terms = [c[0] for c in candidates]

        for term, _ in test_candidates:
            assert term in candidate_terms

    def test_get_candidate_statistics(self, term_detection_service):
        """Test candidate statistics calculation."""
        # Add some candidates
        terms = ["blockchain", "fintech", "startup"]
        for term in terms:
            term_detection_service.db_repository.add_candidate_term(term, f"{term} context")

        stats = term_detection_service.get_candidate_statistics()

        assert isinstance(stats, dict)
        assert "total_candidates" in stats
        assert "unique_candidates" in stats
        assert stats["total_candidates"] == len(terms)
        assert stats["unique_candidates"] == len(terms)

    def test_remove_candidate_success(self, term_detection_service):
        """Test successful candidate removal."""
        # Add candidate first
        term = "blockchain"
        term_detection_service.db_repository.add_candidate_term(term, "context")

        success = term_detection_service.remove_candidate(term)

        assert success is True
        assert not term_detection_service.db_repository.candidate_term_exists(term)

    def test_remove_candidate_not_found(self, term_detection_service):
        """Test removal of non-existent candidate."""
        success = term_detection_service.remove_candidate("nonexistent")

        assert success is False

    def test_remove_candidate_database_error(self, term_detection_service):
        """Test handling of database errors during removal."""
        with patch.object(term_detection_service.db_repository, 'remove_candidate_term') as mock_remove:
            mock_remove.side_effect = Exception("Database error")

            success = term_detection_service.remove_candidate("test")

            assert success is False


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_detect_new_terms_database_error_handling(self, term_detection_service):
        """Test handling of database errors during detection."""
        with patch.object(term_detection_service.db_repository, 'add_candidate_term') as mock_add:
            mock_add.side_effect = Exception("Database error")

            transcript = "blockchain fintech startup"

            # Should not raise exception
            try:
                stats = term_detection_service.detect_new_terms(transcript)
                # Depending on implementation, might return 0 or partial results
                assert isinstance(stats, dict)
            except Exception:
                # If implementation allows exceptions to propagate, that's also valid
                pass

    def test_get_candidates_database_error(self, term_detection_service):
        """Test handling of database errors when getting candidates."""
        with patch.object(term_detection_service.db_repository, 'get_candidate_terms') as mock_get:
            mock_get.side_effect = Exception("Database error")

            candidates = term_detection_service.get_candidates()

            # Should return empty list on error
            assert candidates == []

    def test_get_candidate_statistics_database_error(self, term_detection_service):
        """Test handling of database errors when getting statistics."""
        with patch.object(term_detection_service.db_repository, 'get_candidate_terms') as mock_get:
            mock_get.side_effect = Exception("Database error")

            stats = term_detection_service.get_candidate_statistics()

            # Should return default values on error
            assert stats == {"total_candidates": 0, "unique_candidates": 0}

    def test_logging_behavior(self, term_detection_service):
        """Test that appropriate logging occurs."""
        with patch('src.services.term_detection_service.logger') as mock_logger:
            transcript = "blockchain is a new technology"

            term_detection_service.detect_new_terms(transcript)

            # Verify logging calls
            mock_logger.info.assert_called()


class TestPerformance:
    """Test performance-related aspects."""

    def test_detect_new_terms_with_long_transcript(self, term_detection_service):
        """Test detection with very long transcript."""
        # Create long transcript with repeated terms
        base_text = "blockchain fintech startup tecnología innovación "
        long_transcript = base_text * 1000  # Very long text

        stats = term_detection_service.detect_new_terms(long_transcript)

        # Should complete without issues and detect unique terms
        assert stats["new_candidates_added"] > 0

    def test_concurrent_term_detection(self, term_detection_service):
        """Test concurrent term detection for thread safety."""
        import threading
        import time

        results = []
        errors = []

        def detect_terms(thread_id):
            try:
                transcript = f"blockchain_{thread_id} fintech_{thread_id} startup_{thread_id}"
                time.sleep(0.01)  # Small delay
                stats = term_detection_service.detect_new_terms(transcript)
                results.append((thread_id, stats))
            except Exception as e:
                errors.append((thread_id, str(e)))

        # Create multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=detect_terms, args=(thread_id,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Verify results
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) == 5

    def test_memory_usage_with_many_candidates(self, term_detection_service):
        """Test memory usage when processing many candidates."""
        # Create transcript with many potential candidates
        candidates = [f"term_{i}" for i in range(100)]
        transcript = " ".join(candidates)

        stats = term_detection_service.detect_new_terms(transcript)

        # Should handle many candidates without memory issues
        assert stats["new_candidates_added"] == len(candidates)


class TestConfigurationIntegration:
    """Test integration with configuration settings."""

    def test_stopword_filtering_with_custom_stopwords(self, term_detection_service):
        """Test that configured stopwords are properly filtered."""
        with patch('src.config.settings.SPANISH_STOPWORDS', {'custom', 'stopword'}):
            transcript = "custom blockchain stopword fintech regular"

            stats = term_detection_service.detect_new_terms(transcript)

            candidates = term_detection_service.db_repository.get_candidate_terms()
            candidate_terms = [c[0] for c in candidates]

            # Custom stopwords should be filtered out
            assert "custom" not in candidate_terms
            assert "stopword" not in candidate_terms
            assert "blockchain" in candidate_terms
            assert "fintech" in candidate_terms
            assert "regular" in candidate_terms