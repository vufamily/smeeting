"""
Infrastructure: SQLite User Repository
Implements UserRepository interface defined in core.
"""

from typing import Optional, List
from datetime import datetime
import bcrypt

from core.entities.user import User, UserRole, UserStatus
from core.repositories.user_repository import UserRepository
from .sqlite_connection import SQLiteConnection


class SQLiteUserRepository(UserRepository):
    """SQLite implementation of UserRepository."""

    def __init__(self, db_connection: SQLiteConnection):
        self.db = db_connection

    def _row_to_user(self, row) -> User:
        """Convert a database row to a User entity."""
        return User(
            id=row['id'],
            username=row['username'],
            email=row['email'],
            password_hash=row['password_hash'],
            full_name=row['full_name'],
            role=UserRole(row['role']),
            status=UserStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )

    def get_by_id(self, user_id: int) -> Optional[User]:
        row = self.db.fetch_one('SELECT * FROM users WHERE id = ?', (user_id,))
        return self._row_to_user(row) if row else None

    def get_by_username(self, username: str) -> Optional[User]:
        row = self.db.fetch_one('SELECT * FROM users WHERE username = ?', (username,))
        return self._row_to_user(row) if row else None

    def get_by_email(self, email: str) -> Optional[User]:
        row = self.db.fetch_one('SELECT * FROM users WHERE email = ?', (email,))
        return self._row_to_user(row) if row else None

    def create(self, user: User) -> User:
        cursor = self.db.execute(
            '''INSERT INTO users (username, email, password_hash, full_name, role, status)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (user.username, user.email, user.password_hash, user.full_name,
             user.role.value, user.status.value)
        )
        user.id = cursor.lastrowid
        return user

    def update(self, user: User) -> User:
        self.db.execute(
            '''UPDATE users SET username=?, email=?, password_hash=?, full_name=?,
               role=?, status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (user.username, user.email, user.password_hash, user.full_name,
             user.role.value, user.status.value, user.id)
        )
        return user

    def delete(self, user_id: int) -> bool:
        self.db.execute('DELETE FROM users WHERE id = ?', (user_id,))
        return True

    def get_all(self) -> List[User]:
        rows = self.db.fetch_all('SELECT * FROM users ORDER BY created_at DESC')
        return [self._row_to_user(row) for row in rows]

    def update_status(self, user_id: int, status: str) -> bool:
        self.db.execute(
            'UPDATE users SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (status, user_id)
        )
        return True

    def update_password(self, user_id: int, password_hash: str) -> bool:
        self.db.execute(
            'UPDATE users SET password_hash = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (password_hash, user_id)
        )
        return True
