"""
Database management commands for migrations and maintenance.
"""
import click
import logging
from typing import Optional
from .migrations import get_migrator, MigrationError

logger = logging.getLogger(__name__)


@click.group()
def db():
    """Database management commands."""
    pass


@db.command()
@click.option('--db-path', help='Database path (defaults to settings)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def migrate(db_path: Optional[str], dry_run: bool):
    """Apply all pending migrations."""
    try:
        migrator = get_migrator(db_path)

        if dry_run:
            click.echo("=== DRY RUN MODE ===")

        status = migrator.get_migration_status()
        current = status['current_version']
        latest = status['latest_available_version']
        pending = status['pending_count']

        click.echo(f"Current database version: {current}")
        click.echo(f"Latest available version: {latest}")
        click.echo(f"Pending migrations: {pending}")

        if pending == 0:
            click.echo("✅ Database is up to date!")
            return

        click.echo(f"\nApplying {pending} migrations...")

        if migrator.migrate(dry_run=dry_run):
            if not dry_run:
                click.echo(f"✅ Successfully migrated to version {latest}")
            else:
                click.echo("✅ Dry run completed successfully")
        else:
            click.echo("❌ Migration failed!")
            exit(1)

    except MigrationError as e:
        click.echo(f"❌ Migration error: {e}")
        exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        exit(1)


@db.command()
@click.argument('version', type=int)
@click.option('--db-path', help='Database path (defaults to settings)')
@click.option('--dry-run', is_flag=True, help='Show what would be done without executing')
def rollback(version: int, db_path: Optional[str], dry_run: bool):
    """Rollback to a specific migration version."""
    try:
        migrator = get_migrator(db_path)

        if dry_run:
            click.echo("=== DRY RUN MODE ===")

        current = migrator.get_current_version()
        click.echo(f"Current database version: {current}")
        click.echo(f"Target version: {version}")

        if version >= current:
            click.echo("❌ Target version must be lower than current version")
            return

        if migrator.rollback(version, dry_run=dry_run):
            if not dry_run:
                click.echo(f"✅ Successfully rolled back to version {version}")
            else:
                click.echo("✅ Dry run completed successfully")
        else:
            click.echo("❌ Rollback failed!")
            exit(1)

    except MigrationError as e:
        click.echo(f"❌ Rollback error: {e}")
        exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}")
        exit(1)


@db.command()
@click.option('--db-path', help='Database path (defaults to settings)')
def status(db_path: Optional[str]):
    """Show migration status."""
    try:
        migrator = get_migrator(db_path)
        status = migrator.get_migration_status()

        click.echo("=== Database Migration Status ===")
        click.echo(f"Current version: {status['current_version']}")
        click.echo(f"Latest available: {status['latest_available_version']}")
        click.echo(f"Total migrations: {status['total_migrations']}")
        click.echo(f"Applied: {status['applied_count']}")
        click.echo(f"Pending: {status['pending_count']}")
        click.echo(f"Integrity check: {'✅ PASSED' if status['integrity_valid'] else '❌ FAILED'}")

        if status['applied_count'] > 0:
            click.echo("\n=== Applied Migrations ===")
            for migration in status['applied_migrations']:
                click.echo(f"  {migration['version']:3d}: {migration['name']} ({migration['applied_at']})")

        if status['pending_count'] > 0:
            click.echo("\n=== Pending Migrations ===")
            for migration in status['pending_migrations']:
                click.echo(f"  {migration['version']:3d}: {migration['name']} - {migration['description']}")

    except Exception as e:
        click.echo(f"❌ Error getting status: {e}")
        exit(1)


@db.command()
@click.option('--db-path', help='Database path (defaults to settings)')
def verify(db_path: Optional[str]):
    """Verify migration integrity."""
    try:
        migrator = get_migrator(db_path)

        click.echo("Verifying migration integrity...")

        if migrator.validate_migration_integrity():
            click.echo("✅ All migrations are valid and unchanged")
        else:
            click.echo("❌ Migration integrity check failed!")
            click.echo("Some applied migrations have been modified!")
            exit(1)

    except Exception as e:
        click.echo(f"❌ Error during verification: {e}")
        exit(1)


@db.command()
@click.argument('name')
@click.option('--description', help='Migration description')
def create(name: str, description: Optional[str]):
    """Create a new migration file."""
    try:
        from pathlib import Path
        from datetime import datetime

        # Get next version number
        migrator = get_migrator()
        latest_version = max(m.version for m in migrator.migrations) if migrator.migrations else 0
        next_version = latest_version + 1

        # Create migrations directory if it doesn't exist
        migrations_dir = Path("migrations")
        migrations_dir.mkdir(exist_ok=True)

        # Generate filename
        filename = f"{next_version:03d}_{name}.sql"
        filepath = migrations_dir / filename

        # Generate migration template
        template = f"""-- Description: {description or f'Migration {next_version}: {name}'}
-- Created: {datetime.now().isoformat()}

-- UP Migration
-- Add your schema changes here



-- DOWN Migration
-- Add rollback changes here (remove what was added above)



"""

        filepath.write_text(template)

        click.echo(f"✅ Created migration file: {filepath}")
        click.echo("Edit the file to add your schema changes.")

    except Exception as e:
        click.echo(f"❌ Error creating migration: {e}")
        exit(1)


if __name__ == '__main__':
    db()