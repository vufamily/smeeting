"""
Main Audio Processing Orchestrator
Runs the complete AI pipeline for meeting transcription
"""

import os
import logging
import json
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
    key_decisions: List[str]
    tasks: List[Dict]
    meeting_minutes: str
    raw_transcription: str


class AudioProcessor:
    """
    Main orchestrator for the complete audio processing pipeline.
    
    Pipeline stages:
    1. Audio input → Source Separation (Demucs) → Clean vocals
    2. Clean audio → VAD (Silero) → Voice segments
    3. Voice segments → Speaker Diarization (pyannote) → Segmented by speaker
    4. Segmented audio → ASR (sherpa-paraformer) → Text transcription
    5. Transcription → LLM Key Info Extraction (Gemma4) → Structured data
    6. Structured data → LLM Meeting Minutes Generation (Gemma4) → Markdown minutes
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
        
        logger.info("Initializing audio processing pipeline...")
        
        try:
            from ..audio_pipeline import source_separation
            from ..audio_pipeline import vad
            from ..audio_pipeline import speaker_diarization
            from ..audio_pipeline import asr
            from ..llm import extract_key_info
            from ..llm import generate_meeting_minutes
            
            self._source_separator = source_separation.SourceSeparator(self.config)
            self._vad_detector = vad.VoiceActivityDetector(self.config)
            self._diarizer = speaker_diarization.SpeakerDiarizer(self.config)
            self._asr_engine = asr.ASREngine(self.config)
            self._llm_extractor = extract_key_info.KeyInfoExtractor(self.config)
            self._llm_generator = generate_meeting_minutes.MeetingMinutesGenerator(self.config)
            
            self._initialized = True
            logger.info("Pipeline components initialized successfully")
            
        except ImportError as e:
            logger.error(f"Failed to import pipeline components: {e}")
            raise RuntimeError(f"Missing dependencies: {e}")
    
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
        
        logger.info(f"=" * 60)
        logger.info(f"Starting audio processing for meeting {meeting_id}")
        logger.info(f"Input file: {audio_path}")
        logger.info(f"=" * 60)
        
        start_time = datetime.now()
        
        try:
            # === STAGE 1: Source Separation ===
            logger.info("[STAGE 1/6] Source Separation - Removing noise and background music...")
            clean_audio_path = self._source_separator.separate(audio_path)
            if not clean_audio_path:
                raise RuntimeError("Source separation failed - no clean audio output")
            logger.info(f"Stage 1 complete: Clean audio saved to {clean_audio_path}")
            
            # === STAGE 2: Voice Activity Detection ===
            logger.info("[STAGE 2/6] Voice Activity Detection - Finding speech segments...")
            voice_segments = self._vad_detector.detect(clean_audio_path)
            if not voice_segments:
                raise RuntimeError("VAD failed - no voice segments detected")
            logger.info(f"Stage 2 complete: Detected {len(voice_segments)} voice segments")
            
            # === STAGE 3: Speaker Diarization ===
            logger.info("[STAGE 3/6] Speaker Diarization - Identifying speakers...")
            speaker_segments = self._diarizer.diarize(clean_audio_path, voice_segments)
            unique_speakers = set(s.speaker_label for s in speaker_segments)
            logger.info(f"Stage 3 complete: {len(speaker_segments)} segments from {len(unique_speakers)} speakers ({', '.join(sorted(unique_speakers))})")
            
            # === STAGE 4: ASR Transcription ===
            logger.info("[STAGE 4/6] ASR Transcription - Converting speech to text...")
            audio_segments = []
            raw_transcription_parts = []
            
            for i, segment in enumerate(speaker_segments):
                logger.debug(f"Transcribing segment {i+1}/{len(speaker_segments)}: {segment.speaker_label} ({segment.start_time:.1f}s - {segment.end_time:.1f}s)")
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
                
                if (i + 1) % 5 == 0:
                    logger.info(f"Transcribed {i+1}/{len(speaker_segments)} segments...")
            
            raw_transcription = "\n".join(raw_transcription_parts)
            logger.info(f"Stage 4 complete: Transcribed {len(audio_segments)} segments")
            
            # === STAGE 5: LLM Key Info Extraction ===
            logger.info("[STAGE 5/6] LLM Key Info Extraction - Extracting decisions and tasks...")
            key_info = self._llm_extractor.extract(raw_transcription)
            key_decisions = key_info.get("key_decisions", [])
            tasks = key_info.get("tasks", [])
            logger.info(f"Stage 5 complete: Extracted {len(key_decisions)} decisions, {len(tasks)} tasks")
            
            # === STAGE 6: LLM Meeting Minutes Generation ===
            logger.info("[STAGE 6/6] LLM Meeting Minutes Generation - Creating formatted minutes...")
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
            logger.info(f"=" * 60)
            logger.info(f"Processing COMPLETE for meeting {meeting_id}")
            logger.info(f"Total time: {elapsed:.1f} seconds")
            logger.info(f"Summary: {len(audio_segments)} segments, {len(unique_speakers)} speakers, "
                       f"{len(key_decisions)} decisions, {len(tasks)} tasks")
            logger.info(f"=" * 60)
            
            return result
            
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
    
    def process_audio_simple(self, audio_path: str, meeting_id: int) -> dict:
        """
        Simplified processing - returns dict instead of dataclass.
        Useful for API integration.
        """
        result = self.process_audio(audio_path, meeting_id)
        
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
