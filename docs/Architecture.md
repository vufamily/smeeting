# Architecture.md — Web-based Meeting Assistant

**Project:** Meeting Assistant  
**Location:** `C:\Users\SRV\workspace\meeting-assistant\`  
**Date:** 2026-05-07  
**Stack:** Python (vanilla HTML/CSS/JS frontend) | Python backend | SQLite | Gemma4 LLM @ 107.98.158.221:9229

---

## 1. System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MEETING ASSISTANT                                  │
│                        (Internal Company Network)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────┐        ┌───────────────────┐       ┌──────────────┐      │
│   │   CLIENT     │        │   BACKEND SERVER  │       │   LLM API   │      │
│   │  (Browser)   │◄──────►│    (Python/Flask) │◄────►│  (Gemma4)   │      │
│   │              │ HTTP   │                   │HTTP  │ 107.98.158  │      │
│   │  HTML/CSS/JS │  REST  │  AI Pipeline      │POST  │ .221:9229   │      │
│   └──────────────┘        └───────────────────┘       └──────────────┘      │
│                                  │                                          │
│                                  ▼                                          │
│                           ┌───────────────┐                                 │
│                           │   SQLite DB  │                                 │
│                           │ (meeting.db)  │                                 │
│                           └───────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Modules:**

| Module | Technology | Role |
|---|---|---|
| `frontend/` | HTML/CSS/JS | Giao diện web, gửi/nhận API |
| `backend/` | Python + Flask | Xử lý logic, điều phối pipeline |
| `ai_pipeline/` | Python + sherpa models | Xử lý audio (sep, VAD, diarization, ASR) |
| `llm_service/` | Python | Gọi Gemma4, tạo MoM |
| `database/` | SQLite | Lưu users, meetings, transcriptions, MoM |

---

## 2. Component Descriptions

### 2.1 Frontend (`frontend/`)

- **File:** `index.html`, `assets/css/style.css`, `assets/js/app.js`
- **Chức năng:**
  - Giao diện người dùng (đăng nhập, dashboard, upload/nhập audio, xem MoM)
  - Gửi file audio lên backend qua `fetch` API
  - Hiển thị kết quả transcription và Meeting of Minutes
  - Quản lý trạng thái UI (loading, success, error)
- **Không dùng framework JS** — vanilla JS để đơn giản hóa deployment

### 2.2 Backend AI Pipeline (`backend/ai_pipeline/`)

```
backend/ai_pipeline/
├── __init__.py
├── source_separator.py    # Loại bỏ noise, background music
├── vad.py                 # Voice Activity Detection (loại bỏ silence)
├── diarization.py         # Speaker segmentation & diarization
├── asr.py                 # Automatic Speech Recognition (transcription)
└── pipeline.py            # Điều phối pipeline, gộp các bước
```

| File | Model/Thư viện | Mô tả |
|---|---|---|
| `source_separator.py` | sherpa-nextgpt/source-sep | Tách voice khỏi noise/music |
| `vad.py` | sherpa-onnx/vad | Phát hiện giọng nói, cắt silence |
| `diarization.py` | sherpa-onnx/diarization | Phân đoạn speaker |
| `asr.py` | sherpa-onnx/paraformer | Nhận dạng giọng nói → text |
| `pipeline.py` | Điều phối pipeline | Chạy tuần tự các bước trên |

### 2.3 LLM Service (`backend/llm_service/`)

```
backend/llm_service/
├── __init__.py
├── gemma_client.py        # Gọi Gemma4 API
├── extract_decisions.py   # Bóc tách key decisions & tasks từ transcript
└── generate_mom.py        # Tổng hợp Meeting of Minutes
```

| File | Mô tả |
|---|---|
| `gemma_client.py` | HTTP POST đến `http://107.98.158.221:9229/v1/chat/completions` |
| `extract_decisions.py` | Prompt Gemma4 → trích xuất decisions, action items, owners |
| `generate_mom.py` | Prompt Gemma4 → tổng hợp MoM theo template chuẩn |

### 2.4 Database (`database/`)

- **File:** `database/schema.sql`, `database/db.py`, `database/models.py`
- **Engine:** SQLite (`meeting.db`)

### 2.5 API Server (`backend/`)

- **File:** `backend/app.py` (Flask app chính)
- **Routes:** Xem mục 4 — API Endpoints Design

---

## 3. Database Schema (SQLite)

### Bảng `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    email TEXT UNIQUE,
    role TEXT DEFAULT 'user',          -- 'admin' | 'user'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng `meetings`

```sql
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    scheduled_at DATETIME,
    duration_minutes INTEGER,
    status TEXT DEFAULT 'pending',      -- 'pending' | 'processing' | 'completed' | 'failed'
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng `settings`

```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng `audio_files`

