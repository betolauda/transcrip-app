"""
Authentication repository for user management and authentication operations.
"""
import sqlite3
from datetime import datetime
from typing import Optional, List
from contextlib import contextmanager

from ..auth.models import User, UserRole, UserStatus, APIKey
from ..auth.security import get_password_hash, verify_password


class AuthRepository:
    """Repository for authentication and user management operations."""

    def __init__(self, db_path: str = "data/transcriptions.db"):
        self.db_path = db_path
        self._init_auth_tables()

    def _init_auth_tables(self):
        """Initialize authentication-related tables."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Users table
            cursor.execute('''
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
                )
            ''')

            # Password reset tokens table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            ''')

            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_username ON users (username)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_api_key ON users (api_key)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_password_reset_tokens_token ON password_reset_tokens (token)')

            # Create default admin user if none exists
            cursor.execute('SELECT COUNT(*) FROM users WHERE role = ?', (UserRole.ADMIN,))
            admin_count = cursor.fetchone()[0]

            if admin_count == 0:
                self._create_default_admin(cursor)

    def _create_default_admin(self, cursor):
        """Create default admin user."""
        admin_password = get_password_hash("admin123")  # Default password
        cursor.execute('''
            INSERT INTO users (username, email, hashed_password, full_name, role, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            "admin",
            "admin@transcription.local",
            admin_password,
            "System Administrator",
            UserRole.ADMIN,
            UserStatus.ACTIVE,
            datetime.utcnow().isoformat()
        ))

    @contextmanager
    def get_connection(self):
        """Get database connection with context manager."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_user(self, username: str, email: str, password: str, full_name: str,
                   role: UserRole = UserRole.USER) -> Optional[User]:
        """Create a new user."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if username or email already exists
                cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (username, email))
                if cursor.fetchone():
                    return None

                hashed_password = get_password_hash(password)
                created_at = datetime.utcnow().isoformat()

                cursor.execute('''
                    INSERT INTO users (username, email, hashed_password, full_name, role, status, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (username, email, hashed_password, full_name, role, UserStatus.ACTIVE, created_at))

                user_id = cursor.lastrowid
                return self.get_user_by_id(user_id)

        except sqlite3.IntegrityError:
            return None

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            row = cursor.fetchone()

            if row:
                return self._row_to_user(row)
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
            row = cursor.fetchone()

            if row:
                return self._row_to_user(row)
            return None

    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
            row = cursor.fetchone()

            if row:
                return self._row_to_user(row)
            return None

    def get_user_by_api_key(self, api_key_hash: str) -> Optional[User]:
        """Get user by API key hash."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE api_key = ?', (api_key_hash,))
            row = cursor.fetchone()

            if row:
                return self._row_to_user(row)
            return None

    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """Authenticate user with username/email and password."""
        # Try username first, then email
        user = self.get_user_by_username(username)
        if not user:
            user = self.get_user_by_email(username)

        if user and verify_password(password, user.hashed_password):
            # Update last login
            self.update_last_login(user.id)
            return user

        return None

    def update_last_login(self, user_id: int):
        """Update user's last login timestamp."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET last_login = ? WHERE id = ?',
                (datetime.utcnow().isoformat(), user_id)
            )

    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user information."""
        if not kwargs:
            return self.get_user_by_id(user_id)

        # Build update query
        update_fields = []
        values = []

        for field, value in kwargs.items():
            if field in ['email', 'full_name', 'role', 'status']:
                update_fields.append(f"{field} = ?")
                values.append(value)

        if not update_fields:
            return self.get_user_by_id(user_id)

        values.append(user_id)
        query = f"UPDATE users SET {', '.join(update_fields)} WHERE id = ?"

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)

        return self.get_user_by_id(user_id)

    def change_password(self, user_id: int, new_password: str) -> bool:
        """Change user password."""
        hashed_password = get_password_hash(new_password)

        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET hashed_password = ? WHERE id = ?',
                (hashed_password, user_id)
            )
            return cursor.rowcount > 0

    def set_api_key(self, user_id: int, api_key_hash: str) -> bool:
        """Set API key for user."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET api_key = ?, api_key_created_at = ? WHERE id = ?',
                (api_key_hash, datetime.utcnow().isoformat(), user_id)
            )
            return cursor.rowcount > 0

    def update_api_key_usage(self, user_id: int):
        """Update API key last used timestamp."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET api_key_last_used = ? WHERE id = ?',
                (datetime.utcnow().isoformat(), user_id)
            )

    def revoke_api_key(self, user_id: int) -> bool:
        """Revoke user's API key."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET api_key = NULL, api_key_created_at = NULL, api_key_last_used = NULL WHERE id = ?',
                (user_id,)
            )
            return cursor.rowcount > 0

    def get_all_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM users ORDER BY created_at DESC LIMIT ? OFFSET ?',
                (limit, skip)
            )
            rows = cursor.fetchall()
            return [self._row_to_user(row) for row in rows]

    def delete_user(self, user_id: int) -> bool:
        """Delete user (soft delete by setting status to inactive)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE users SET status = ? WHERE id = ?',
                (UserStatus.INACTIVE, user_id)
            )
            return cursor.rowcount > 0

    def _row_to_user(self, row) -> User:
        """Convert database row to User object."""
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            hashed_password=row['hashed_password'],
            full_name=row['full_name'],
            role=UserRole(row['role']),
            status=UserStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']),
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
            api_key=row['api_key']
        )