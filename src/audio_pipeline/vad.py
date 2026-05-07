"""
Voice Activity Detection Module - Detect speech segments using Silero VAD
"""

import os
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VoiceSegment:
    """Represents a detected voice segment"""
    start_time: float
    end_time: float
    confidence: float = 1.0


class VoiceActivityDetector:
    """Uses Silero VAD to detect voice activity in audio"""
    
    def __init__(self, config: dict):
        self.config = config
        vad_config = config.get("vad", {})
        self.model_path = vad_config.get("model_path", "models/silero_vad.jit")
        self.threshold = vad_config.get("threshold", 0.5)
        self.min_speech_duration = vad_config.get("min_speech_duration_ms", 250)
        self.min_silence_duration = vad_config.get("min_silence_duration_ms", 200)
        self.window_size = vad_config.get("window_size_samples", 512)
        self.sampling_rate = vad_config.get("sampling_rate", 16000)
        
        self._model = None
        self._torch = None
    
    def _load_model(self):
        """Lazy load Silero VAD model"""
        if self._model is None:
            try:
                import torch
                self._torch = torch
                
                # Try to load from local path first
                if os.path.exists(self.model_path):
                    self._model = torch.jit.load(self.model_path)
                    logger.info(f"Loaded Silero VAD from local path: {self.model_path}")
                else:
                    # Download from torch.hub
                    logger.info("Downloading Silero VAD model...")
                    self._model = torch.hub.load(
                        "snakers4/silero-vad",
                        "silero_vad",
                        trust_repo=True
                    )
                    logger.info("Silero VAD model loaded from torch.hub")
                    
            except Exception as e:
                logger.error(f"Failed to load Silero VAD model: {e}")
                raise
    
    def detect(self, audio_path: str) -> List[VoiceSegment]:
        """
        Detect voice segments in audio file
        
        Args:
            audio_path: Path to audio file
            
        Returns:
            List of VoiceSegment objects with start/end times
        """
        self._load_model()
        
        import torch
        import torchaudio
        
        logger.info(f"Running VAD on: {audio_path}")
        
        # Load audio
        waveform, sample_rate = torchaudio.load(audio_path)
        
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = waveform.mean(dim=0, keepdim=True)
        
        # Resample to 16kHz if needed
        if sample_rate != self.sampling_rate:
            logger.info(f"Resampling from {sample_rate}Hz to {self.sampling_rate}Hz")
            resampler = torchaudio.transforms.Resample(
                orig_freq=sample_rate,
                new_freq=self.sampling_rate
            )
            waveform = resampler(waveform)
        
        # Convert to numpy for processing
        waveform = waveform.squeeze().numpy()
        
        # Get speech timestamps using Silero VAD
        try:
            from scipy.io import wavfile
            import numpy as np
            
            # Save temp file for VAD (Silero expects wav)
            temp_wav = "data/temp_vad_input.wav"
            os.makedirs(os.path.dirname(temp_wav), exist_ok=True)
            wavfile.write(temp_wav, self.sampling_rate, waveform)
            
            # Run Silero VAD
            speech_timestamps = self._model(
                torch.from_numpy(np.array(waveform)).unsqueeze(0),
                sampling_rate=self.sampling_rate,
                threshold=self.threshold,
                min_speech_duration_ms=self.min_speech_duration,
                min_silence_duration_ms=self.min_silence_duration
            )
            
            segments = []
            for ts in speech_timestamps:
                segments.append(VoiceSegment(
                    start_time=ts.get("start", 0.0) / 1000.0,  # Convert ms to seconds
                    end_time=ts.get("end", 0.0) / 1000.0,
                    confidence=ts.get("conf", 1.0)
                ))
            
            logger.info(f"Detected {len(segments)} voice segments")
            return segments
            
        except Exception as e:
            logger.error(f"VAD detection failed: {e}")
            # Fallback: return entire audio as one segment
            logger.warning("Falling back to full audio as single segment")
            return [VoiceSegment(start_time=0.0, end_time=len(waveform)/self.sampling_rate)]
    
    def detect_with_timestamps(self, audio_path: str) -> List[dict]:
        """
        Alternative method returning dict format with timestamps in ms
        
        Returns:
            List of dicts: [{"start": ms, "end": ms, "conf": float}, ...]
        """
        segments = self.detect(audio_path)
        return [
            {
                "start": int(seg.start_time * 1000),
                "end": int(seg.end_time * 1000),
                "conf": seg.confidence
            }
            for seg in segments
        ]
