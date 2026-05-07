"""
Core Repositories - Abstract interfaces for data access.
"""

from .user_repository import UserRepository
from .meeting_repository import MeetingRepository

__all__ = [
    "UserRepository",
    "MeetingRepository",
]
