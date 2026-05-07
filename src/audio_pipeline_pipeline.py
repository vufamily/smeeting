"""
Audio Pipeline Integration - Connects AI modules with Flask backend
"""

import os
import logging
import json
import uuid
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Represents a segment of audio with speaker and text info"""
    speaker_label: str
    text: str
    start_time: float
    end_time: float
    audio_path: Optional[str] = None


@dataclass
class ProcessingResult:
    """Result of complete audio processing"""
    meeting_id: int
    audio_segments: List[AudioSegment]
    key_decisions: List[Dict]
    tasks: List[Dict]
    meeting_minutes: str
    raw_transcription: str


class AudioPipeline:
    """
    Audio Processing Pipeline - integrates all AI components.
    
    Pipeline stages:
    1. Source Separation (Demucs) → Clean vocals
    2. VAD (Silero) → Voice segments
    3. Speaker Diarization (PyAnote) → Segmented by speaker
    4. ASR (Sherpa Paraformer) → Text transcription
    5. LLM Key Info Extraction (Gemma4) → Structured data
    6. LLM Meeting Minutes Generation (Gemma4) → Markdown minutes
    """
    
    def __init__(self, config: Dict):
        self.config = config
        self._source_separator = None
        self._vad_detector = None
        self._diarizer = None
        self._asr_engine = None
        self._llm_extractor = None
        self._llm_generator = None
        self._initialized = False
    
    def _lazy_init(self):
        """Lazy initialization of pipeline components"""
        if self._initialized:
            return
        
        logger.info("Initializing audio pipeline components...")
        
        try:
            from .audio_pipeline import source_separation
            from .audio_pipeline import vad
            from .audio_pipeline import speaker_diarization
            from .audio_pipeline import asr
            from .llm import extract_key_info
            from .llm import generate_meeting_minutes
            
            self._source_separator = source_separation.SourceSeparator(self.config)
            self._vad_detector = vad.VoiceActivityDetector(self.config)
            self._diarizer = speaker_diarization.SpeakerDiarizer(self.config)
            self._asr_engine = asr.ASREngine(self.config)
            self._llm_extractor = extract_key_info.KeyInfoExtractor(self.config)
            self._llm_generator = generate_meeting_minutes.MeetingMinutesGenerator(self.config)
            
            self._initialized = True
            logger.info("All pipeline components initialized")
            
        except ImportError as e:
            logger.error(f"Failed to import pipeline components: {e}")
            # Pipeline will work in demo mode
            self._initialized = True
    
    def process_audio(self, audio_path: str, meeting_id: int) -> ProcessingResult:
        """
        Run complete processing pipeline on audio file.
        
        Args:
            audio_path: Path to input audio file
            meeting_id: Database meeting ID for associating results
            
        Returns:
            ProcessingResult with all extracted information
        """
        self._lazy_init()
        
        logger.info(f"Starting audio processing for meeting {meeting_id}")
        logger.info(f"Input file: {audio_path}")
        
        start_time = datetime.now()
        
        try:
            # === STAGE 1: Source Separation ===
            logger.info("[1/6] Source Separation...")
            clean_audio_path = self._source_separator.separate(audio_path)
            if not clean_audio_path:
                clean_audio_path = audio_path  # Fallback to original
            logger.info(f"Stage 1 complete: {clean_audio_path}")
            
            # === STAGE 2: Voice Activity Detection ===
            logger.info("[2/6] Voice Activity Detection...")
            voice_segments = self._vad_detector.detect(clean_audio_path)
            if not voice_segments:
                # Fallback: create one segment for entire audio
                voice_segments = [vad.VoiceSegment(start_time=0.0, end_time=300.0)]
            logger.info(f"Stage 2 complete: {len(voice_segments)} voice segments")
            
            # === STAGE 3: Speaker Diarization ===
            logger.info("[3/6] Speaker Diarization...")
            speaker_segments = self._diarizer.diarize(clean_audio_path, voice_segments)
            unique_speakers = set(s.speaker_label for s in speaker_segments)
            logger.info(f"Stage 3 complete: {len(speaker_segments)} segments from {len(unique_speakers)} speakers")
            
            # === STAGE 4: ASR Transcription ===
            logger.info("[4/6] ASR Transcription...")
            audio_segments = []
            raw_transcription_parts = []
            
            for i, segment in enumerate(speaker_segments):
                text = self._asr_engine.transcribe(segment.audio_path) if segment.audio_path else ""
                
                audio_segment = AudioSegment(
                    speaker_label=segment.speaker_label,
                    text=text or "[No speech detected]",
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    audio_path=segment.audio_path
                )
                audio_segments.append(audio_segment)
                raw_transcription_parts.append(f"{segment.speaker_label}: {text}")
            
            raw_transcription = "\n".join(raw_transcription_parts)
            logger.info(f"Stage 4 complete: {len(audio_segments)} segments transcribed")
            
            # === STAGE 5: LLM Key Info Extraction ===
            logger.info("[5/6] LLM Key Info Extraction...")
            key_info = self._llm_extractor.extract(raw_transcription)
            key_decisions = key_info.get("key_decisions", [])
            tasks = key_info.get("tasks", [])
            logger.info(f"Stage 5 complete: {len(key_decisions)} decisions, {len(tasks)} tasks")
            
            # === STAGE 6: LLM Meeting Minutes Generation ===
            logger.info("[6/6] LLM Meeting Minutes Generation...")
            meeting_minutes = self._llm_generator.generate(
                transcription=raw_transcription,
                key_decisions=key_decisions,
                tasks=tasks,
                audio_segments=audio_segments
            )
            logger.info("Stage 6 complete: Meeting minutes generated")
            
            # === Build Result ===
            result = ProcessingResult(
                meeting_id=meeting_id,
                audio_segments=audio_segments,
                key_decisions=key_decisions,
                tasks=tasks,
                meeting_minutes=meeting_minutes,
                raw_transcription=raw_transcription
            )
            
            elapsed = (datetime.now() - start_time).total_seconds()
            logger.info(f"Processing COMPLETE in {elapsed:.1f}s for meeting {meeting_id}")
            
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
    
    def process_audio_simple(self, audio_path: str, meeting_id: int) -> dict:
        """
        Simplified processing - returns dict format for API integration.
        """
        try:
            result = self.process_audio(audio_path, meeting_id)
        except Exception as e:
            logger.warning(f"Pipeline processing failed, using demo data: {e}")
            # Return demo result structure
            return self._create_demo_result(meeting_id)
        
        return {
            "meeting_id": result.meeting_id,
            "raw_transcription": result.raw_transcription,
            "meeting_minutes": result.meeting_minutes,
            "key_decisions": result.key_decisions,
            "tasks": result.tasks,
            "segments": [
                {
                    "speaker": seg.speaker_label,
                    "text": seg.text,
                    "start_time": seg.start_time,
                    "end_time": seg.end_time
                }
                for seg in result.audio_segments
            ]
        }
    
    def _create_demo_result(self, meeting_id: int) -> dict:
        """Create demo result when pipeline is not available"""
        return {
            "meeting_id": meeting_id,
            "transcription": self._create_demo_transcription(),
            "decisions": self._create_demo_decisions(),
            "tasks": self._create_demo_tasks(),
            "summary": self._create_demo_summary(),
            "is_demo": True
        }
    
    def _create_demo_transcription(self) -> list:
        """Sample transcription for demo mode"""
        return [
            {"speaker": "Speaker A", "start": 0.0, "end": 5.2, "text": "Good morning everyone, let's start the sprint planning meeting."},
            {"speaker": "Speaker B", "start": 5.5, "end": 12.8, "text": "Thanks for joining. Today we need to plan the Q2 deliverables."},
            {"speaker": "Speaker A", "start": 13.2, "end": 22.5, "text": "I've reviewed the mockups. We can target March 15th for the beta release."},
            {"speaker": "Speaker B", "start": 36.0, "end": 45.3, "text": "April 1st works for marketing. Sarah, can you prepare a revised schedule?"},
        ]
    
    def _create_demo_decisions(self) -> list:
        """Sample decisions for demo mode"""
        return [
            {"id": str(uuid.uuid4()), "text": "Mobile app beta release target: April 1st", "speaker": "Speaker A", "timestamp": 22.5},
            {"id": str(uuid.uuid4()), "text": "Marketing budget: 50K approved", "speaker": "Speaker B", "timestamp": 78.2}
        ]
    
    def _create_demo_tasks(self) -> list:
        """Sample tasks for demo mode"""
        return [
            {"id": str(uuid.uuid4()), "text": "Prepare revised Q2 schedule", "assignee": "Sarah", "due_date": "2026-05-10", "completed": False},
            {"id": str(uuid.uuid4()), "text": "Coordinate staging environment setup", "assignee": "David", "due_date": "2026-05-14", "completed": False}
        ]
    
    def _create_demo_summary(self) -> str:
        """Sample summary for demo mode"""
        return """
## Meeting Summary

**Date:** May 7, 2026  
**Participants:** Speaker A, Speaker B

### Key Outcomes
1. Mobile app beta release scheduled for April 1st
2. 50,000 marketing budget approved

### Action Items
- Sarah to send revised schedule by May 10
- David to coordinate staging environment setup

---
*Meeting recorded and transcribed automatically*
        """.strip()
