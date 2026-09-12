# IBVAP - Intelligent Border Video Analytics Platform (Backend)

An edge-first, AI-driven surveillance backend transforming standard IP/RTSP CCTV cameras at Border Out Posts (BOPs) into an intelligent surveillance network with real-time alerting and hierarchical synchronization to Battalion HQ.

---

## 🛠️ Tech Stack (Phase 1)
- **Runtime**: Python 3.13
- **Framework**: FastAPI + Uvicorn
- **Data Validation**: Pydantic v2 & Pydantic Settings
- **Database ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL / Supabase (with SQLite support for zero-config local prototyping)

---

## 📁 Directory Structure
```text
ProjectSih/
├── .env.example              # Template for environment settings
├── .env                      # Local active environment variables (ignored by git)
├── .gitignore                # Git exclusions
├── requirements.txt          # Python dependencies
├── storage/                  # Local media evidence (snapshots & clips)
│   ├── snapshots/
│   └── clips/
└── app/
    ├── __init__.py
    ├── main.py               # FastAPI app entrypoint, CORS, & Lifespan
    ├── core/
    │   ├── config.py         # Application settings & environment loader
    │   └── database.py       # SQLAlchemy 2.0 engine, Base, & session generator
    ├── models/               # Database tables (Phase 2)
    ├── schemas/              # Pydantic request/response schemas (Phase 2)
    ├── api/
    │   └── v1/
    │       ├── api.py        # Central router
    │       └── endpoints/
    │           └── health.py # /api/v1/health status endpoint
    └── services/             # Modular business & AI logic (Phase 3+)
        ├── vision/           # Video ingestion & YOLO detector
        ├── alerts/           # Threat evaluation & WebSockets
        └── sync/             # Edge-to-HQ synchronization
```

---

## 🚀 Quick Start Guide

### 1. Activate the Virtual Environment
```bash
source .venv/bin/activate
```

### 2. Configure Environment Variables
Copy `.env.example` to `.env` (already done for development):
```bash
cp .env.example .env
```
By default, `DATABASE_URL` is set to `sqlite:///./ibvap_edge.db` for instant local testing without setting up a database server.
To connect to PostgreSQL or Supabase, update `DATABASE_URL` in `.env`:
```env
DATABASE_URL="postgresql://<username>:<password>@<host>:<port>/<database_name>"
```

### 3. Run the Development Server
```bash
uvicorn app.main:app --reload --port 8000
```

### 4. Test the Endpoints
- **Root**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **Health Check**: [http://127.0.0.1:8000/api/v1/health](http://127.0.0.1:8000/api/v1/health)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