```sql
CREATE TABLE audio_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id INTEGER REFERENCES meetings(id),
    filename TEXT NOT NULL,
    original_filename TEXT,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    duration_seconds REAL,
    sample_rate INTEGER,
    audio_format TEXT DEFAULT 'wav',
    status TEXT DEFAULT 'uploaded',     -- 'uploaded' | 'processing' | 'processed' | 'failed'
    error_message TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng `transcriptions`

```sql
CREATE TABLE transcriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    audio_file_id INTEGER REFERENCES audio_files(id),
    full_text TEXT,
    language TEXT DEFAULT 'vi',
    speaker_count INTEGER,
    segments_json TEXT,               -- JSON: [{"speaker": "SPEAKER_01", "text": "...", "start": 0.0, "end": 5.2}, ...]
    confidence REAL,
    processing_time_seconds REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Bảng `meeting_minutes`

```sql
CREATE TABLE meeting_minutes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transcription_id INTEGER REFERENCES transcriptions(id),
    meeting_id INTEGER REFERENCES meetings(id),
    summary TEXT,                      -- Tóm tắt ngắn
    key_decisions TEXT,                -- JSON: [{"decision": "...", "owner": "...", "due_date": "..."}]
    action_items TEXT,                 -- JSON: [{"task": "...", "owner": "...", "due_date": "...", "status": "open"}]
    key_discussion_points TEXT,        -- JSON: [...]
    participants TEXT,                 -- JSON: ["name", ...]
    location TEXT,
    mom_text TEXT,                     -- Văn bản MoM hoàn chỉnh (markdown)
    generated_by TEXT DEFAULT 'gemma4',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

---

## 4. API Endpoints Design (REST API)

Base URL: `http://<server>:5000/api/v1`

### Authentication

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/auth/register` | Đăng ký user |
| POST | `/auth/login` | Đăng nhập → JWT token |
| POST | `/auth/logout` | Đăng xuất |
| GET | `/auth/me` | Lấy thông tin user hiện tại |

### Meetings

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/meetings` | Danh sách meetings |
| POST | `/meetings` | Tạo meeting mới |
| GET | `/meetings/<id>` | Chi tiết meeting |
| PUT | `/meetings/<id>` | Cập nhật meeting |
| DELETE | `/meetings/<id>` | Xóa meeting |

### Audio Files

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/meetings/<id>/audio` | Upload audio cho meeting |
| GET | `/meetings/<id>/audio` | Danh sách audio của meeting |
| GET | `/audio/<id>` | Chi tiết audio |
| DELETE | `/audio/<id>` | Xóa audio |
| GET | `/audio/<id>/download` | Download audio file |

### Processing Pipeline

| Method | Endpoint | Mô tả |
|---|---|---|
| POST | `/audio/<id>/process` | Chạy full pipeline (sep→VAD→diar→ASR→LLM) |
| GET | `/audio/<id>/status` | Lấy trạng thái xử lý |

### Transcription & MoM

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/audio/<id>/transcription` | Lấy kết quả transcription |
| GET | `/audio/<id>/mom` | Lấy Meeting of Minutes |
| POST | `/audio/<id>/regenerate-mom` | Tạo lại MoM (sau khi edit transcript) |

### Settings

| Method | Endpoint | Mô tả |
|---|---|---|
| GET | `/settings` | Lấy tất cả settings |
| GET | `/settings/<key>` | Lấy một setting |
| PUT | `/settings/<key>` | Cập nhật setting |

---

## 5. Audio Processing Pipeline (Chi tiết)

### Pipeline Flow

```
[Audio Input]
     │
     ▼
┌────────────────────┐
│  1. SOURCE SEPARATOR │  ← Loại bỏ noise, music, reverb
│  sherpa source-sep  │
└─────────┬──────────┘
          ▼
┌────────────────────┐
│        2. VAD       │  ← Voice Activity Detection
│   (Silence removal) │     Cắt phần không có giọng nói
└─────────┬──────────┘
          ▼
┌────────────────────┐
│  3. SPEAKER DIAR.  │  ← Phân đoạn & gán nhãn speaker
│  (Who spoke when)  │     Output: SPEAKER_01, SPEAKER_02...
└─────────┬──────────┘
          ▼
┌────────────────────┐
│    4. ASR (Whisper) │  ← Transcription: audio → text
│  (Speech to text)   │     Gắn speaker label vào text
└─────────┬──────────┘
          ▼
     [Transcript]
          │
          ▼
┌────────────────────┐
│  5. LLM: Decisions │  ← Gemma4: bóc tách decisions & tasks
│   (Key extraction) │     Output: JSON decisions + action items
└─────────┬──────────┘
          ▼
┌────────────────────┐
│  6. LLM: Generate   │  ← Gemma4: tổng hợp MoM
│      MoM           │     Output: Markdown MoM document
└─────────┬──────────┘
          ▼
   [Meeting of Minutes]
```

