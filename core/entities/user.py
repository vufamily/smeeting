"""
Core Entity: User
Business entity with no external dependencies.
"""

from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    """User role enum"""
    ADMIN = "admin"
    USER = "user"


class UserStatus(str, Enum):
    """User account status enum"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISABLED = "disabled"


class User:
    """User account business entity"""

    def __init__(
        self,
        id: Optional[int] = None,
        username: str = "",
        email: str = "",
        password_hash: str = "",
        full_name: Optional[str] = None,
        role: UserRole = UserRole.USER,
        status: UserStatus = UserStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.full_name = full_name or username
        self.role = role if isinstance(role, UserRole) else UserRole(role)
        self.status = status if isinstance(status, UserStatus) else UserStatus(status)
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN and self.status == UserStatus.APPROVED

    def is_approved(self) -> bool:
        return self.status == UserStatus.APPROVED

    def is_active(self) -> bool:
        return self.status == UserStatus.APPROVED

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "full_name": self.full_name,
            "role": self.role.value if isinstance(self.role, UserRole) else self.role,
            "status": self.status.value if isinstance(self.status, UserStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username}, role={self.role}, status={self.status})>"
