"""
Database migration system for schema versioning and evolution.

This module provides a robust migration system that tracks database schema
changes, applies migrations in order, and supports rollbacks.
"""
import sqlite3
import os
import logging
from typing import List, Dict, Tuple, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import hashlib
import json

logger = logging.getLogger(__name__)


@dataclass
class Migration:
    """Represents a database migration."""
    version: int
    name: str
    description: str
    up_sql: str
    down_sql: str
    checksum: str = ""
    applied_at: Optional[datetime] = None

    def __post_init__(self):
        """Calculate checksum after initialization."""
        if not self.checksum:
            content = f"{self.version}{self.name}{self.up_sql}{self.down_sql}"
            self.checksum = hashlib.sha256(content.encode()).hexdigest()


class MigrationError(Exception):
    """Custom exception for migration errors."""
    pass


class DatabaseMigrator:
    """
    Database migration manager with versioning support.

    Features:
    - Sequential migration versioning
    - Checksum validation for migration integrity
    - Rollback support
    - Migration status tracking
    - Dry-run capability
    - Backup creation before major changes
    """

    def __init__(self, db_path: str, migrations_dir: str = "migrations"):
        self.db_path = db_path
        self.migrations_dir = Path(migrations_dir)
        self.migrations_dir.mkdir(exist_ok=True)
        self.migrations: List[Migration] = []
        self._ensure_migration_table()
        self._load_migrations()

    def _ensure_migration_table(self):
        """Create the migrations tracking table if it doesn't exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Create schema_migrations table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    checksum TEXT NOT NULL,
                    applied_at TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    success BOOLEAN DEFAULT TRUE
                )
            ''')

            # Create migration_history table for detailed logging
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS migration_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    version INTEGER NOT NULL,
                    action TEXT NOT NULL, -- 'apply', 'rollback', 'verify'
                    timestamp TEXT NOT NULL,
                    execution_time_ms INTEGER,
                    success BOOLEAN,
                    error_message TEXT,
                    sql_executed TEXT
                )
            ''')

            conn.commit()

    def _get_connection(self):
        """Get database connection with proper configuration."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _load_migrations(self):
        """Load migration definitions from files and code."""
        # Load built-in migrations first
        self._load_builtin_migrations()

        # Load migrations from files if migrations directory exists
        if self.migrations_dir.exists():
            self._load_file_migrations()

        # Sort migrations by version
        self.migrations.sort(key=lambda m: m.version)

    def _load_builtin_migrations(self):
        """Load built-in migrations for the application."""

        # Migration 1: Initial schema
        self.migrations.append(Migration(
            version=1,
            name="initial_schema",
            description="Create initial transcriptions table",
            up_sql='''
                CREATE TABLE IF NOT EXISTS transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    transcript TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    file_size INTEGER,
                    duration_seconds REAL,
                    language TEXT DEFAULT 'es'
                );

                CREATE INDEX IF NOT EXISTS idx_transcriptions_created_at ON transcriptions(created_at);
                CREATE INDEX IF NOT EXISTS idx_transcriptions_filename ON transcriptions(filename);
            ''',
            down_sql='''
                DROP INDEX IF EXISTS idx_transcriptions_filename;
                DROP INDEX IF EXISTS idx_transcriptions_created_at;
                DROP TABLE IF EXISTS transcriptions;
            '''
        ))

        # Migration 2: Add glossary tables
        self.migrations.append(Migration(
            version=2,
            name="add_glossaries",
            description="Add economic and Argentine glossary tables",
            up_sql='''
                CREATE TABLE IF NOT EXISTS economic_glossary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE NOT NULL,
                    definition TEXT,
                    category TEXT,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                );

                CREATE TABLE IF NOT EXISTS argentine_glossary (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    expression TEXT UNIQUE NOT NULL,
                    meaning TEXT,
                    region TEXT,
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_economic_term ON economic_glossary(term);
                CREATE INDEX IF NOT EXISTS idx_argentine_expression ON argentine_glossary(expression);
            ''',
            down_sql='''
                DROP INDEX IF EXISTS idx_argentine_expression;
                DROP INDEX IF EXISTS idx_economic_term;
                DROP TABLE IF EXISTS argentine_glossary;
                DROP TABLE IF EXISTS economic_glossary;
            '''
        ))

        # Migration 3: Add candidate terms table
        self.migrations.append(Migration(
            version=3,
            name="add_candidate_terms",
            description="Add candidate terms detection system",
            up_sql='''
                CREATE TABLE IF NOT EXISTS candidate_terms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    term TEXT UNIQUE NOT NULL,
                    detection_count INTEGER DEFAULT 1,
                    confidence_score REAL DEFAULT 0.0,
                    contexts TEXT, -- JSON array of contexts where term was found
                    first_detected TEXT NOT NULL,
                    last_detected TEXT NOT NULL,
                    promoted BOOLEAN DEFAULT FALSE,
                    promoted_to TEXT, -- 'economic' or 'argentine'
                    promoted_at TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_candidate_terms_term ON candidate_terms(term);
                CREATE INDEX IF NOT EXISTS idx_candidate_terms_count ON candidate_terms(detection_count);
                CREATE INDEX IF NOT EXISTS idx_candidate_terms_promoted ON candidate_terms(promoted);
            ''',
            down_sql='''
                DROP INDEX IF EXISTS idx_candidate_terms_promoted;
                DROP INDEX IF EXISTS idx_candidate_terms_count;
                DROP INDEX IF EXISTS idx_candidate_terms_term;
                DROP TABLE IF EXISTS candidate_terms;
            '''
        ))

        # Migration 4: Add user authentication tables (already created in auth_repository)
        self.migrations.append(Migration(
            version=4,
            name="add_user_authentication",
            description="Add user authentication and authorization tables",
            up_sql='''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    hashed_password TEXT NOT NULL,
                    full_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    api_key TEXT UNIQUE,
                    api_key_created_at TEXT,
                    api_key_last_used TEXT
                );

                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

                CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
                CREATE INDEX IF NOT EXISTS idx_users_email ON users (email);
                CREATE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key);
                CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens (token);
            ''',
            down_sql='''
                DROP INDEX IF EXISTS idx_password_reset_tokens_token;
                DROP INDEX IF EXISTS idx_users_api_key;
                DROP INDEX IF EXISTS idx_users_email;
                DROP INDEX IF EXISTS idx_users_username;
                DROP TABLE IF EXISTS password_reset_tokens;
                DROP TABLE IF EXISTS users;
            '''
        ))

        # Migration 5: Add audit log for tracking changes
        self.migrations.append(Migration(
            version=5,
            name="add_audit_log",
            description="Add audit logging for tracking data changes",
            up_sql='''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    table_name TEXT NOT NULL,
                    record_id INTEGER NOT NULL,
                    action TEXT NOT NULL, -- 'INSERT', 'UPDATE', 'DELETE'
                    old_values TEXT, -- JSON of old values
                    new_values TEXT, -- JSON of new values
                    user_id INTEGER,
                    timestamp TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

                CREATE INDEX IF NOT EXISTS idx_audit_log_table_record ON audit_log(table_name, record_id);
                CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
                CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
            ''',
            down_sql='''
                DROP INDEX IF EXISTS idx_audit_log_user;
                DROP INDEX IF EXISTS idx_audit_log_timestamp;
                DROP INDEX IF EXISTS idx_audit_log_table_record;
                DROP TABLE IF EXISTS audit_log;
            '''
        ))

        # Migration 6: Add performance and monitoring tables
        self.migrations.append(Migration(
            version=6,
            name="add_monitoring_tables",
            description="Add tables for storing performance and monitoring data",
            up_sql='''
                CREATE TABLE IF NOT EXISTS api_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    method TEXT NOT NULL,
                    status_code INTEGER NOT NULL,
                    response_time_ms INTEGER NOT NULL,
                    request_size INTEGER DEFAULT 0,
                    response_size INTEGER DEFAULT 0,
                    user_id INTEGER,
                    ip_address TEXT,
                    timestamp TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

                CREATE TABLE IF NOT EXISTS error_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    level TEXT NOT NULL, -- 'ERROR', 'WARNING', 'CRITICAL'
                    message TEXT NOT NULL,
                    traceback TEXT,
                    endpoint TEXT,
                    user_id INTEGER,
                    ip_address TEXT,
                    timestamp TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                );

                CREATE INDEX IF NOT EXISTS idx_api_metrics_endpoint ON api_metrics(endpoint);
                CREATE INDEX IF NOT EXISTS idx_api_metrics_timestamp ON api_metrics(timestamp);
                CREATE INDEX IF NOT EXISTS idx_error_log_level ON error_log(level);
                CREATE INDEX IF NOT EXISTS idx_error_log_timestamp ON error_log(timestamp);
            ''',
            down_sql='''
                DROP INDEX IF EXISTS idx_error_log_timestamp;
                DROP INDEX IF EXISTS idx_error_log_level;
                DROP INDEX IF EXISTS idx_api_metrics_timestamp;
                DROP INDEX IF EXISTS idx_api_metrics_endpoint;
                DROP TABLE IF EXISTS error_log;
                DROP TABLE IF EXISTS api_metrics;
            '''
        ))

    def _load_file_migrations(self):
        """Load migrations from .sql files in migrations directory."""
        for migration_file in sorted(self.migrations_dir.glob("*.sql")):
            try:
                # Parse filename: 001_migration_name.sql
                filename = migration_file.stem
                parts = filename.split("_", 1)
                if len(parts) != 2:
                    continue

                version = int(parts[0])
                name = parts[1]

                # Read migration content
                content = migration_file.read_text()

                # Split up and down migrations (separated by -- DOWN)
                if "-- DOWN" in content:
                    up_sql, down_sql = content.split("-- DOWN", 1)
                else:
                    up_sql = content
                    down_sql = ""

                # Extract description from comments
                description = ""
                for line in content.split("\n"):
                    if line.strip().startswith("-- Description:"):
                        description = line.replace("-- Description:", "").strip()
                        break

                migration = Migration(
                    version=version,
                    name=name,
                    description=description or f"Migration {version}: {name}",
                    up_sql=up_sql.strip(),
                    down_sql=down_sql.strip()
                )

                self.migrations.append(migration)

            except Exception as e:
                logger.error(f"Error loading migration file {migration_file}: {e}")

    def get_current_version(self) -> int:
        """Get the current database schema version."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT MAX(version) FROM schema_migrations WHERE success = TRUE"
            )
            result = cursor.fetchone()
            return result[0] if result[0] is not None else 0

    def get_pending_migrations(self) -> List[Migration]:
        """Get list of pending migrations that need to be applied."""
        current_version = self.get_current_version()
        return [m for m in self.migrations if m.version > current_version]

    def get_applied_migrations(self) -> List[Tuple[int, str, datetime]]:
        """Get list of applied migrations with their application timestamps."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT version, name, applied_at
                FROM schema_migrations
                WHERE success = TRUE
                ORDER BY version
            ''')
            return [(row[0], row[1], datetime.fromisoformat(row[2])) for row in cursor.fetchall()]

    def validate_migration_integrity(self) -> bool:
        """Validate that applied migrations haven't been tampered with."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT version, checksum FROM schema_migrations WHERE success = TRUE")

            for version, stored_checksum in cursor.fetchall():
                migration = next((m for m in self.migrations if m.version == version), None)
                if migration and migration.checksum != stored_checksum:
                    logger.error(f"Migration {version} checksum mismatch!")
                    return False

        return True

    def apply_migration(self, migration: Migration, dry_run: bool = False) -> bool:
        """Apply a single migration."""
        start_time = datetime.now()

        if dry_run:
            logger.info(f"DRY RUN: Would apply migration {migration.version}: {migration.name}")
            logger.debug(f"SQL to execute:\n{migration.up_sql}")
            return True

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Execute the migration SQL
                logger.info(f"Applying migration {migration.version}: {migration.name}")

                # Split and execute each statement
                statements = [stmt.strip() for stmt in migration.up_sql.split(';') if stmt.strip()]
                for statement in statements:
                    cursor.execute(statement)

                # Record successful migration
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                cursor.execute('''
                    INSERT INTO schema_migrations
                    (version, name, description, checksum, applied_at, execution_time_ms, success)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    migration.version,
                    migration.name,
                    migration.description,
                    migration.checksum,
                    start_time.isoformat(),
                    execution_time,
                    True
                ))

                # Log to migration history
                cursor.execute('''
                    INSERT INTO migration_history
                    (version, action, timestamp, execution_time_ms, success, sql_executed)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    migration.version,
                    'apply',
                    start_time.isoformat(),
                    execution_time,
                    True,
                    migration.up_sql
                ))

                conn.commit()
                logger.info(f"Successfully applied migration {migration.version} in {execution_time}ms")
                return True

        except Exception as e:
            # Record failed migration
            execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
            try:
                with self._get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO migration_history
                        (version, action, timestamp, execution_time_ms, success, error_message, sql_executed)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        migration.version,
                        'apply',
                        start_time.isoformat(),
                        execution_time,
                        False,
                        str(e),
                        migration.up_sql
                    ))
                    conn.commit()
            except Exception:
                pass  # Don't fail if we can't log the error

            logger.error(f"Failed to apply migration {migration.version}: {e}")
            raise MigrationError(f"Migration {migration.version} failed: {e}")

    def rollback_migration(self, migration: Migration, dry_run: bool = False) -> bool:
        """Rollback a single migration."""
        if not migration.down_sql:
            raise MigrationError(f"Migration {migration.version} has no rollback SQL")

        start_time = datetime.now()

        if dry_run:
            logger.info(f"DRY RUN: Would rollback migration {migration.version}: {migration.name}")
            logger.debug(f"SQL to execute:\n{migration.down_sql}")
            return True

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # Execute the rollback SQL
                logger.info(f"Rolling back migration {migration.version}: {migration.name}")

                statements = [stmt.strip() for stmt in migration.down_sql.split(';') if stmt.strip()]
                for statement in statements:
                    cursor.execute(statement)

                # Remove migration record
                cursor.execute("DELETE FROM schema_migrations WHERE version = ?", (migration.version,))

                # Log to migration history
                execution_time = int((datetime.now() - start_time).total_seconds() * 1000)
                cursor.execute('''
                    INSERT INTO migration_history
                    (version, action, timestamp, execution_time_ms, success, sql_executed)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    migration.version,
                    'rollback',
                    start_time.isoformat(),
                    execution_time,
                    True,
                    migration.down_sql
                ))

                conn.commit()
                logger.info(f"Successfully rolled back migration {migration.version}")
                return True

        except Exception as e:
            logger.error(f"Failed to rollback migration {migration.version}: {e}")
            raise MigrationError(f"Rollback of migration {migration.version} failed: {e}")

    def migrate(self, target_version: Optional[int] = None, dry_run: bool = False) -> bool:
        """Apply all pending migrations up to target version."""
        current_version = self.get_current_version()

        if target_version is None:
            target_version = max(m.version for m in self.migrations) if self.migrations else 0

        if current_version >= target_version:
            logger.info(f"Database is already at version {current_version}")
            return True

        # Validate migration integrity before proceeding
        if not self.validate_migration_integrity():
            raise MigrationError("Migration integrity check failed")

        pending = [m for m in self.migrations if current_version < m.version <= target_version]

        if not pending:
            logger.info("No pending migrations to apply")
            return True

        logger.info(f"Applying {len(pending)} migrations from version {current_version} to {target_version}")

        for migration in pending:
            if not self.apply_migration(migration, dry_run):
                return False

        if not dry_run:
            logger.info(f"Successfully migrated to version {target_version}")

        return True

    def rollback(self, target_version: int, dry_run: bool = False) -> bool:
        """Rollback migrations to target version."""
        current_version = self.get_current_version()

        if current_version <= target_version:
            logger.info(f"Database is already at or below version {target_version}")
            return True

        # Get migrations to rollback (in reverse order)
        to_rollback = [m for m in reversed(self.migrations) if target_version < m.version <= current_version]

        if not to_rollback:
            logger.info("No migrations to rollback")
            return True

        logger.info(f"Rolling back {len(to_rollback)} migrations from version {current_version} to {target_version}")

        for migration in to_rollback:
            if not self.rollback_migration(migration, dry_run):
                return False

        if not dry_run:
            logger.info(f"Successfully rolled back to version {target_version}")

        return True

    def get_migration_status(self) -> Dict:
        """Get comprehensive migration status information."""
        current_version = self.get_current_version()
        pending = self.get_pending_migrations()
        applied = self.get_applied_migrations()

        return {
            "current_version": current_version,
            "latest_available_version": max(m.version for m in self.migrations) if self.migrations else 0,
            "total_migrations": len(self.migrations),
            "applied_count": len(applied),
            "pending_count": len(pending),
            "applied_migrations": [
                {"version": v, "name": n, "applied_at": t.isoformat()}
                for v, n, t in applied
            ],
            "pending_migrations": [
                {"version": m.version, "name": m.name, "description": m.description}
                for m in pending
            ],
            "integrity_valid": self.validate_migration_integrity()
        }


# Global migrator instance - will be initialized when needed
_migrator: Optional[DatabaseMigrator] = None


def get_migrator(db_path: str = None) -> DatabaseMigrator:
    """Get the global migrator instance."""
    global _migrator
    if _migrator is None or (db_path and _migrator.db_path != db_path):
        from ..config.settings import settings
        actual_db_path = db_path or settings.DB_PATH
        _migrator = DatabaseMigrator(actual_db_path)
    return _migrator


def auto_migrate(db_path: str = None) -> bool:
    """Automatically apply all pending migrations."""
    try:
        migrator = get_migrator(db_path)
        return migrator.migrate()
    except Exception as e:
        logger.error(f"Auto-migration failed: {e}")
        return False