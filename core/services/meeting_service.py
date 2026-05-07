"""
Core Service: MeetingService
Business logic for meeting management — no external dependencies.
"""

import uuid
from typing import Optional, List, Tuple
from datetime import datetime
from ..entities.meeting import Meeting, MeetingStatus
from ..repositories.meeting_repository import MeetingRepository


class MeetingService:
    """Handles meeting business logic."""

    def __init__(self, meeting_repository: MeetingRepository):
        self.meeting_repository = meeting_repository

    def create_meeting(
        self,
        user_id: int,
        title: str,
        description: Optional[str] = None,
        date: Optional[datetime] = None,
        duration_minutes: Optional[int] = None
    ) -> Meeting:
        """Create a new meeting."""
        meeting = Meeting(
            user_id=user_id,
            title=title,
            description=description,
            date=date or datetime.utcnow(),
            duration_minutes=duration_minutes,
            status=MeetingStatus.PENDING
        )
        return self.meeting_repository.create(meeting)

    def get_meeting(self, meeting_id: int) -> Optional[Meeting]:
        """Get meeting by ID."""
        return self.meeting_repository.get_by_id(meeting_id)

    def get_user_meetings(self, user_id: int) -> List[Meeting]:
        """Get all meetings for a user."""
        return self.meeting_repository.get_by_user(user_id)

    def get_all_meetings(self) -> List[Meeting]:
        """Get all meetings."""
        return self.meeting_repository.get_all()

    def update_meeting(
        self,
        meeting_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        date: Optional[datetime] = None,
        duration_minutes: Optional[int] = None
    ) -> Tuple[bool, str, Optional[Meeting]]:
        """Update meeting details."""
        meeting = self.meeting_repository.get_by_id(meeting_id)
        if not meeting:
            return False, "Meeting not found", None

        if title is not None:
            meeting.title = title
        if description is not None:
            meeting.description = description
        if date is not None:
            meeting.date = date
        if duration_minutes is not None:
            meeting.duration_minutes = duration_minutes

        meeting.updated_at = datetime.utcnow()
        meeting = self.meeting_repository.update(meeting)
        return True, "Meeting updated successfully", meeting

    def delete_meeting(self, meeting_id: int) -> Tuple[bool, str]:
        """Delete a meeting."""
        success = self.meeting_repository.delete(meeting_id)
        return success, "Meeting deleted" if success else (False, "Failed to delete meeting")

    def start_processing(self, meeting_id: int) -> Tuple[bool, str]:
        """Mark meeting as processing."""
        meeting = self.meeting_repository.get_by_id(meeting_id)
        if not meeting:
            return False, "Meeting not found"

        success = self.meeting_repository.update_status(meeting_id, MeetingStatus.PROCESSING.value)
        return success, "Processing started" if success else (False, "Failed to start processing")

    def complete_meeting(self, meeting_id: int) -> Tuple[bool, str]:
        """Mark meeting as completed."""
        success = self.meeting_repository.update_status(meeting_id, MeetingStatus.COMPLETED.value)
        return success, "Meeting completed" if success else (False, "Failed to complete meeting")

    def fail_meeting(self, meeting_id: int) -> Tuple[bool, str]:
        """Mark meeting as failed."""
        success = self.meeting_repository.update_status(meeting_id, MeetingStatus.FAILED.value)
        return success, "Meeting marked as failed" if success else (False, "Failed to update meeting")


# In-memory meeting storage for backward compatibility with existing API
class InMemoryMeetingService:
    """In-memory meeting storage for API backward compatibility."""

    def __init__(self):
        self.meetings = {}
        self.processing_jobs = {}

    def create_meeting(self, name: str, audio_file: str, user_id: int) -> dict:
        meeting_id = str(uuid.uuid4())
        meeting = {
            'id': meeting_id,
            'name': name,
            'created_at': datetime.now().isoformat(),
            'audio_file': audio_file,
            'status': 'uploaded',
            'user_id': user_id
        }
        self.meetings[meeting_id] = meeting
        return meeting

    def get_meeting(self, meeting_id: str) -> Optional[dict]:
        return self.meetings.get(meeting_id)

    def get_all_meetings(self) -> List[dict]:
        meetings_list = []
        for m in self.meetings.values():
            meetings_list.append({
                'id': m['id'],
                'name': m['name'],
                'created_at': m['created_at'],
                'status': m.get('status', 'unknown')
            })
        meetings_list.sort(key=lambda x: x['created_at'], reverse=True)
        return meetings_list

    def delete_meeting(self, meeting_id: str) -> bool:
        if meeting_id in self.meetings:
            del self.meetings[meeting_id]
            for job_id, job in list(self.processing_jobs.items()):
                if job['meeting_id'] == meeting_id:
                    del self.processing_jobs[job_id]
            return True
        return False

    def update_status(self, meeting_id: str, status: str):
        if meeting_id in self.meetings:
            self.meetings[meeting_id]['status'] = status

    def create_processing_job(self, meeting_id: str) -> dict:
        job_id = str(uuid.uuid4())
        job = {
            'job_id': job_id,
            'meeting_id': meeting_id,
            'status': 'processing',
            'progress': 0,
            'step': 'upload',
            'steps': {
                'upload': {'status': 'complete', 'progress': 100},
                'validate': {'status': 'complete', 'progress': 100},
                'transcribe': {'status': 'processing', 'progress': 50},
                'speakers': {'status': 'pending', 'progress': 0},
                'decisions': {'status': 'pending', 'progress': 0},
                'tasks': {'status': 'pending', 'progress': 0},
                'summary': {'status': 'pending', 'progress': 0},
                'complete': {'status': 'pending', 'progress': 0}
            }
        }
        self.processing_jobs[job_id] = job
        if meeting_id in self.meetings:
            self.meetings[meeting_id]['status'] = 'processing'
            self.meetings[meeting_id]['job_id'] = job_id
        return job

    def get_job(self, job_id: str) -> Optional[dict]:
        return self.processing_jobs.get(job_id)

    def complete_job(self, job_id: str):
        if job_id in self.processing_jobs:
            self.processing_jobs[job_id]['status'] = 'complete'
            self.processing_jobs[job_id]['progress'] = 100
            self.processing_jobs[job_id]['step'] = 'complete'
            for step in self.processing_jobs[job_id]['steps']:
                self.processing_jobs[job_id]['steps'][step] = {'status': 'complete', 'progress': 100}

    def get_meeting_job(self, meeting_id: str) -> Optional[dict]:
        for job in self.processing_jobs.values():
            if job['meeting_id'] == meeting_id:
                return job
        return None