### Module Details

#### 5.1 Source Separator (`source_separator.py`)

- **Input:** Raw audio file (wav/mp3/flac)
- **Output:** Clean voice audio
- **Model:** `sherpa-nextgpt/source-separator` (hoặc equivalent)
- **Xử lý:** Loại bỏ background noise, music, reverb
- **Output format:** WAV 16kHz mono

#### 5.2 VAD (`vad.py`)

- **Input:** Clean audio từ step 1
- **Output:** List of audio chunks có giọng nói
- **Model:** `sherpa-onnx/vad`
- **Threshold:** Có thể config trong `settings`
- **Min speech duration:** 0.3s (configurable)
- **Min silence duration:** 0.5s (để cắt)

#### 5.3 Speaker Diarization (`diarization.py`)

- **Input:** Audio chunks từ VAD
- **Output:** Speaker labels cho từng chunk
- **Model:** `sherpa-onnx/diarization`
- **Max speakers:** 10 (configurable)
- **Output:** Dict `{audio_chunk_path: speaker_id}`

#### 5.4 ASR (`asr.py`)

- **Input:** Audio chunks + speaker labels
- **Output:** Transcript segments JSON
- **Model:** `sherpa-onnx/paraformer-vi` (Vietnamese)
- **Language:** Vietnamese (`vi`) — có thể set qua settings
- **Output format:**
  ```json
  {
    "segments": [
      {
        "speaker": "SPEAKER_01",
        "text": "Chào mọi người, cuộc họp bắt đầu",
        "start": 0.0,
        "end": 5.2,
        "confidence": 0.95
      },
      {
        "speaker": "SPEAKER_02",
        "text": "Vâng, tôi đồng ý với đề xuất này",
        "start": 5.3,
        "end": 8.7,
        "confidence": 0.92
      }
    ],
    "full_text": "SPEAKER_01: Chào mọi người...\nSPEAKER_02: Vâng...",
    "language": "vi",
    "speaker_count": 2
  }
  ```

#### 5.5 LLM — Extract Decisions (`extract_decisions.py`)

- **Input:** `full_text` từ ASR
- **Output:** JSON decisions + action items
- **LLM:** Gemma4 @ `http://107.98.158.221:9229/v1/chat/completions`
- **Prompt:**

```
Bạn là AI assistant chuyên bóc tách thông tin từ biên bản họp.

Dưới đây là transcript cuộc họp:
---
{transcript}
---

Hãy trích xuất và trả về JSON theo format:
{
  "decisions": [
    {
      "decision": "Mô tả quyết định",
      "owner": "Người chịu trách nhiệm",
      "due_date": "YYYY-MM-DD hoặc null"
    }
  ],
  "action_items": [
    {
      "task": "Mô tả công việc",
      "owner": "Người phụ trách",
      "due_date": "YYYY-MM-DD hoặc null",
      "priority": "high|medium|low"
    }
  ],
  "participants": ["Danh sách người tham dự được nhắc đến"],
  "key_points": ["Các điểm thảo luận chính"]
}

Chỉ trả về JSON, không có text khác.
```

#### 5.6 LLM — Generate MoM (`generate_mom.py`)

- **Input:** `transcript` + `decisions` + `action_items`
- **Output:** Markdown Meeting of Minutes
- **LLM:** Gemma4
- **Prompt:**

```
Bạn là AI assistant chuyên viết biên bản họp (Meeting of Minutes).

Thông tin cuộc họp:
- Title: {meeting_title}
- Date: {meeting_date}
- Participants: {participants}

Transcript:
{transcript}

Decisions & Action Items:
{decisions_json}

Hãy viết biên bản họp theo format sau:

# BIÊN BẢN HỌP

## Thông tin cuộc họp
- **Ngày:** ...
- **Thời gian:** ...
- **Thành phần tham dự:** ...
- **Địa điểm:** ...

## Nội dung thảo luận
[Các điểm chính được thảo luận]

## Các quyết định
1. [Quyết định 1] - {owner} - Hạn: {due_date}
2. [Quyết định 2] - {owner} - Hạn: {due_date}

## Công việc cần làm
| STT | Công việc | Người phụ trách | Hạn | Độ ưu tiên |
|-----|-----------|----------------|-----|-----------|
| 1   | ...       | ...            | ... | ...       |

## Tóm tắt
[Tóm tắt ngắn gọn 2-3 câu]

---
Biên bản được tạo tự động bởi Meeting Assistant AI
```

---

## 6. Data Flow Diagram

