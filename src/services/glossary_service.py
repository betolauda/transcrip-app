import re
import logging
from typing import Dict, List, Tuple

from ..config.settings import settings
from ..repositories.database_repository import DatabaseRepository

logger = logging.getLogger(__name__)

class GlossaryService:
    """Service for managing economic glossary and Argentine dictionary"""

    def __init__(self, db_repository: DatabaseRepository = None):
        self.db_repository = db_repository or DatabaseRepository()

    def update_glossaries(self, transcript: str) -> Dict[str, int]:
        """
        Update both economic glossary and Argentine dictionary with terms found in transcript
        Returns: Dictionary with counts of new terms added
        """
        stats = {"economic_terms_added": 0, "argentine_expressions_added": 0}

        # Process economic terms
        for term in settings.ECONOMIC_TERMS:
            if re.search(rf"\b{term}\b", transcript, re.IGNORECASE):
                if self.db_repository.add_economic_term(term, "economic"):
                    stats["economic_terms_added"] += 1
                    logger.info(f"Added economic term: {term}")

        # Process Argentine expressions
        for expression in settings.ARGENTINE_EXPRESSIONS:
            if re.search(rf"\b{expression}\b", transcript, re.IGNORECASE):
                if self.db_repository.add_argentine_expression(expression):
                    stats["argentine_expressions_added"] += 1
                    logger.info(f"Added Argentine expression: {expression}")

        return stats

    def get_glossaries(self) -> Dict[str, List[Tuple]]:
        """
        Get all terms from both glossaries
        Returns: Dictionary with economic_glossary and argentine_dictionary lists
        """
        try:
            economic_terms = self.db_repository.get_economic_terms()
            argentine_expressions = self.db_repository.get_argentine_expressions()

            return {
                "economic_glossary": economic_terms,
                "argentine_dictionary": argentine_expressions
            }
        except Exception as e:
            logger.error(f"Error retrieving glossaries: {e}")
            return {"economic_glossary": [], "argentine_dictionary": []}

    def promote_candidate_to_economic(self, term: str) -> bool:
        """
        Promote a candidate term to economic glossary
        Returns: True if successful, False otherwise
        """
        try:
            # Check if candidate exists
            if not self.db_repository.candidate_term_exists(term):
                logger.warning(f"Candidate term '{term}' not found")
                return False

            # Add to economic glossary
            if self.db_repository.add_economic_term(term, "manual"):
                # Remove from candidates
                self.db_repository.remove_candidate_term(term)
                logger.info(f"Promoted candidate '{term}' to economic glossary")
                return True
            else:
                logger.warning(f"Term '{term}' already exists in economic glossary")
                return False

        except Exception as e:
            logger.error(f"Error promoting candidate '{term}' to economic glossary: {e}")
            return False

    def promote_candidate_to_argentine(self, term: str) -> bool:
        """
        Promote a candidate term to Argentine dictionary
        Returns: True if successful, False otherwise
        """
        try:
            # Check if candidate exists
            if not self.db_repository.candidate_term_exists(term):
                logger.warning(f"Candidate term '{term}' not found")
                return False

            # Add to Argentine dictionary
            if self.db_repository.add_argentine_expression(term):
                # Remove from candidates
                self.db_repository.remove_candidate_term(term)
                logger.info(f"Promoted candidate '{term}' to Argentine dictionary")
                return True
            else:
                logger.warning(f"Expression '{term}' already exists in Argentine dictionary")
                return False

        except Exception as e:
            logger.error(f"Error promoting candidate '{term}' to Argentine dictionary: {e}")
            return False