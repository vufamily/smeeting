"""
Core Repository Interface: MeetingRepository
Abstract interface for meeting data access.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from ..entities.meeting import Meeting


class MeetingRepository(ABC):
    """Abstract interface for Meeting persistence operations."""

    @abstractmethod
    def get_by_id(self, meeting_id: int) -> Optional[Meeting]:
        """Get meeting by ID."""
        pass

    @abstractmethod
    def create(self, meeting: Meeting) -> Meeting:
        """Create a new meeting."""
        pass

    @abstractmethod
    def update(self, meeting: Meeting) -> Meeting:
        """Update an existing meeting."""
        pass

    @abstractmethod
    def delete(self, meeting_id: int) -> bool:
        """Delete a meeting by ID."""
        pass

    @abstractmethod
    def get_by_user(self, user_id: int) -> List[Meeting]:
        """Get all meetings for a user."""
        pass

    @abstractmethod
    def update_status(self, meeting_id: int, status: str) -> bool:
        """Update meeting status."""
        pass

    @abstractmethod
    def get_all(self) -> List[Meeting]:
        """Get all meetings."""
        pass
