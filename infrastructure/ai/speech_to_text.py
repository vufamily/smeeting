"""
Infrastructure AI: Speech-to-Text Engine
Wraps ASR module for speech recognition.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SpeechToTextEngine:
    """Speech-to-text using sherpa-paraformer."""

    def __init__(self, config: dict):
        self.config = config
        asr_config = config.get("asr", {})
        self.model_path = asr_config.get("model_path", "models/sherpa-paraformer")
        self.quantized = asr_config.get("quantized", True)
        self.use_gpu = asr_config.get("use_gpu", False)
        self.language = asr_config.get("language", "vi")
        self._recognizer = None

    def _load_model(self):
        """Lazy load the ASR model."""
        if self._recognizer is None:
            try:
                import sherpa_paraformer
                logger.info(f"Loading sherpa-paraformer from: {self.model_path}")
                self._recognizer = sherpa_paraformer.Recognizer(
                    model=self.model_path,
                    use_quantized=self.quantized,
                    use_gpu=self.use_gpu
                )
                logger.info("ASR model loaded successfully")
            except ImportError:
                logger.warning("sherpa-paraformer not installed. ASR will return empty results.")
                self._recognizer = None
            except Exception as e:
                logger.error(f"Failed to load ASR model: {e}")
                self._recognizer = None

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text or empty string
        """
        if not audio_path or not os.path.exists(audio_path):
            logger.warning(f"Audio file not found: {audio_path}")
            return ""

        self._load_model()

        if self._recognizer is None:
            return ""

        try:
            import torch

            stream = self._recognizer.create_stream()

            if audio_path.endswith(".wav"):
                import scipy.io.wavfile as wavfile
                sr, waveform = wavfile.read(audio_path)
                waveform = waveform.astype(torch.float32) / 32768.0
            else:
                import librosa
                waveform, sr = librosa.load(audio_path, sr=16000)
                waveform = waveform.astype(torch.float32)

            stream.accept_waveform(sr, waveform)
            tail_paddings = torch.zeros(self.recognizer.config.model_config.tail_paddings)
            stream.accept_waveform(sr, tail_paddings.numpy())
            result = self._recognizer.decode(stream)

            return result.text.strip()

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return ""

    @property
    def recognizer(self):
        self._load_model()
        return self._recognizer
