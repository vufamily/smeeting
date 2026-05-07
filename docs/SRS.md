# SRS.md — Software Requirements Specification
# Web-based Meeting Assistant

**Project:** Meeting Assistant  
**Location:** `C:\Users\SRV\workspace\meeting-assistant\`  
**Date:** 2026-05-07  
**Version:** 1.0

---

## 1. Introduction

### 1.1 Purpose

Meeting Assistant là ứng dụng web nội bộ giúp đội ngũ làm việc hiệu quả hơn bằng cách tự động hóa quy trình xử lý biên bản họp (Meeting of Minutes). Hệ thống tiếp nhận file audio từ cuộc họp, xử lý qua pipeline AI (tách noise, nhận dạng giọng nói, phân đoạn speaker, transcription), sau đó dùng LLM (Gemma4) để trích xuất quyết định, công việc và tổng hợp thành biên bản họp hoàn chỉnh.

### 1.2 Scope

| STT | Module | Mô tả |
|---|---|---|
| 1 | Audio Upload | Người dùng upload hoặc record audio cuộc họp |
| 2 | AI Pipeline | Xử lý audio tự động: source separation → VAD → diarization → ASR |
| 3 | LLM Processing | Gemma4 trích xuất decisions + tạo MoM |
| 4 | Web UI | Giao diện dashboard, quản lý meeting, xem MoM |
| 5 | Database | Lưu users, meetings, audio, transcripts, MoM |

### 1.3 Target Users

- **Nhân viên văn phòng:** Upload audio cuộc họp, xem biên bản
- **Quản lý:** Review biên bản, phân công task từ MoM
- **Admin:** Quản lý users, settings hệ thống

---

## 2. Functional Requirements (FR)

### Authentication & User Management

| ID | Requirement | Priority |
|---|---|---|
| FR-1.1 | Hệ thống cho phép đăng ký tài khoản mới (username, password, full name, email) | Must |
| FR-1.2 | Hệ thống cho phép đăng nhập, trả về JWT token | Must |
| FR-1.3 | JWT token có thời hạn 24h, được dùng cho tất cả API requests | Must |
| FR-1.4 | Chỉ admin mới được quản lý users (thêm, xóa, phân quyền) | Must |
| FR-1.5 | Users có thể xem và cập nhật profile của mình | Should |

### Meeting Management

| ID | Requirement | Priority |
|---|---|---|
| FR-2.1 | Users có thể tạo meeting mới (title, description, scheduled_at, duration) | Must |
| FR-2.2 | Users có thể xem danh sách meetings của mình (phân trang) | Must |
| FR-2.3 | Users có thể cập nhật thông tin meeting | Should |
| FR-2.4 | Users có thể xóa meeting (xóa cả audio + transcription liên quan) | Must |
| FR-2.5 | Meeting có các trạng thái: `pending`, `processing`, `completed`, `failed` | Must |

### Audio File Management

| ID | Requirement | Priority |
|---|---|---|
| FR-3.1 | Users có thể upload audio file cho một meeting (wav, mp3, flac, m4a) | Must |
| FR-3.2 | Max file size upload: 500MB (configurable) | Must |
| FR-3.3 | Hệ thống validate file format và hiển thị lỗi nếu không hợp lệ | Must |
| FR-3.4 | Users có thể xóa audio file | Must |
| FR-3.5 | Users có thể download audio file đã upload | Must |

### AI Audio Processing Pipeline

| ID | Requirement | Priority |
|---|---|---|
| FR-4.1 | **Source Separation:** Loại bỏ noise, background music từ audio | Must |
| FR-4.2 | **VAD (Voice Activity Detection):** Phát hiện và cắt phần silence | Must |
| FR-4.3 | **Speaker Diarization:** Phân đoạn speaker, gán nhãn (SPEAKER_01, 02...) | Must |
| FR-4.4 | **ASR (Automatic Speech Recognition):** Chuyển audio → text, gắn speaker labels | Must |
| FR-4.5 | Pipeline xử lý hoàn toàn offline sử dụng sherpa models | Must |
| FR-4.6 | Hệ thống hiển thị trạng thái xử lý (progress %) qua API | Should |
| FR-4.7 | Nếu xử lý thất bại, lưu error message vào DB, trạng thái → `failed` | Must |
| FR-4.8 | Audio chunks tạm thời được lưu trong thư mục `uploads/temp/` và dọn dẹp sau xử lý | Should |

### LLM Processing

| ID | Requirement | Priority |
|---|---|---|
| FR-5.1 | **Extract Decisions:** Gemma4 bóc tách key decisions từ transcript | Must |
| FR-5.2 | **Extract Action Items:** Gemma4 trích xuất tasks + owners + due dates | Must |
| FR-5.3 | **Generate MoM:** Gemma4 tổng hợp thành Meeting of Minutes (Markdown) | Must |
| FR-5.4 | LLM endpoint: `http://107.98.158.221:9229/v1/chat/completions` | Must |
| FR-5.5 | Retry logic: thử lại 3 lần nếu LLM request thất bại | Should |
| FR-5.6 | Timeout cho LLM request: 120 giây | Should |
| FR-5.7 | Users có thể regenerate MoM sau khi edit transcript | Should |

