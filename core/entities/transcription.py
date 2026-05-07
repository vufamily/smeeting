"""
Core Entity: Transcription
Business entity with no external dependencies.
"""

from datetime import datetime
from typing import Optional


class Transcription:
    """Transcription segment business entity"""

    def __init__(
        self,
        id: Optional[int] = None,
        meeting_id: int = 0,
        audio_file_id: Optional[int] = None,
        speaker_label: str = "Speaker 1",
        text: str = "",
        start_time: float = 0.0,
        end_time: float = 0.0,
        confidence: float = 1.0,
        language: str = "vi",
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.meeting_id = meeting_id
        self.audio_file_id = audio_file_id
        self.speaker_label = speaker_label
        self.text = text
        self.start_time = start_time
        self.end_time = end_time
        self.confidence = confidence
        self.language = language
        self.created_at = created_at or datetime.utcnow()

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "audio_file_id": self.audio_file_id,
            "speaker_label": self.speaker_label,
            "text": self.text,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "confidence": self.confidence,
            "language": self.language,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Transcription(id={self.id}, speaker={self.speaker_label}, text={self.text[:50]}...)>"
