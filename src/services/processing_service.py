"""
Processing Service - Orchestrates the AI pipeline with database integration
"""

import os
import logging
import json
from typing import Dict, Optional, Tuple
from datetime import datetime

from ..processor import AudioProcessor, AudioSegment
from ..models import Meeting, AudioFile, Transcription, MeetingMinutes

logger = logging.getLogger(__name__)


class ProcessingService:
    """
    High-level service that orchestrates audio processing and database operations.
    
    Responsibilities:
    - Coordinate the AI processing pipeline
    - Save results to database
    - Handle errors gracefully
    - Provide status updates
    """
    
    def __init__(self, config: Dict, db_session=None):
        """
        Initialize processing service.
        
        Args:
            config: Application configuration dict
            db_session: Optional database session for persistence
        """
        self.config = config
        self.db_session = db_session
        self.processor = AudioProcessor(config)
        self._upload_dir = config.get("storage", {}).get("upload_dir", "data/uploads")
        self._output_dir = config.get("storage", {}).get("output_dir", "data/outputs")
        
        # Ensure directories exist
        os.makedirs(self._upload_dir, exist_ok=True)
        os.makedirs(self._output_dir, exist_ok=True)
    
    def start_processing(self, meeting_id: int, audio_path: str) -> Tuple[bool, str]:
        """
        Start audio processing for a meeting.
        
        Args:
            meeting_id: Database ID of the meeting
            audio_path: Path to uploaded audio file
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        logger.info(f"Starting processing for meeting {meeting_id}")
        logger.info(f"Audio path: {audio_path}")
        
        # Validate audio file exists
        if not os.path.exists(audio_path):
            return False, f"Audio file not found: {audio_path}"
        
        # Update meeting status to processing
        if self.db_session:
            self._update_meeting_status(meeting_id, "processing")
        
        try:
            # Run the complete AI pipeline
            result = self.processor.process_audio(audio_path, meeting_id)
            
            # Save transcription segments to database
            if self.db_session:
                self._save_transcriptions(meeting_id, result.audio_segments)
                self._save_meeting_minutes(meeting_id, result)
                self._update_meeting_status(meeting_id, "completed")
            
            logger.info(f"Processing completed successfully for meeting {meeting_id}")
            return True, "Processing completed successfully"
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            
            if self.db_session:
                self._update_meeting_status(meeting_id, "failed")
            
            return False, f"Processing failed: {str(e)}"
    
    def get_processing_status(self, meeting_id: int) -> Dict:
        """
        Get current processing status for a meeting.
        
        Args:
            meeting_id: Database ID of the meeting
            
        Returns:
            Dict with status information
        """
        if not self.db_session:
            return {"status": "unknown", "message": "No database connection"}
        
        try:
            meeting = self.db_session.query(Meeting).get(meeting_id)
            if not meeting:
                return {"status": "not_found", "message": f"Meeting {meeting_id} not found"}
            
            return {
                "status": meeting.status.value if hasattr(meeting.status, 'value') else meeting.status,
                "meeting_id": meeting_id,
                "title": meeting.title,
                "date": meeting.date.isoformat() if meeting.date else None
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {"status": "error", "message": str(e)}
    
    def get_meeting_minutes(self, meeting_id: int) -> Optional[Dict]:
        """
        Retrieve meeting minutes for a completed meeting.
        
        Args:
            meeting_id: Database ID of the meeting
            
        Returns:
            Dict with meeting minutes data or None if not found
        """
        if not self.db_session:
            return None
        
        try:
            minutes = self.db_session.query(MeetingMinutes).filter_by(
                meeting_id=meeting_id
            ).first()
            
            if minutes:
                return minutes.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving minutes: {e}")
            return None
    
    def get_transcriptions(self, meeting_id: int) -> list:
        """
        Retrieve all transcription segments for a meeting.
        
        Args:
            meeting_id: Database ID of the meeting
            
        Returns:
            List of transcription dicts
        """
        if not self.db_session:
            return []
        
        try:
            transcriptions = self.db_session.query(Transcription).filter_by(
                meeting_id=meeting_id
            ).order_by(Transcription.start_time).all()
            
            return [t.to_dict() for t in transcriptions]
            
        except Exception as e:
            logger.error(f"Error retrieving transcriptions: {e}")
            return []
    
    def _update_meeting_status(self, meeting_id: int, status: str):
        """Update meeting status in database"""
        try:
            meeting = self.db_session.query(Meeting).get(meeting_id)
            if meeting:
                from ..models.meeting import MeetingStatus
                meeting.status = MeetingStatus(status)
                meeting.updated_at = datetime.utcnow()
                self.db_session.commit()
                logger.info(f"Meeting {meeting_id} status updated to: {status}")
        except Exception as e:
            logger.error(f"Failed to update meeting status: {e}")
            self.db_session.rollback()
    
    def _save_transcriptions(self, meeting_id: int, segments: list):
        """Save transcription segments to database"""
        try:
            for segment in segments:
                transcription = Transcription(
                    meeting_id=meeting_id,
                    speaker_label=segment.speaker_label,
                    text=segment.text,
                    start_time=segment.start_time,
                    end_time=segment.end_time
                )
                self.db_session.add(transcription)
            
            self.db_session.commit()
            logger.info(f"Saved {len(segments)} transcription segments")
            
        except Exception as e:
            logger.error(f"Failed to save transcriptions: {e}")
            self.db_session.rollback()
            raise
    
    def _save_meeting_minutes(self, meeting_id: int, result):
        """Save meeting minutes to database"""
        try:
            minutes = MeetingMinutes(
                meeting_id=meeting_id,
                content_md=result.meeting_minutes,
                raw_transcription=result.raw_transcription,
                key_decisions=result.key_decisions,
                tasks_json=json.dumps(result.tasks, ensure_ascii=False)
            )
            
            self.db_session.add(minutes)
            self.db_session.commit()
            logger.info(f"Saved meeting minutes for meeting {meeting_id}")
            
        except Exception as e:
            logger.error(f"Failed to save meeting minutes: {e}")
            self.db_session.rollback()
            raise
