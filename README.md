# Meeting Assistant - AI Backend

AI-powered meeting transcription and minutes generation system.

## Features

- **Source Separation**: Remove noise and background music using Demucs (htdemucs)
- **Voice Activity Detection**: Detect speech segments using Silero VAD
- **Speaker Diarization**: Identify and separate speakers using PyAnote
- **Speech-to-Text**: Offline ASR using sherpa-paraformer (Vietnamese)
- **Key Info Extraction**: Extract decisions and tasks using Gemma4 LLM
- **Meeting Minutes**: Generate formatted minutes using Gemma4 LLM

## Project Structure

```
meeting-assistant/
├── config/
│   └── config.py           # Main configuration
├── src/
│   ├── __init__.py
│   ├── processor.py       # Main orchestrator
│   ├── audio_pipeline/    # Audio processing modules
│   │   ├── __init__.py
│   │   ├── source_separation.py
│   │   ├── vad.py
│   │   ├── speaker_diarization.py
│   │   └── asr.py
│   ├── llm/              # LLM processing
│   │   ├── __init__.py
│   │   ├── extract_key_info.py
│   │   └── generate_meeting_minutes.py
│   ├── models/           # Database models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── meeting.py
│   │   ├── audio_file.py
│   │   ├── transcription.py
│   │   └── meeting_minutes.py
│   ├── services/         # Business logic
│   │   ├── __init__.py
│   │   └── processing_service.py
│   └── api/             # Flask REST API
│       └── __init__.py
├── data/                 # Data storage
├── logs/                 # Application logs
├── main.py              # Entry point
├── requirements.txt     # Python dependencies
└── README.md
```

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Edit `config/config.py` or set environment variables:

```bash
# LLM Configuration
export LLM_API_KEY=your_api_key

# HuggingFace (for PyAnote speaker diarization)
export HF_TOKEN=your_hf_token

# Database
export DATABASE_URL=sqlite:///data/meeting_assistant.db
```

## Usage

### Run API Server

```bash
python main.py
```

### Process Audio Programmatically

```python
from src.processor import AudioProcessor
from config.config import CONFIG

processor = AudioProcessor(CONFIG)
result = processor.process_audio("path/to/audio.mp3", meeting_id=1)

print(result.meeting_minutes)
print(result.key_decisions)
print(result.tasks)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/meetings/<id>/process` | POST | Upload and process audio |
| `/api/meetings/<id>/status` | GET | Get processing status |
| `/api/meetings/<id>/minutes` | GET | Get meeting minutes |
| `/api/meetings/<id>/transcriptions` | GET | Get transcriptions |
| `/api/config/models` | GET | Get model status |

## Processing Pipeline

1. **Source Separation** (Demucs): Remove background music and noise
2. **VAD** (Silero): Detect voice activity segments
3. **Speaker Diarization** (PyAnote): Identify speakers
4. **ASR** (Sherpa Paraformer): Transcribe speech to text
5. **Key Info Extraction** (Gemma4): Extract decisions and tasks
6. **Minutes Generation** (Gemma4): Create formatted meeting minutes

## Requirements

- Python 3.9+
- FFmpeg (for audio processing)
- CUDA (optional, for GPU acceleration)
