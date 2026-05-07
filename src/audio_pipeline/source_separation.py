"""
Source Separation Module - Remove noise and background music using Demucs
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class SourceSeparator:
    """Uses Demucs (htdemucs) to separate vocals from accompaniment"""
    
    def __init__(self, config: dict):
        self.config = config
        self.model_name = config.get("source_separation", {}).get("model", "htdemucs")
        self.device = config.get("source_separation", {}).get("device", "cpu")
        self.output_dir = config.get("source_separation", {}).get("output_dir", "data/separated")
        
        # Lazy import demucs to avoid heavy import at module load
        self._demucs_available = None
    
    def _check_demucs(self) -> bool:
        """Check if demucs is available"""
        if self._demucs_available is None:
            try:
                from demucs import separate
                self._demucs_available = True
            except ImportError:
                logger.warning("Demucs not installed. Run: pip install demucs")
                self._demucs_available = False
        return self._demucs_available
    
    def separate(self, audio_path: str) -> Optional[str]:
        """
        Separate audio into stems: vocals, accompaniment, bass, drums
        
        Args:
            audio_path: Path to input audio file
            
        Returns:
            Path to clean vocal track, or None if failed
        """
        if not self._check_demucs():
            logger.warning("Demucs not available, returning original audio")
            return audio_path
        
        from demucs import separate
        import torch
        
        logger.info(f"Separating audio with model: {self.model_name}")
        
        # Create output directory
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Get audio filename without extension
        audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
        
        try:
            # Run demucs separation
            # Results saved to {output_dir}/{model}/{audio_basename}
            separated = separate.main(
                argv=[
                    "--mp3",  # output as mp3
                    "--models", self.model_name,
                    "--device", self.device,
                    "-o", self.output_dir,
                    audio_path
                ]
            )
            
            # Find the vocal track path
            # Demucs output structure: output_dir/model/audio_file/vocals.mp3
            vocal_path = os.path.join(
                self.output_dir,
                self.model_name,
                audio_basename,
                "vocals.mp3"
            )
            
            if os.path.exists(vocal_path):
                logger.info(f"Vocal track extracted: {vocal_path}")
                return vocal_path
            else:
                logger.error(f"Vocal track not found at: {vocal_path}")
                return None
                
        except Exception as e:
            logger.error(f"Source separation failed: {e}")
            return None
    
    def separate_to_wav(self, audio_path: str) -> Optional[str]:
        """Same as separate but output as WAV for better compatibility"""
        if not self._check_demucs():
            logger.warning("Demucs not available, returning original audio")
            return audio_path
        
        from demucs import separate
        
        logger.info(f"Separating audio to WAV with model: {self.model_name}")
        
        os.makedirs(self.output_dir, exist_ok=True)
        audio_basename = os.path.splitext(os.path.basename(audio_path))[0]
        
        try:
            separated = separate.main(
                argv=[
                    "--wav",  # output as wav
                    "--models", self.model_name,
                    "--device", self.device,
                    "-o", self.output_dir,
                    audio_path
                ]
            )
            
            vocal_path = os.path.join(
                self.output_dir,
                self.model_name,
                audio_basename,
                "vocals.wav"
            )
            
            if os.path.exists(vocal_path):
                logger.info(f"Vocal track extracted: {vocal_path}")
                return vocal_path
            else:
                logger.error(f"Vocal track not found at: {vocal_path}")
                return None
                
        except Exception as e:
            logger.error(f"Source separation to WAV failed: {e}")
            return None
