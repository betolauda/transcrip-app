"""
API endpoints for database management and migration operations.
"""
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse

from ..auth.dependencies import require_admin
from ..auth.models import User
from ..database.migrations import get_migrator, MigrationError

router = APIRouter(prefix="/database", tags=["Database Management"])


@router.get("/migration-status")
async def get_migration_status(
    current_user: User = Depends(require_admin)
):
    """Get current database migration status (admin only)."""
    try:
        migrator = get_migrator()
        status = migrator.get_migration_status()
        return status
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get migration status: {e}"
        )


@router.post("/migrate")
async def apply_migrations(
    target_version: Optional[int] = Query(None, description="Target version (latest if not specified)"),
    dry_run: bool = Query(False, description="Perform dry run without executing"),
    current_user: User = Depends(require_admin)
):
    """Apply pending database migrations (admin only)."""
    try:
        migrator = get_migrator()

        # Get current status
        status_before = migrator.get_migration_status()

        if status_before['pending_count'] == 0:
            return {
                "message": "Database is already up to date",
                "current_version": status_before['current_version'],
                "applied_migrations": 0
            }

        # Validate migration integrity before proceeding
        if not migrator.validate_migration_integrity():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Migration integrity check failed. Some applied migrations have been modified."
            )

        # Apply migrations
        success = migrator.migrate(target_version=target_version, dry_run=dry_run)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Migration failed"
            )

        # Get status after migration
        status_after = migrator.get_migration_status()

        return {
            "message": "Migrations applied successfully" if not dry_run else "Dry run completed successfully",
            "dry_run": dry_run,
            "version_before": status_before['current_version'],
            "version_after": status_after['current_version'],
            "applied_migrations": status_after['current_version'] - status_before['current_version']
        }

    except MigrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Migration error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to apply migrations: {e}"
        )


@router.post("/rollback")
async def rollback_migrations(
    target_version: int = Query(..., description="Target version to rollback to"),
    dry_run: bool = Query(False, description="Perform dry run without executing"),
    current_user: User = Depends(require_admin)
):
    """Rollback database to a specific version (admin only)."""
    try:
        migrator = get_migrator()

        # Get current status
        current_version = migrator.get_current_version()

        if target_version >= current_version:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Target version {target_version} must be lower than current version {current_version}"
            )

        # Perform rollback
        success = migrator.rollback(target_version, dry_run=dry_run)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Rollback failed"
            )

        return {
            "message": "Rollback completed successfully" if not dry_run else "Dry run completed successfully",
            "dry_run": dry_run,
            "version_before": current_version,
            "version_after": target_version,
            "rolled_back_migrations": current_version - target_version
        }

    except MigrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Rollback error: {e}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rollback migrations: {e}"
        )


@router.post("/verify-integrity")
async def verify_migration_integrity(
    current_user: User = Depends(require_admin)
):
    """Verify the integrity of applied migrations (admin only)."""
    try:
        migrator = get_migrator()

        is_valid = migrator.validate_migration_integrity()

        return {
            "integrity_valid": is_valid,
            "message": "All migrations are valid and unchanged" if is_valid else "Migration integrity check failed! Some applied migrations have been modified."
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify migration integrity: {e}"
        )


@router.get("/backup")
async def create_database_backup(
    current_user: User = Depends(require_admin)
):
    """Create a backup of the current database (admin only)."""
    try:
        import shutil
        import os
        from datetime import datetime
        from pathlib import Path

        migrator = get_migrator()
        db_path = migrator.db_path

        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)

        backup_filename = f"database_backup_{timestamp}.db"
        backup_path = backup_dir / backup_filename

        # Copy database file
        shutil.copy2(db_path, backup_path)

        # Get backup file size
        backup_size = os.path.getsize(backup_path)

        return {
            "message": "Database backup created successfully",
            "backup_path": str(backup_path),
            "backup_size_bytes": backup_size,
            "backup_size_mb": round(backup_size / (1024 * 1024), 2),
            "timestamp": timestamp
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create database backup: {e}"
        )


@router.get("/schema")
async def get_database_schema(
    current_user: User = Depends(require_admin)
):
    """Get current database schema information (admin only)."""
    try:
        migrator = get_migrator()

        with migrator._get_connection() as conn:
            cursor = conn.cursor()

            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            tables = [row[0] for row in cursor.fetchall()]

            schema_info = {}

            for table in tables:
                # Get table schema
                cursor.execute(f"PRAGMA table_info({table})")
                columns = []
                for row in cursor.fetchall():
                    columns.append({
                        "name": row[1],
                        "type": row[2],
                        "not_null": bool(row[3]),
                        "default_value": row[4],
                        "primary_key": bool(row[5])
                    })

                # Get indexes
                cursor.execute(f"PRAGMA index_list({table})")
                indexes = []
                for row in cursor.fetchall():
                    index_name = row[1]
                    cursor.execute(f"PRAGMA index_info({index_name})")
                    index_columns = [col_row[2] for col_row in cursor.fetchall()]
                    indexes.append({
                        "name": index_name,
                        "unique": bool(row[2]),
                        "columns": index_columns
                    })

                schema_info[table] = {
                    "columns": columns,
                    "indexes": indexes
                }

        return {
            "total_tables": len(tables),
            "tables": list(tables),
            "schema": schema_info
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database schema: {e}"
        )


@router.get("/statistics")
async def get_database_statistics(
    current_user: User = Depends(require_admin)
):
    """Get database usage statistics (admin only)."""
    try:
        migrator = get_migrator()

        with migrator._get_connection() as conn:
            cursor = conn.cursor()

            # Get database file size
            import os
            db_size = os.path.getsize(migrator.db_path)

            # Get table statistics
            table_stats = {}

            # Get all user tables (exclude sqlite system tables)
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
            """)
            tables = [row[0] for row in cursor.fetchall()]

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                row_count = cursor.fetchone()[0]
                table_stats[table] = {"row_count": row_count}

            # Get migration history summary
            cursor.execute("""
                SELECT
                    COUNT(*) as total_migrations,
                    COUNT(CASE WHEN success = 1 THEN 1 END) as successful_migrations,
                    COUNT(CASE WHEN success = 0 THEN 1 END) as failed_migrations,
                    AVG(execution_time_ms) as avg_execution_time
                FROM migration_history
            """)
            migration_stats = cursor.fetchone()

            return {
                "database_size_bytes": db_size,
                "database_size_mb": round(db_size / (1024 * 1024), 2),
                "total_tables": len(tables),
                "table_statistics": table_stats,
                "migration_statistics": {
                    "total_migrations": migration_stats[0] if migration_stats[0] else 0,
                    "successful_migrations": migration_stats[1] if migration_stats[1] else 0,
                    "failed_migrations": migration_stats[2] if migration_stats[2] else 0,
                    "average_execution_time_ms": round(migration_stats[3], 2) if migration_stats[3] else 0
                }
            }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get database statistics: {e}"
        )