"""
Automatic Speech Recognition Module - Transcribe audio using sherpa-paraformer
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class ASREngine:
    """Offline ASR using sherpa-paraformer model"""
    
    def __init__(self, config: dict):
        self.config = config
        asr_config = config.get("asr", {})
        self.model_path = asr_config.get("model_path", "models/sherpa-paraformer")
        self.quantized = asr_config.get("quantized", True)
        self.use_gpu = asr_config.get("use_gpu", False)
        self.language = asr_config.get("language", "vi")  # Vietnamese default
        
        self._recognizer = None
        self._context = None
    
    def _load_model(self):
        """Lazy load sherpa-paraformer model"""
        if self._recognizer is None:
            try:
                import sherpa_paraformer
                
                logger.info(f"Loading sherpa-paraformer model from: {self.model_path}")
                
                # Initialize recognizer
                self._recognizer = sherpa_paraformer.Recognizer(
                    model=self.model_path,
                    use_quantized=self.quantized,
                    use_gpu=self.use_gpu
                )
                
                logger.info("Sherpa-paraformer model loaded successfully")
                
            except ImportError:
                logger.warning("sherpa-paraformer not installed. Run: pip install sherpa-paraformer")
                raise
            except Exception as e:
                logger.error(f"Failed to load sherpa model: {e}")
                raise
    
    def transcribe(self, audio_path: str) -> Optional[str]:
        """
        Transcribe audio file to text
        
        Args:
            audio_path: Path to audio file (wav/mp3)
            
        Returns:
            Transcribed text or None if failed
        """
        if not audio_path or not os.path.exists(audio_path):
            logger.warning(f"Audio file not found: {audio_path}")
            return ""
        
        self._load_model()
        
        try:
            import torch
            
            # Create stream
            stream = self._recognizer.create_stream()
            
            # Process audio file
            if audio_path.endswith(".wav"):
                import scipy.io.wavfile as wavfile
                sr, waveform = wavfile.read(audio_path)
                # Normalize to [-1, 1]
                waveform = waveform.astype(torch.float32) / 32768.0
            else:
                # Use librosa for mp3 and other formats
                import librosa
                waveform, sr = librosa.load(audio_path, sr=16000)
                waveform = waveform.astype(torch.float32)
            
            # Accept wave samples
            stream.accept_waveform(sr, waveform)
            
            # Process
            tail_paddings = torch.zeros(self.recognizer.config.model_config.tail_paddings)
            stream.accept_waveform(sr, tail_paddings.numpy())
            
            # Get result
            result = self._recognizer.decode(stream)
            
            text = result.text.strip()
            logger.debug(f"Transcribed {len(text)} chars from {audio_path}")
            
            return text
            
        except Exception as e:
            logger.error(f"Transcription failed for {audio_path}: {e}")
            return ""
    
    def transcribe_segments(self, audio_segments: list) -> list:
        """
        Transcribe multiple audio segments
        
        Args:
            audio_segments: List of audio file paths or dicts with 'path' key
            
        Returns:
            List of transcribed texts
        """
        results = []
        
        for i, segment in enumerate(audio_segments):
            if isinstance(segment, dict):
                path = segment.get("path", "")
            else:
                path = segment
            
            text = self.transcribe(path)
            results.append({
                "segment_index": i,
                "text": text,
                "path": path
            })
            
            if (i + 1) % 10 == 0:
                logger.info(f"Transcribed {i+1}/{len(audio_segments)} segments")
        
        return results
    
    @property
    def recognizer(self):
        """Lazy load and return recognizer instance"""
        self._load_model()
        return self._recognizer
