"""
Meeting Assistant - AI-Powered Meeting Transcription and Minutes Generation

Base Configuration
"""

import os

# Base paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
CONFIG_DIR = os.path.join(BASE_DIR, "config")

# Storage paths
STORAGE = {
    "upload_dir": os.path.join(DATA_DIR, "uploads"),
    "output_dir": os.path.join(DATA_DIR, "outputs"),
    "separated_dir": os.path.join(DATA_DIR, "separated"),
    "segments_dir": os.path.join(DATA_DIR, "segments"),
    "temp_dir": os.path.join(DATA_DIR, "temp"),
    "logs_dir": os.path.join(BASE_DIR, "logs"),
}

# Source Separation (Demucs)
SOURCE_SEPARATION = {
    "model": "htdemucs",  # or "htdemucs_ft" for higher quality
    "device": "cpu",  # or "cuda" if GPU available
    "output_dir": os.path.join(DATA_DIR, "separated"),
}

# Voice Activity Detection (Silero VAD)
VAD = {
    "model_path": "models/silero_vad.jit",
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "min_silence_duration_ms": 200,
    "window_size_samples": 512,
    "sampling_rate": 16000,
}

# Speaker Diarization (PyAnote)
SPEAKER_DIARIZATION = {
    "model": "pyannote",
    "min_speakers": 1,
    "max_speakers": 10,
    "huggingface_token": os.environ.get("HF_TOKEN", ""),  # Required for pyannote
}

# ASR (Sherpa Paraformer)
ASR = {
    "model_path": "models/sherpa-paraformer",
    "quantized": True,
    "use_gpu": False,
    "language": "vi",  # Vietnamese
}

# LLM Configuration (Gemma4)
LLM = {
    "endpoint": "http://107.98.158.221:9229/v1",
    "model": "gemma4",
    "api_key": os.environ.get("LLM_API_KEY", "dummy"),
    "temperature": 0.3,
    "max_tokens": 4096,
    "timeout": 90,
}

# Flask Configuration
FLASK = {
    "host": "0.0.0.0",
    "port": 5000,
    "debug": False,
    "max_content_length": 500 * 1024 * 1024,  # 500MB max file size
}

# Database Configuration
DATABASE = {
    "url": os.environ.get("DATABASE_URL", "sqlite:///data/meeting_assistant.db"),
    "echo": False,
}

# Logging Configuration
LOGGING = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": os.path.join(BASE_DIR, "logs", "meeting_assistant.log"),
}

# Combine all config
CONFIG = {
    "storage": STORAGE,
    "source_separation": SOURCE_SEPARATION,
    "vad": VAD,
    "speaker_diarization": SPEAKER_DIARIZATION,
    "asr": ASR,
    "llm": LLM,
    "flask": FLASK,
    "database": DATABASE,
    "logging": LOGGING,
}
