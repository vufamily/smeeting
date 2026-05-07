# Architecture.md — Web-based Meeting Assistant (Clean Architecture)

**Project:** Meeting Assistant  
**Location:** `C:\Users\SRV\workspace\meeting-assistant\`  
**Date:** 2026-05-07  
**Stack:** Python/Flask | SQLite | Clean Architecture + MVC | Gemma4 LLM @ 107.98.158.221:9229

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
│   │  (Browser)   │◄──────►│    (Flask/Python) │◄────►│  (Gemma4)   │      │
│   │              │ HTTP   │                   │HTTP  │ 107.98.158  │      │
│   │  HTML/CSS/JS │  REST  │  Clean Architecture│POST  │ .221:9229   │      │
│   └──────────────┘        └───────────────────┘       └──────────────┘      │
│                                  │                                          │
│              ┌───────────────────┼───────────────────┐                     │
│              ▼                   ▼                   ▼                      │
│       ┌────────────┐     ┌────────────┐      ┌────────────┐              │
│       │presentation│ →   │    core    │  →   │infrastructure│              │
│       │   (MVC)    │     │(entities,   │      │  (DB, AI)   │              │
│       │            │     │ repos,      │      │             │              │
│       │ templates/ │     │ services)   │      │ SQLite,      │              │
│       │ controllers │     │             │      │ bcrypt, LLM  │              │
│       │   routes/   │     │             │      │ integrations │              │
│       └────────────┘     └─────────────┘      └─────────────┘              │
│                                  │                                          │
│                                  ▼                                          │
│                           ┌───────────────┐                                 │
│                           │   SQLite DB  │                                 │
│                           │ (meeting.db)  │                                 │
│                           └───────────────┘                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Clean Architecture Layers

### 2.1 Core Layer (`core/`)

**Purpose:** Business logic with NO external dependencies.

```
core/
├── __init__.py
├── entities/          # Business objects (plain Python classes)
│   ├── __init__.py
│   ├── user.py        # User entity (UserRole, UserStatus enums)
│   ├── meeting.py     # Meeting entity (MeetingStatus enum)
│   ├── transcription.py
│   ├── audio_file.py
│   ├── decision.py
│   ├── task.py
│   └── meeting_minutes.py
├── repositories/       # Abstract interfaces (data access contracts)
│   ├── __init__.py
│   ├── user_repository.py    # UserRepository ABC
│   └── meeting_repository.py
└── services/           # Business logic use cases
    ├── __init__.py
    ├── auth_service.py        # Register, login, approve/reject
    ├── meeting_service.py    # Meeting CRUD, InMemoryMeetingService
    └── audio_processing_service.py
```

### 2.2 Infrastructure Layer (`infrastructure/`)

**Purpose:** External concerns — DB, AI, Auth implementations.

```
infrastructure/
├── __init__.py
├── database/           # SQLite implementations
│   ├── __init__.py
│   ├── sqlite_connection.py      # Connection manager + schema init
│   ├── sqlite_user_repository.py # Implements UserRepository
│   └── sqlite_meeting_repository.py
├── auth/               # Auth integrations
│   ├── __init__.py
│   ├── flask_auth.py   # Flask-Login wrapper (FlaskUser)
│   └── password_bcrypt.py
├── ai/                 # AI integrations
│   ├── __init__.py
│   ├── speech_to_text.py
│   ├── speaker_diarization.py
│   └── llm_integration.py
└── storage/            # File storage
    └── file_storage.py
```

### 2.3 Presentation Layer (`presentation/`)

**Purpose:** MVC Views — Flask templates + static assets.

```
presentation/
├── __init__.py
├── controllers/        # (reserved for future use)
├── views/
│   ├── admin/
│   ├── auth/
│   └── meeting/
└── static/
    ├── css/
    └── js/
```

### 2.4 Routes Layer (`routes/`)

**Purpose:** HTTP route handlers that bridge presentation to core services.

```
routes/
├── __init__.py           # Blueprint exports (auth_bp, admin_bp, meeting_bp)
├── auth_routes.py        # /auth/login, /auth/register, /auth/logout
├── admin_routes.py       # /admin/users/* (admin only)
└── meeting_routes.py     # /, /dashboard, /api/* (meeting CRUD)
```

---

## 3. app.py — Minimal Flask Entry Point

`app.py` is minimal. It only:
1. Initializes Flask
2. Creates/initializes infrastructure (db, repos)
3. Creates core services (injecting repos)
4. Sets up Flask-Login
5. Registers route blueprints
6. Runs the server

**All route logic lives in `routes/`**, not in `app.py`.

---

## 4. Data Flow

```
HTTP Request
     │
     ▼
