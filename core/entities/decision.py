"""
Core Entity: Decision
Business entity with no external dependencies.
"""

from datetime import datetime
from typing import Optional


class Decision:
    """Key decision extracted from meeting"""

    def __init__(
        self,
        id: Optional[int] = None,
        meeting_id: int = 0,
        text: str = "",
        speaker: str = "",
        timestamp: float = 0.0,
        owner: Optional[str] = None,
        due_date: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.meeting_id = meeting_id
        self.text = text
        self.speaker = speaker
        self.timestamp = timestamp
        self.owner = owner
        self.due_date = due_date
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "text": self.text,
            "speaker": self.speaker,
            "timestamp": self.timestamp,
            "owner": self.owner,
            "due_date": self.due_date,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Decision(id={self.id}, text={self.text[:50]}...)>"
