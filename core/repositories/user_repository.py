"""
Core Repository Interface: UserRepository
Abstract interface for user data access.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities.user import User


class UserRepository(ABC):
    """Abstract interface for User persistence operations."""

    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        pass

    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        pass

    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        pass

    @abstractmethod
    def create(self, user: User) -> User:
        """Create a new user."""
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        """Update an existing user."""
        pass

    @abstractmethod
    def delete(self, user_id: int) -> bool:
        """Delete a user by ID."""
        pass

    @abstractmethod
    def get_all(self) -> List[User]:
        """Get all users."""
        pass

    @abstractmethod
    def update_status(self, user_id: int, status: str) -> bool:
        """Update user status."""
        pass

    @abstractmethod
    def update_password(self, user_id: int, password_hash: str) -> bool:
        """Update user password hash."""
        pass

    @abstractmethod
    def update_user(self, user: User) -> User:
        """Update user entity (role, full_name only)."""
        pass