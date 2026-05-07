"""
Core Entity: Task
Business entity with no external dependencies.
"""

from datetime import datetime
from typing import Optional
from enum import Enum


class TaskPriority(str, Enum):
    """Task priority enum"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TaskStatus(str, Enum):
    """Task completion status"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Task:
    """Action item / task extracted from meeting"""

    def __init__(
        self,
        id: Optional[int] = None,
        meeting_id: int = 0,
        text: str = "",
        assignee: str = "",
        due_date: Optional[str] = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        status: TaskStatus = TaskStatus.OPEN,
        created_at: Optional[datetime] = None
    ):
        self.id = id
        self.meeting_id = meeting_id
        self.text = text
        self.assignee = assignee
        self.due_date = due_date
        self.priority = priority if isinstance(priority, TaskPriority) else TaskPriority(priority)
        self.status = status if isinstance(status, TaskStatus) else TaskStatus(status)
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "meeting_id": self.meeting_id,
            "text": self.text,
            "assignee": self.assignee,
            "due_date": self.due_date,
            "priority": self.priority.value if isinstance(self.priority, TaskPriority) else self.priority,
            "status": self.status.value if isinstance(self.status, TaskStatus) else self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f"<Task(id={self.id}, text={self.text[:50]}..., assignee={self.assignee})>"
