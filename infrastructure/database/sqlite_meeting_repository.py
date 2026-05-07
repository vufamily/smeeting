"""
Infrastructure: SQLite Meeting Repository
Implements MeetingRepository interface defined in core.
"""

from typing import Optional, List
from datetime import datetime

from core.entities.meeting import Meeting, MeetingStatus
from core.repositories.meeting_repository import MeetingRepository
from .sqlite_connection import SQLiteConnection


class SQLiteMeetingRepository(MeetingRepository):
    """SQLite implementation of MeetingRepository."""

    def __init__(self, db_connection: SQLiteConnection):
        self.db = db_connection

    def _row_to_meeting(self, row) -> Meeting:
        """Convert a database row to a Meeting entity."""
        return Meeting(
            id=row['id'],
            user_id=row.get('created_by', 0),
            title=row['title'],
            description=row['description'],
            date=datetime.fromisoformat(row['scheduled_at']) if row.get('scheduled_at') else None,
            duration_minutes=row.get('duration_minutes'),
            status=MeetingStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
        )

    def get_by_id(self, meeting_id: int) -> Optional[Meeting]:
        row = self.db.fetch_one('SELECT * FROM meetings WHERE id = ?', (meeting_id,))
        return self._row_to_meeting(row) if row else None

    def create(self, meeting: Meeting) -> Meeting:
        cursor = self.db.execute(
            '''INSERT INTO meetings (title, description, scheduled_at, duration_minutes, status, created_by)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (meeting.title, meeting.description,
             meeting.date.isoformat() if meeting.date else None,
             meeting.duration_minutes, meeting.status.value, meeting.user_id)
        )
        meeting.id = cursor.lastrowid
        return meeting

    def update(self, meeting: Meeting) -> Meeting:
        self.db.execute(
            '''UPDATE meetings SET title=?, description=?, scheduled_at=?, duration_minutes=?,
               status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?''',
            (meeting.title, meeting.description,
             meeting.date.isoformat() if meeting.date else None,
             meeting.duration_minutes, meeting.status.value, meeting.id)
        )
        return meeting

    def delete(self, meeting_id: int) -> bool:
        self.db.execute('DELETE FROM meetings WHERE id = ?', (meeting_id,))
        return True

    def get_by_user(self, user_id: int) -> List[Meeting]:
        rows = self.db.fetch_all(
            'SELECT * FROM meetings WHERE created_by = ? ORDER BY created_at DESC',
            (user_id,)
        )
        return [self._row_to_meeting(row) for row in rows]

    def update_status(self, meeting_id: int, status: str) -> bool:
        self.db.execute(
            'UPDATE meetings SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
            (status, meeting_id)
        )
        return True

    def get_all(self) -> List[Meeting]:
        rows = self.db.fetch_all('SELECT * FROM meetings ORDER BY created_at DESC')
        return [self._row_to_meeting(row) for row in rows]
