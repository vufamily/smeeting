"""
Infrastructure AI: Speaker Diarization Engine
Wraps speaker diarization module.
"""

import os
import logging
from typing import List

logger = logging.getLogger(__name__)


class SpeakerDiarizationEngine:
    """Speaker diarization using pyannote."""

    def __init__(self, config: dict):
        self.config = config
        diar_config = config.get("speaker_diarization", {})
        self.model_type = diar_config.get("model", "pyannote")
        self.min_speakers = diar_config.get("min_speakers", 1)
        self.max_speakers = diar_config.get("max_speakers", 10)
        self.huggingface_token = diar_config.get("huggingface_token", None)
        self._pipeline = None

    def _load_model(self):
        """Lazy load pyannote pipeline."""
        if self._pipeline is None:
            try:
                from pyannote.audio import Pipeline
                if self.huggingface_token:
                    self._pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=self.huggingface_token
                    )
                else:
                    logger.warning("No HuggingFace token for pyannote")
            except Exception as e:
                logger.warning(f"Could not load pyannote model: {e}")
                self._pipeline = None

    def diarize(self, audio_path: str, voice_segments: List) -> List:
        """
        Assign speaker labels to voice segments.

        Args:
            audio_path: Path to audio file
            voice_segments: List of voice segment dicts with start/end times

        Returns:
            List of dicts with speaker_label added
        """
        self._load_model()

        if self._pipeline is None:
            return self._fallback_diarization(voice_segments)

        try:
            import torch
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            self._pipeline.to(device)

            diarization = self._pipeline(
                audio_path,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers
            )

            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append({
                    "speaker_label": str(speaker),
                    "start_time": turn.start,
                    "end_time": turn.end,
                    "audio_path": audio_path
                })

            return segments

        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return self._fallback_diarization(voice_segments)

    def _fallback_diarization(self, voice_segments: List) -> List:
        """Fallback: label segments sequentially as Speaker 1, 2, 3..."""
        segments = []
        speaker_count = 0

        for seg in voice_segments:
            duration = seg.get("end", 0) - seg.get("start", 0)
            if duration > 30:
                speaker_count = (speaker_count % 3) + 1

            segments.append({
                "speaker_label": f"Speaker {speaker_count or 1}",
                "start_time": seg.get("start", 0.0),
                "end_time": seg.get("end", 0.0),
                "audio_path": seg.get("audio_path", "")
            })

        return segments