routes/ (auth_routes.py, meeting_routes.py, admin_routes.py)
     │  (imports core services via app.auth_service, app.meeting_service)
     ▼
core/services/ (auth_service.py, meeting_service.py)
     │  (uses repository interfaces, no concrete DB knowledge)
     ▼
core/repositories/ (user_repository.py, meeting_repository.py)
     │  (abstract interfaces defined here)
     ▼
infrastructure/database/ (sqlite_user_repository.py, sqlite_meeting_repository.py)
     │  (concrete implementations of repository interfaces)
     ▼
SQLiteConnection → meeting.db
```

---

## 5. Database Schema (SQLite)

### `users`

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    role TEXT DEFAULT 'user',       -- 'admin' | 'user'
    status TEXT DEFAULT 'pending',  -- 'pending' | 'approved' | 'rejected' | 'disabled'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `meetings`

```sql
CREATE TABLE meetings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    scheduled_at DATETIME,
    duration_minutes INTEGER,
    status TEXT DEFAULT 'pending',  -- 'pending' | 'processing' | 'completed' | 'failed'
    created_by INTEGER REFERENCES users(id),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### `audio_files`, `transcriptions`, `meeting_minutes`, `settings`

See full schema in `infrastructure/database/sqlite_connection.py` (`init_database()`).

---

## 6. Key Patterns

### Clean Architecture Dependency Rule

```
presentation → core ← infrastructure
```

- `core/` knows nothing about Flask, SQLite, or any external framework
- `infrastructure/` implements `core/` interfaces
- `presentation/` (routes, templates) depends on `core/` services

### Repository Pattern

```python
# core/repositories/user_repository.py (abstract interface)
class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]: pass

# infrastructure/database/sqlite_user_repository.py (concrete implementation)
class SQLiteUserRepository(UserRepository):
    def __init__(self, db_connection: SQLiteConnection): ...
    def get_by_id(self, user_id: int) -> Optional[User]: ...
```

### Service Layer Pattern

```python
# core/services/auth_service.py
class AuthService:
    def __init__(self, user_repository: UserRepository):
        self.user_repository = user_repository  # interface, not implementation
```

### Flask-Login Bridge

```python
# app.py
class FlaskUser(UserMixin):
    def __init__(self, user: User): ...  # wraps core User entity
```

---

## 7. Auth & User Status

- **Registration:** user created with `status = 'pending'`, cannot login
- **Admin approval:** `/admin/users/<id>/approve` → `status = 'approved'`
- **Default admin:** `admin` / `admin123` created on first startup (approved)

### Auth Decorators

- `@login_required` — standard Flask-Login
- `@approved_required` — custom, requires `status == 'approved'`
- `@admin_required` — custom, requires `role == 'admin'` AND `status == 'approved'`

---

## 8. File Structure Summary

```
meeting-assistant/
├── app.py                           # Flask entry point (minimal)
├── main.py                          # Alternative entry point
├── requirements.txt
├── core/
│   ├── __init__.py
│   ├── entities/
│   │   ├── user.py, meeting.py, transcription.py, ...
│   │   └── __init__.py
│   ├── repositories/
│   │   ├── user_repository.py, meeting_repository.py
│   │   └── __init__.py
│   └── services/
│       ├── auth_service.py, meeting_service.py, ...
│       └── __init__.py
├── infrastructure/
│   ├── __init__.py
│   ├── database/
│   │   ├── sqlite_connection.py (schema init)
│   │   ├── sqlite_user_repository.py
│   │   ├── sqlite_meeting_repository.py
│   │   └── __init__.py
│   ├── auth/ (flask_auth.py, password_bcrypt.py)
│   ├── ai/   (speech_to_text.py, speaker_diarization.py, llm_integration.py)
│   └── storage/
├── routes/
│   ├── __init__.py
│   ├── auth_routes.py
│   ├── admin_routes.py
│   └── meeting_routes.py
├── presentation/
│   ├── controllers/
│   ├── views/ (admin/, auth/, meeting/)
│   └── static/ (css/, js/)
├── templates/ (admin.html, index.html, login.html, register.html, ...)
├── static/    (legacy — gradually migrated to presentation/)
├── data/ (meeting.db)
├── uploads/
├── docs/
└── logs/
```

---

*Document version 2.0 — 2026-05-07 (Clean Architecture refactor complete)*