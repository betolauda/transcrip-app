import sqlite3
import logging
from contextlib import contextmanager
from typing import List, Optional, Tuple
from datetime import datetime

from ..config.settings import settings
from ..models.domain_models import Transcription, EconomicTerm, ArgentineTerm, CandidateTerm

logger = logging.getLogger(__name__)

class DatabaseRepository:
    """Repository for all database operations"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.DB_PATH
        self.init_db()

    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable dict-like access
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def init_db(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Transcriptions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)

            # Economic glossary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS economic_glossary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    first_seen TEXT NOT NULL
                )
            """)

            # Argentine dictionary table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS argentine_dictionary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expression TEXT UNIQUE NOT NULL,
                    first_seen TEXT NOT NULL
                )
            """)

            # Candidate terms table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS candidate_terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE NOT NULL,
                    first_seen TEXT NOT NULL,
                    context_snippet TEXT NOT NULL
                )
            """)

            # Add indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_economic_glossary_term ON economic_glossary(term)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_argentine_dictionary_expression ON argentine_dictionary(expression)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_candidate_terms_term ON candidate_terms(term)")

            conn.commit()

    # Transcription operations
    def save_transcription(self, filename: str, transcript: str) -> int:
        """Save a new transcription and return its ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transcriptions (filename, transcript, created_at)
                VALUES (?, ?, ?)
            """, (filename, transcript, datetime.utcnow().isoformat()))
            conn.commit()
            return cursor.lastrowid

    def get_transcription_by_id(self, transcription_id: int) -> Optional[Transcription]:
        """Get a transcription by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM transcriptions WHERE id = ?", (transcription_id,))
            row = cursor.fetchone()
            if row:
                return Transcription(
                    id=row['id'],
                    filename=row['filename'],
                    transcript=row['transcript'],
                    created_at=datetime.fromisoformat(row['created_at'])
                )
        return None

    # Economic glossary operations
    def add_economic_term(self, term: str, category: str = "economic") -> bool:
        """Add a term to economic glossary. Returns True if added, False if already exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO economic_glossary (term, category, first_seen)
                    VALUES (?, ?, ?)
                """, (term, category, datetime.utcnow().isoformat()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_economic_terms(self) -> List[Tuple[str, str, str]]:
        """Get all economic terms"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT term, category, first_seen FROM economic_glossary")
            return cursor.fetchall()

    def term_exists_in_economic_glossary(self, term: str) -> bool:
        """Check if term exists in economic glossary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM economic_glossary WHERE term = ?", (term,))
            return cursor.fetchone() is not None

    # Argentine dictionary operations
    def add_argentine_expression(self, expression: str) -> bool:
        """Add an expression to Argentine dictionary. Returns True if added, False if already exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO argentine_dictionary (expression, first_seen)
                    VALUES (?, ?)
                """, (expression, datetime.utcnow().isoformat()))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_argentine_expressions(self) -> List[Tuple[str, str]]:
        """Get all Argentine expressions"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT expression, first_seen FROM argentine_dictionary")
            return cursor.fetchall()

    def expression_exists_in_argentine_dictionary(self, expression: str) -> bool:
        """Check if expression exists in Argentine dictionary"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM argentine_dictionary WHERE expression = ?", (expression,))
            return cursor.fetchone() is not None

    # Candidate terms operations
    def add_candidate_term(self, term: str, context_snippet: str) -> bool:
        """Add a candidate term. Returns True if added, False if already exists."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO candidate_terms (term, first_seen, context_snippet)
                    VALUES (?, ?, ?)
                """, (term, datetime.utcnow().isoformat(), context_snippet))
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                return False

    def get_candidate_terms(self) -> List[Tuple[str, str, str]]:
        """Get all candidate terms"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT term, first_seen, context_snippet FROM candidate_terms")
            return cursor.fetchall()

    def candidate_term_exists(self, term: str) -> bool:
        """Check if candidate term exists"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM candidate_terms WHERE term = ?", (term,))
            return cursor.fetchone() is not None

    def remove_candidate_term(self, term: str) -> bool:
        """Remove a candidate term. Returns True if removed, False if not found."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM candidate_terms WHERE term = ?", (term,))
            conn.commit()
            return cursor.rowcount > 0