### Transcription & MoM

| ID | Requirement | Priority |
|---|---|---|
| FR-6.1 | Users có thể xem transcription (text + speaker segments) | Must |
| FR-6.2 | Transcription lưu dạng JSON segments: `[{"speaker","text","start","end"}]` | Must |
| FR-6.3 | Users có thể xem Meeting of Minutes đã tạo | Must |
| FR-6.4 | MoM format: Markdown, bao gồm meeting info, discussion points, decisions, action items | Must |
| FR-6.5 | Users có thể export MoM dạng text file | Should |

### Settings

| ID | Requirement | Priority |
|---|---|---|
| FR-7.1 | Admin có thể xem và cập nhật system settings qua API | Must |
| FR-7.2 | Settings được lưu trong DB, có thể hot-reload | Must |
| FR-7.3 | Các settings quan trọng: VAD threshold, max speakers, ASR language, JWT expiry | Should |

---

## 3. Non-Functional Requirements (NFR)

### 3.1 Performance

| Metric | Target |
|---|---|
| Audio processing speed | ≥ 2x realtime (audio 60 phút → xử lý trong 30 phút) |
| LLM response time (MoM generation) | < 30 giây cho transcript 10,000 ký tự |
| API response time (simple CRUD) | < 500ms |
| Concurrent users | ≥ 10 users đồng thời |

### 3.2 Reliability

| Metric | Target |
|---|---|
| System uptime | ≥ 99% trong giờ hành chính |
| Pipeline success rate | ≥ 90% cho audio rõ ràng, 1-4 speakers |
| Error recovery | Pipeline fail → có thể retry từng bước, không mất dữ liệu |

### 3.3 Security

| Requirement | Chi tiết |
|---|---|
| Môi trường | Chạy trên mạng nội bộ, không exposure ra internet |
| Authentication | JWT-based, password hashed (bcrypt/argon2) |
| File validation | Chỉ cho upload audio formats: wav, mp3, flac, m4a |
| Max upload size | 500MB |
| RBAC | 2 roles: `admin` và `user` |

### 3.4 Usability

| Requirement | Chi tiết |
|---|---|
| Browser support | Chrome, Edge, Firefox (modern versions) |
| Mobile support | Responsive, tối thiểu cho tablet |
| Language | Giao diện tiếng Việt + English labels |
| Accessibility | Keyboard navigation, screen reader friendly labels |

### 3.5 Maintainability

| Requirement | Chi tiết |
|---|---|
| Tech stack | Python backend (Flask), vanilla HTML/CSS/JS (no heavy frameworks) |
| Code style | PEP 8 for Python, linting enforced |
| CI/CD | Scripts đơn giản, có thể deploy thủ công hoặc Docker |

### 3.6 Scalability

- Hệ thống thiết kế cho internal use, không cần scale ngang
- SQLite đủ cho < 10,000 meetings; có thể migrate lên PostgreSQL nếu cần

---

## 4. Use Cases

### UC-1: Đăng ký & Đăng nhập

