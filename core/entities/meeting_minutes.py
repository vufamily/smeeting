"""
Core Entity: MeetingMinutes
Business entity with no external dependencies.
"""

from datetime import datetime
from typing import Optional, List
import json


class MeetingMinutes:
    """Meeting minutes business entity"""

    def __init__(
        self,
        id: Optional[int] = None,
        meeting_id: int = 0,
        transcription_id: Optional[int] = None,
        title: Optional[str] = None,
        content_md: str = "",
        raw_transcription: str = "",
        key_decisions: List[str] = None,
        tasks_json: str = "[]",
        attendees: List[str] = None,
        next_meeting: Optional[str] = None,
        generated_by: str = "gemma4",
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None
    ):
        self.id = id
        self.meeting_id = meeting_id
        self.transcription_id = transcription_id
        self.title = title
        self.content_md = content_md
        self.raw_transcription = raw_transcription
        self.key_decisions = key_decisions or []
        self.tasks_json = tasks_json or "[]"
        self.attendees = attendees or []
        self.next_meeting = next_meeting
        self.generated_by = generated_by
        self.created_at = created_at or datetime.utcnow()
        self.updated_at = updated_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "transcription_id": self.transcription_id,
            "title": self.title,
            "content_md": self.content_md,
            "raw_transcription": self.raw_transcription,
            "key_decisions": self.key_decisions,
            "tasks": self.get_tasks(),
            "attendees": self.attendees,
            "next_meeting": self.next_meeting,
            "generated_by": self.generated_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

    def get_tasks(self) -> List[dict]:
        """Parse tasks from JSON"""
        try:
            return json.loads(self.tasks_json)
        except Exception:
            return []

    def set_tasks(self, tasks: List[dict]):
        """Serialize tasks to JSON"""
        self.tasks_json = json.dumps(tasks, ensure_ascii=False)

    def __repr__(self):
        return f"<MeetingMinutes(id={self.id}, meeting_id={self.meeting_id}, title={self.title})>"
