"""
Audio Processing Pipeline for Meeting Assistant
Orchestrates audio cleaning, VAD, speaker diarization, and ASR
"""

import os
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from .audio_pipeline import source_separation, vad, speaker_diarization, asr
from .llm import extract_key_info, generate_meeting_minutes

logger = logging.getLogger(__name__)


@dataclass
class AudioSegment:
    """Represents a segment of audio with speaker info"""
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
    """Main orchestrator for audio processing pipeline"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.source_separator = source_separation.SourceSeparator(config)
        self.vad_detector = vad.VoiceActivityDetector(config)
        self.diarizer = speaker_diarization.SpeakerDiarizer(config)
        self.asr_engine = asr.ASREngine(config)
        self.llm_extractor = extract_key_info.KeyInfoExtractor(config)
        self.llm_generator = generate_meeting_minutes.MeetingMinutesGenerator(config)
    
    def process_audio(self, audio_path: str, meeting_id: int) -> ProcessingResult:
        """
        Run complete pipeline on audio file
        
        Pipeline:
        1. Load audio → source_separation → clean audio
        2. VAD → voice segments
        3. Speaker diarization → segmented audio
        4. ASR → transcriptions
        5. LLM extract key info
        6. LLM generate meeting minutes
        7. Return ProcessingResult
        """
        logger.info(f"Starting audio processing for meeting {meeting_id}: {audio_path}")
        
        # Step 1: Source separation - remove noise and background music
        logger.info("Step 1: Running source separation...")
        clean_audio_path = self.source_separator.separate(audio_path)
        if not clean_audio_path:
            raise RuntimeError("Source separation failed")
        logger.info(f"Clean audio saved to: {clean_audio_path}")
        
        # Step 2: Voice Activity Detection
        logger.info("Step 2: Running VAD...")
        voice_segments = self.vad_detector.detect(clean_audio_path)
        if not voice_segments:
            raise RuntimeError("No voice segments detected")
        logger.info(f"Detected {len(voice_segments)} voice segments")
        
        # Step 3: Speaker Diarization
        logger.info("Step 3: Running speaker diarization...")
        speaker_segments = self.diarizer.diarize(clean_audio_path, voice_segments)
        logger.info(f"Identified {len(set(s.title() for s in speaker_segments))} speakers")
        
        # Step 4: ASR - Transcription
        logger.info("Step 4: Running ASR transcription...")
        audio_segments = []
        raw_transcription_parts = []
        
        for segment in speaker_segments:
            text = self.asr_engine.transcribe(segment.audio_path)
            if text:
                audio_segment = AudioSegment(
                    speaker_label=segment.speaker_label,
                    text=text,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    audio_path=segment.audio_path
                )
                audio_segments.append(audio_segment)
                raw_transcription_parts.append(f"{segment.speaker_label}: {text}")
        
        raw_transcription = "\n".join(raw_transcription_parts)
        logger.info(f"Transcribed {len(audio_segments)} segments")
        
        # Step 5: LLM Extract Key Info
        logger.info("Step 5: Extracting key info with LLM...")
        key_info = self.llm_extractor.extract(raw_transcription)
        key_decisions = key_info.get("key_decisions", [])
        tasks = key_info.get("tasks", [])
        logger.info(f"Extracted {len(key_decisions)} decisions, {len(tasks)} tasks")
        
        # Step 6: Generate Meeting Minutes
        logger.info("Step 6: Generating meeting minutes...")
        meeting_minutes = self.llm_generator.generate(
            transcription=raw_transcription,
            key_decisions=key_decisions,
            tasks=tasks,
            audio_segments=audio_segments
        )
        
        result = ProcessingResult(
            meeting_id=meeting_id,
            audio_segments=audio_segments,
            key_decisions=key_decisions,
            tasks=tasks,
            meeting_minutes=meeting_minutes,
            raw_transcription=raw_transcription
        )
        
        logger.info(f"Processing complete for meeting {meeting_id}")
        return result