```
Actor: Nhân viên mới
Precondition: Chưa có tài khoản
Main Flow:
  1. Nhân viên truy cập / → redirect to /login
  2. Nhấn "Đăng ký"
  3. Điền form: username, password, full name, email
  4. Hệ thống tạo tài khoản, trả về token
  5. Redirect to dashboard
Alternative: Username/email đã tồn tại → báo lỗi validation
```

### UC-2: Upload Audio & Xử lý MoM

```
Actor: User
Precondition: Đã đăng nhập, có cuộc họp
Main Flow:
  1. User vào Dashboard → nhấn "Tạo Meeting"
  2. Điền title, description, scheduled_at → Tạo meeting
  3. Upload audio file cho meeting đó
  4. Nhấn "Xử lý" → Backend trigger pipeline
  5. Backend: sep → VAD → diarization → ASR → LLM(decisions) → LLM(MoM)
  6. Cập nhật trạng thái meeting: processing → completed
  7. User xem kết quả: transcription + MoM
Alternative 1: File không hợp lệ → báo lỗi ngay
Alternative 2: Pipeline fail → status=failed, hiển thị error message
```

### UC-3: Xem & Export MoM

```
Actor: User
Precondition: Meeting đã xử lý xong
Main Flow:
  1. User vào meeting detail page
  2. Xem MoM (Markdown rendered)
  3. Nhấn "Export" → download .txt file
  4. Nhấn "Regenerate" → chỉnh sửa transcript (tùy chọn) → tạo lại MoM
```

### UC-4: Quản lý Users (Admin)

```
Actor: Admin
Precondition: User có role=admin
Main Flow:
  1. Admin vào /admin/users
  2. Xem danh sách users
  3. Thêm user mới / Reset password / Xóa user
  4. Thay đổi role (user ↔ admin)
```

### UC-5: Cấu hình Settings (Admin)

```
Actor: Admin
Precondition: User có role=admin
Main Flow:
  1. Admin vào /admin/settings
  2. Xem danh sách settings hiện tại
  3. Cập nhật giá trị → Save
  4. Hệ thống apply settings (hot-reload nếu supported)
```

---

## 5. UI/UX Requirements

### 5.1 Page Structure

| Page | Route | Mô tả |
|---|---|---|
| Login | `/login` | Form đăng nhập |
| Register | `/register` | Form đăng ký |
| Dashboard | `/dashboard` | Danh sách meetings, quick actions |
| Meeting Detail | `/meetings/<id>` | Chi tiết meeting, audio, MoM |
| Audio Upload | `/meetings/<id>/audio` | Upload & quản lý audio |
| Admin Users | `/admin/users` | Quản lý users (admin only) |
| Admin Settings | `/admin/settings` | Cấu hình hệ thống (admin only) |

### 5.2 UI Components

| Component | Mô tả |
|---|---|
| `MeetingCard` | Card hiển thị meeting info (title, date, status, audio count) |
| `AudioUploader` | Dropzone + progress bar + file info |
| `PipelineStatus` | Progress steps: upload → sep → VAD → diar → ASR → MoM |
| `TranscriptViewer` | Text với speaker labels, có thể click để nghe lại segment |
| `MoMEditor` | Markdown editor cho MoM, preview panel |
| `ToastNotification` | Thông báo success/error (auto-dismiss 5s) |
| `Pagination` | Phân trang cho danh sách meetings |

### 5.3 Visual Design

| Element | Spec |
|---|---|
| Color scheme | Primary: #2563EB (blue), Secondary: #64748B (slate) |
| Font | System font stack (no external dependency) |
| Spacing | 8px grid |
| Responsive | Mobile-first, breakpoints at 640px, 1024px |
| Animations | CSS transitions only, no heavy JS animations |
| Icons | SVG inline (no external icon lib) |

### 5.4 UX Flows

**Audio Upload Flow:**
1. User kéo thả hoặc click để chọn file
2. Progress bar hiển thị upload %
3. Sau khi upload xong → nút "Xử lý" hiện lên
4. Click "Xử lý" → pipeline status hiện ra
5. Mỗi step hiển thị spinner/check/x mark
6. Xong → notification + redirect đến MoM

