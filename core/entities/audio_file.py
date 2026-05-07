"""
Core Entity: AudioFile
Business entity with no external dependencies.
"""

from datetime import datetime
from typing import Optional
from enum import Enum


class AudioFormat(str, Enum):
    """Audio format enum"""
    MP3 = "mp3"
    WAV = "wav"
    M4A = "m4a"
    OGG = "ogg"
    FLAC = "flac"
    WEBM = "webm"


class AudioFileStatus(str, Enum):
    """Audio file processing status"""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class AudioFile:
    """Audio file business entity"""

    def __init__(
        self,
        id: Optional[int] = None,
        meeting_id: int = 0,
        filename: str = "",
        original_filename: Optional[str] = None,
        file_path: str = "",
        file_size: int = 0,
        duration: Optional[float] = None,
        format: AudioFormat = AudioFormat.MP3,
        sample_rate: Optional[int] = None,
        channels: int = 1,
        status: AudioFileStatus = AudioFileStatus.UPLOADED,
        error_message: Optional[str] = None,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.meeting_id = meeting_id
        self.filename = filename
        self.original_filename = original_filename or filename
        self.file_path = file_path
        self.file_size = file_size
        self.duration = duration
        self.format = format if isinstance(format, AudioFormat) else AudioFormat(format)
        self.sample_rate = sample_rate
        self.channels = channels
        self.status = status if isinstance(status, AudioFileStatus) else AudioFileStatus(status)
        self.error_message = error_message
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "duration": self.duration,
            "format": self.format.value if isinstance(self.format, AudioFormat) else self.format,
            "sample_rate": self.sample_rate,
            "channels": self.channels,
            "status": self.status.value if isinstance(self.status, AudioFileStatus) else self.status,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<AudioFile(id={self.id}, filename={self.filename}, duration={self.duration}s)>"