```
User Action (Browser)
        │
        ▼
┌───────────────────┐
│  frontend/index.js │  ← Gửi HTTP request
└────────┬──────────┘
         │ fetch('/api/v1/...')
         ▼
┌───────────────────┐
│   backend/app.py   │  ← Flask routes
│   (API Gateway)    │
└────────┬──────────┘
         │
         ├─────────────────────────────────────┐
         │                                         │
         ▼                                         ▼
┌───────────────────┐                   ┌───────────────────┐
│   database/       │                   │  backend/         │
│   db.py          │                   │  ai_pipeline/     │
│   (CRUD ops)     │                   │  pipeline.py      │
└────────┬──────────┘                   └────────┬──────────┘
         │                                     │ sequential
         │                                     ▼
         │                          ┌───────────────────────┐
         │                          │  Source Separator     │
         │                          └───────────┬───────────┘
         │                                      ▼
         │                          ┌───────────────────────┐
         │                          │         VAD            │
         │                          └───────────┬───────────┘
         │                                      ▼
         │                          ┌───────────────────────┐
         │                          │  Speaker Diarization │
         │                          └───────────┬───────────┘
         │                                      ▼
         │                          ┌───────────────────────┐
         │                          │    ASR (Whisper)     │
         │                          └───────────┬───────────┘
         │                                      │
         │                                      ▼
         │                          ┌───────────────────────┐
         │                          │  LLM: Extract Info    │
         │                          └───────────┬───────────┘
         │                                      ▼
         │                          ┌───────────────────────┐
         │                          │  LLM: Generate MoM    │
         │                          └───────────┬───────────┘
         │                                      │
         ▼                                      ▼
┌───────────────────┐                   ┌───────────────────┐
│   SQLite DB       │                   │  Return Results  │
│  (Persist data)   │◄──────────────────│  (JSON response)  │
└───────────────────┘                   └───────────────────┘
```

---

## 7. Security Considerations (Internal Network)

> **Môi trường:** Chạy trên mạng nội bộ công ty. Các biện pháp sau được khuyến nghị:

### 7.1 Network Security

- Chỉ expose cổng 5000 (Flask) trên LAN interface, không expose ra internet
- Firewall rule: chỉ cho phép truy cập từ IP range nội bộ (`192.168.x.x` / `10.x.x.x`)
- Không mở cổng LLM service (`107.98.158.221:9229`) ra ngoài

### 7.2 Authentication & Authorization

- **JWT tokens** cho API authentication
- Token expiry: 24h (configurable)
- Role-based access: `admin` vs `user`
- Passwords hashed bằng `bcrypt` hoặc `argon2`

### 7.3 Data Security

- Audio files lưu trong thư mục có quyền đọc/ghi riêng (không public)
- File upload validation: chỉ cho phép `wav`, `mp3`, `flac`, `m4a`
- Max file size: 500MB (configurable)
- Không lưu plaintext sensitive info trong DB

### 7.4 File Structure

```
meeting-assistant/
├── frontend/
│   ├── index.html
│   └── assets/
│       ├── css/style.css
│       └── js/app.js
├── backend/
│   ├── app.py                 # Flask app (main entry)
│   ├── config.py              # Configuration
│   ├── routes/                # API route handlers
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── meetings.py
│   │   ├── audio.py
│   │   └── settings.py
│   ├── ai_pipeline/
│   │   ├── __init__.py
│   │   ├── source_separator.py
│   │   ├── vad.py
│   │   ├── diarization.py
│   │   ├── asr.py
│   │   └── pipeline.py
│   ├── llm_service/
│   │   ├── __init__.py
│   │   ├── gemma_client.py
│   │   ├── extract_decisions.py
│   │   └── generate_mom.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db.py
│   │   ├── models.py
│   │   └── schema.sql
│   └── utils/
│       ├── __init__.py
│       ├── file_handler.py
│       └── validators.py
├── database/
│   └── meeting.db
├── uploads/                    # Audio uploads (not in git)
├── docs/
│   ├── Architecture.md
│   └── SRS.md
├── requirements.txt
├── .env.example
└── README.md
```

---

## 8. Configuration (`.env`)

```env
# Server
HOST=0.0.0.0
PORT=5000
DEBUG=false

# Database
DB_PATH=database/meeting.db

# LLM
LLM_BASE_URL=http://107.98.158.221:9229/v1
LLM_MODEL=gemma4
LLM_API_KEY=   # internal, leave empty if no auth

# Audio Processing
MAX_UPLOAD_SIZE_MB=500
ALLOWED_AUDIO_FORMATS=wav,mp3,flac,m4a
VAD_THRESHOLD=0.5
VAD_MIN_SPEECH_DURATION=0.3
VAD_MIN_SILENCE_DURATION=0.5
MAX_SPEAKERS=10
ASR_LANGUAGE=vi

# JWT
JWT_SECRET_KEY=<random-secret-key>
JWT_EXPIRY_HOURS=24

# Upload
UPLOAD_FOLDER=uploads
```

---

*Document version 1.0 — 2026-05-07*