**Error Handling UX:**
- Validation errors hiển thị inline dưới field
- API errors hiển thị toast notification (red)
- Pipeline errors hiển thị trong pipeline status panel + có nút Retry

---

## 6. System Constraints

### 6.1 Technical Constraints

| Constraint | Chi tiết |
|---|---|
| Frontend | Vanilla HTML/CSS/JS only — no React/Vue/Angular |
| Backend | Python 3.10+ với Flask |
| AI Models | sherpa models (offline, chạy local) |
| LLM | Gemma4 @ 107.98.158.221:9229 (internal network) |
| Database | SQLite (file-based, không cần database server) |
| OS | Windows Server hoặc Linux (deployment) |

### 6.2 Organizational Constraints

| Constraint | Chi tiết |
|---|---|
| Network | Hệ thống chỉ chạy trên mạng nội bộ công ty |
| Internet | Không cần internet để hoạt động (LLM server internal) |
| Deployment | IT team deploy thủ công hoặc qua script |
| Support | Internal IT support, không có vendor SLA |

### 6.3 Resource Constraints

| Resource | Limit |
|---|---|
| Max audio file | 500MB |
| Max concurrent processing | 2 (RAM/CPU bounded) |
| Storage | Audio files + DB ≤ 50GB |
| Memory per model | sherpa models có thể dùng 2-4GB RAM |

---

## 7. Acceptance Criteria

### AC-1: Authentication

- [ ] User có thể đăng ký với username/password/email
- [ ] User có thể đăng nhập và nhận JWT token
- [ ] Unauthorized requests (không có token) → 401 response
- [ ] Admin có thể quản lý users

### AC-2: Audio Upload & Processing

- [ ] Upload file wav/mp3/flac/m4a ≤ 500MB thành công
- [ ] Upload file không hợp lệ → error message rõ ràng
- [ ] Pipeline chạy: sep → VAD → diar → ASR → LLM → MoM
- [ ] Pipeline fail → status=failed, có error message
- [ ] Processing status hiển thị đúng từng step

### AC-3: Transcription & MoM

- [ ] Transcription chứa speaker labels + timestamps
- [ ] MoM có đầy đủ: meeting info, discussion points, decisions, action items
- [ ] MoM format: Markdown, export được thành .txt file
- [ ] Regenerate MoM sau edit transcript hoạt động

### AC-4: Performance

- [ ] API simple CRUD response < 500ms
- [ ] Audio 60 phút xử lý xong trong < 30 phút (2x realtime)

### AC-5: Security

- [ ] Hệ thống không expose ra internet
- [ ] Passwords hashed (bcrypt)
- [ ] JWT tokens expire sau 24h
- [ ] File upload validate format

### AC-6: UI/UX

- [ ] Giao diện hoạt động trên Chrome, Edge, Firefox
- [ ] Responsive trên tablet
- [ ] Error messages hiển thị rõ ràng, không crash UI
- [ ] Progress indicators hiển thị trong suốt pipeline

---

## 8. File Structure Reference

```
meeting-assistant/
├── frontend/
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── meeting.html
│   ├── admin/
│   │   ├── users.html
│   │   └── settings.html
│   └── assets/
│       ├── css/
│       │   └── style.css
│       └── js/
│           ├── app.js          # Main app logic
│           ├── api.js          # API client
│           ├── upload.js       # Audio upload handling
│           └── components.js   # Reusable UI components
├── backend/
│   ├── app.py                  # Flask entry point
│   ├── config.py               # Configuration loader
│   ├── requirements.txt
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py             # /api/v1/auth/*
│   │   ├── meetings.py         # /api/v1/meetings/*
│   │   ├── audio.py            # /api/v1/audio/*
│   │   ├── pipeline.py         # /api/v1/pipeline/*
│   │   └── settings.py         # /api/v1/settings/*
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
│   └── meeting.db               # SQLite database file
├── uploads/                     # Uploaded audio files
├── docs/
│   ├── Architecture.md
│   └── SRS.md
├── .env.example
└── README.md
```

---

*End of SRS.md*
*Document version 1.0 — 2026-05-07*
