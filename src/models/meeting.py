"""
Meeting Model
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum


class MeetingStatus(str, Enum):
    """Meeting status enum"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Meeting:
    """Meeting model"""
    
    def __init__(
        self,
        id: Optional[int] = None,
        user_id: int = 0,
        title: str = "",
        description: Optional[str] = None,
        date: Optional[datetime] = None,
        duration_minutes: Optional[int] = None,
        status: MeetingStatus = MeetingStatus.PENDING,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.date = date or datetime.utcnow()
        self.duration_minutes = duration_minutes
        self.status = status
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "date": self.date.isoformat() if self.date else None,
            "duration_minutes": self.duration_minutes,
            "status": self.status.value if isinstance(self.status, MeetingStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f"<Meeting(id={self.id}, title={self.title}, status={self.status})>"
