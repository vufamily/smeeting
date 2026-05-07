"""
Speaker Diarization Module - Identify and separate speakers in audio
"""

import os
import logging
from typing import List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SpeakerSegment:
    """Represents an audio segment attributed to a specific speaker"""
    speaker_label: str
    start_time: float
    end_time: float
    audio_path: str


class SpeakerDiarizer:
    """Segments audio by speaker using clustering"""
    
    def __init__(self, config: dict):
        self.config = config
        diar_config = config.get("speaker_diarization", {})
        self.model_type = diar_config.get("model", "pyannote")
        self.min_speakers = diar_config.get("min_speakers", 1)
        self.max_speakers = diar_config.get("max_speakers", 10)
        self.huggingface_token = diar_config.get("huggingface_token", None)
        
        self._embedding_model = None
    
    def _get_embedding_model(self):
        """Lazy load embedding model for speaker verification"""
        if self._embedding_model is None:
            try:
                # pyannote speaker embedding model
                from pyannote.audio import Pipeline
                
                if self.huggingface_token:
                    self._embedding_model = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=self.huggingface_token
                    )
                else:
                    logger.warning("No HuggingFace token provided for pyannote")
                    self._embedding_model = None
                    
            except Exception as e:
                logger.warning(f"Could not load pyannote model: {e}")
                self._embedding_model = None
        
        return self._embedding_model
    
    def diarize(self, audio_path: str, voice_segments: List) -> List[SpeakerSegment]:
        """
        Assign speaker labels to voice segments
        
        Args:
            audio_path: Path to audio file
            voice_segments: List of VoiceSegment from VAD
            
        Returns:
            List of SpeakerSegment with assigned speaker labels
        """
        logger.info(f"Running speaker diarization on {len(voice_segments)} segments")
        
        pipeline = self._get_embedding_model()
        
        if pipeline is None:
            # Fallback: assign generic "Speaker 1", "Speaker 2", etc.
            logger.warning("No diarization model available, using generic labels")
            return self._fallback_diarization(voice_segments)
        
        try:
            # Run pyannote diarization
            import torch
            
            device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            pipeline.to(device)
            
            # pyannote expects wav file
            diarization = pipeline(
                audio_path,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers
            )
            
            # Map pyannote segments to our format
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                segments.append(SpeakerSegment(
                    speaker_label=str(speaker),
                    start_time=turn.start,
                    end_time=turn.end,
                    audio_path=self._extract_segment_audio(audio_path, turn.start, turn.end)
                ))
            
            logger.info(f"Diarization complete: {len(segments)} segments, {len(set(s.speaker_label for s in segments))} speakers")
            return segments
            
        except Exception as e:
            logger.error(f"Diarization failed: {e}")
            return self._fallback_diarization(voice_segments)
    
    def _fallback_diarization(self, voice_segments: List) -> List[SpeakerSegment]:
        """Simple fallback: label segments sequentially as Speaker 1, 2, 3..."""
        segments = []
        speaker_count = 0
        current_speaker = "Speaker 1"
        
        for seg in voice_segments:
            # Alternate speakers for non-overlapping segments
            if seg.end_time - seg.start_time > 30:  # Long segment
                speaker_count = (speaker_count % 3) + 1
                current_speaker = f"Speaker {speaker_count}"
            
            segments.append(SpeakerSegment(
                speaker_label=current_speaker,
                start_time=seg.start_time,
                end_time=seg.end_time,
                audio_path=self._extract_segment_audio(None, seg.start_time, seg.end_time)
            ))
        
        return segments
    
    def _extract_segment_audio(self, audio_path: str, start: float, end: float) -> str:
        """Extract audio segment to separate file"""
        if audio_path is None:
            return ""
        
        try:
            import librosa
            import soundfile as sf
            
            # Load audio
            y, sr = librosa.load(audio_path, sr=16000, offset=start, duration=end-start)
            
            # Create unique filename
            output_path = f"data/segments/seg_{int(start*1000)}_{int(end*1000)}.wav"
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            
            # Save segment
            sf.write(output_path, y, sr)
            
            return output_path
            
        except Exception as e:
            logger.warning(f"Could not extract audio segment: {e}")
            return ""
    
    def get_speaker_count(self, audio_path: str) -> int:
        """Quick estimate of number of speakers"""
        pipeline = self._get_embedding_model()
        
        if pipeline is None:
            return 2  # Default assumption
        
        try:
            diarization = pipeline(audio_path)
            speakers = set()
            for _, _, speaker in diarization.itertracks(yield_label=True):
                speakers.add(str(speaker))
            return len(speakers)
        except:
            return 2
