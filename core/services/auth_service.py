"""
Core Service: AuthService
Business logic for authentication — no external dependencies.
"""

import bcrypt
from typing import Optional, Tuple
from ..entities.user import User, UserStatus, UserRole
from ..repositories.user_repository import UserRepository


class AuthService:
    """Handles authentication business logic."""

    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """
        Register a new user with pending status.
        Returns (success, message, user).
        """
        # Validate
        if not username or len(username) < 3:
            return False, "Username must be at least 3 characters", None

        if not username.replace('_', '').replace('-', '').isalnum():
            return False, "Username can only contain letters, numbers, hyphens, and underscores", None

        if not email or '@' not in email:
            return False, "Invalid email address", None

        if not password or len(password) < 6:
            return False, "Password must be at least 6 characters", None

        # Check uniqueness
        if self.user_repository.get_by_username(username):
            return False, "Username already taken", None

        if self.user_repository.get_by_email(email):
            return False, "Email already registered", None

        # Hash password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        # Create user
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            full_name=full_name or username,
            role=UserRole.USER,
            status=UserStatus.PENDING
        )

        user = self.user_repository.create(user)
        return True, "Registration successful. Your account is pending approval.", user

    def authenticate(self, username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        Authenticate user with username and password.
        Returns (success, message, user).
        """
        if not username or not password:
            return False, "Username and password required", None

        user = self.user_repository.get_by_username(username)
        if not user:
            return False, "Invalid username or password", None

        if not bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
            return False, "Invalid username or password", None

        if user.status == UserStatus.PENDING:
            return False, "Your account is pending approval", None

        if user.status == UserStatus.REJECTED:
            return False, "Your account has been rejected", None

        if user.status == UserStatus.DISABLED:
            return False, "Your account has been disabled", None

        return True, "Authentication successful", user

    def approve_user(self, user_id: int) -> Tuple[bool, str]:
        """Approve a pending user."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return False, "User not found"

        if user.status != UserStatus.PENDING:
            return False, f"User status is {user.status.value}, expected pending"

        success = self.user_repository.update_status(user_id, UserStatus.APPROVED.value)
        return success, "User approved successfully"

    def reject_user(self, user_id: int) -> Tuple[bool, str]:
        """Reject a pending user."""
        user = self.user_repository.get_by_id(user_id)
        if not user:
            return False, "User not found"

        success = self.user_repository.update_status(user_id, UserStatus.REJECTED.value)
        return success, "User rejected"

    def disable_user(self, user_id: int) -> Tuple[bool, str]:
        """Disable an approved user."""
        success = self.user_repository.update_status(user_id, UserStatus.DISABLED.value)
        return success, "User disabled" if success else (False, "Failed to disable user")

    def enable_user(self, user_id: int) -> Tuple[bool, str]:
        """Re-enable a disabled user."""
        success = self.user_repository.update_status(user_id, UserStatus.APPROVED.value)
        return success, "User enabled" if success else (False, "Failed to enable user")

    def change_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """Change a user's password."""
        if not new_password or len(new_password) < 6:
            return False, "Password must be at least 6 characters"

        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        success = self.user_repository.update_password(user_id, password_hash)
        return success, "Password changed successfully" if success else (False, "Failed to change password")

    def update_profile(self, user_id: int, email: str, full_name: str) -> Tuple[bool, str, Optional[User]]:
        """Update user profile."""
        # Check email uniqueness (excluding current user)
        existing = self.user_repository.get_by_email(email)
        if existing and existing.id != user_id:
            return False, "Email already in use by another account", None

        user = self.user_repository.get_by_id(user_id)
        if not user:
            return False, "User not found", None

        user.email = email
        user.full_name = full_name
        user = self.user_repository.update(user)
        return True, "Profile updated successfully", user

    def get_all_users(self) -> list:
        """Get all users."""
        return self.user_repository.get_all()

    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return self.user_repository.get_by_id(user_id)
