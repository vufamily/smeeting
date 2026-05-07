"""
Core Service: AudioProcessingService
Business logic for audio processing pipeline.
No direct dependencies on infrastructure — uses injected components.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

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


class AudioProcessingService:
    """
    Orchestrates the AI audio processing pipeline.

    This service coordinates:
    1. Source Separation (remove noise/music)
    2. Voice Activity Detection (find speech segments)
    3. Speaker Diarization (identify who spoke when)
    4. ASR Transcription (speech to text)
    5. LLM Key Info Extraction (decisions & tasks)
    6. LLM Meeting Minutes Generation

    Dependencies are injected to maintain clean architecture:
    - source_separator, vad_detector, diarizer, asr_engine
    - llm_extractor, llm_generator
    """

    def __init__(self, config: Dict, **kwargs):
        """
        Initialize processing service.

        Args:
            config: Application configuration dict
            **kwargs: Injected pipeline components (optional, lazy-loaded)
        """
        self.config = config
        self._source_separator = kwargs.get('source_separator')
        self._vad_detector = kwargs.get('vad_detector')
        self._diarizer = kwargs.get('diarizer')
        self._asr_engine = kwargs.get('asr_engine')
        self._llm_extractor = kwargs.get('llm_extractor')
        self._llm_generator = kwargs.get('llm_generator')
        self._initialized = False

    def _lazy_init(self):
        """Lazy initialization of pipeline components."""
        if self._initialized:
            return

        logger.info("Initializing audio processing pipeline components...")

        try:
            # Import infrastructure implementations lazily
            from infrastructure.ai.speech_to_text import SpeechToTextEngine
            from infrastructure.ai.speaker_diarization import SpeakerDiarizationEngine
            from infrastructure.ai.llm_integration import LLMIntegration

            self._asr_engine = SpeechToTextEngine(self.config)
            self._diarizer = SpeakerDiarizationEngine(self.config)
            self._llm_extractor = LLMIntegration(self.config)
            self._llm_generator = LLMIntegration(self.config)

            self._initialized = True
            logger.info("Pipeline components initialized successfully")

        except ImportError as e:
            logger.warning(f"Some pipeline components not available: {e}")
            self._initialized = True

    def process_audio(self, audio_path: str, meeting_id: int) -> ProcessingResult:
        """
        Run complete processing pipeline on audio file.

        Args:
            audio_path: Path to input audio file
            meeting_id: Meeting ID for associating results

        Returns:
            ProcessingResult with all extracted information
        """
        self._lazy_init()

        logger.info(f"Starting audio processing for meeting {meeting_id}")
        logger.info(f"Input file: {audio_path}")

        # For now, return a placeholder result
        # Full implementation integrates with actual AI pipeline
        result = ProcessingResult(
            meeting_id=meeting_id,
            audio_segments=[],
            key_decisions=[],
            tasks=[],
            meeting_minutes="",
            raw_transcription=""
        )

        return result

    def process_audio_simple(self, audio_path: str, meeting_id: int) -> dict:
        """
        Simplified processing — returns dict instead of dataclass.
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
