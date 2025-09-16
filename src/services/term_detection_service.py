import string
import unicodedata
import logging
from typing import List, Tuple, Dict

from ..config.settings import settings
from ..repositories.database_repository import DatabaseRepository

logger = logging.getLogger(__name__)

class TermDetectionService:
    """Service for detecting and managing candidate terms"""

    def __init__(self, db_repository: DatabaseRepository = None):
        self.db_repository = db_repository or DatabaseRepository()

    def normalize_token(self, token: str) -> str:
        """
        Normalize a token by removing accents, converting to lowercase, and stripping punctuation
        """
        token = token.lower().strip(string.punctuation)
        # Remove accents using Unicode normalization
        token = "".join(
            c for c in unicodedata.normalize("NFD", token)
            if unicodedata.category(c) != "Mn"
        )
        return token

    def is_valid_candidate(self, word: str) -> bool:
        """
        Check if a word is a valid candidate for term detection
        """
        # Must have content after normalization
        if not word:
            return False

        # Must be at least 3 characters
        if len(word) < 3:
            return False

        # Must not be a stopword
        if word in settings.SPANISH_STOPWORDS:
            return False

        # Must not be purely numeric
        if word.isdigit():
            return False

        return True

    def detect_new_terms(self, transcript: str) -> Dict[str, int]:
        """
        Detect new candidate terms in transcript and add them to the database
        Returns: Dictionary with statistics about new terms found
        """
        words = [self.normalize_token(w) for w in transcript.split()]
        new_candidates_count = 0

        for i, word in enumerate(words):
            if not self.is_valid_candidate(word):
                continue

            # Skip if already exists in any glossary
            if (self.db_repository.term_exists_in_economic_glossary(word) or
                self.db_repository.expression_exists_in_argentine_dictionary(word) or
                self.db_repository.candidate_term_exists(word)):
                continue

            # Extract context (3 words before and after)
            context_start = max(0, i - 3)
            context_end = min(len(words), i + 4)
            context = " ".join(words[context_start:context_end])

            # Add to candidate terms
            if self.db_repository.add_candidate_term(word, context):
                new_candidates_count += 1
                logger.info(f"New candidate term detected: '{word}' in context: '{context[:50]}...'")

        return {"new_candidates_added": new_candidates_count}

    def get_candidates(self) -> List[Tuple[str, str, str]]:
        """
        Get all candidate terms
        Returns: List of tuples (term, first_seen, context_snippet)
        """
        try:
            return self.db_repository.get_candidate_terms()
        except Exception as e:
            logger.error(f"Error retrieving candidate terms: {e}")
            return []

    def get_candidate_statistics(self) -> Dict[str, int]:
        """
        Get statistics about candidate terms
        Returns: Dictionary with candidate count and other metrics
        """
        try:
            candidates = self.get_candidates()
            return {
                "total_candidates": len(candidates),
                "unique_candidates": len(set(candidate[0] for candidate in candidates))
            }
        except Exception as e:
            logger.error(f"Error calculating candidate statistics: {e}")
            return {"total_candidates": 0, "unique_candidates": 0}

    def remove_candidate(self, term: str) -> bool:
        """
        Remove a candidate term (for cleanup or manual rejection)
        Returns: True if removed successfully
        """
        try:
            success = self.db_repository.remove_candidate_term(term)
            if success:
                logger.info(f"Removed candidate term: {term}")
            return success
        except Exception as e:
            logger.error(f"Error removing candidate term '{term}': {e}")
            return False