# Orcanos Performance Testing Tool — Codex Instructions

> System-level rules (deployment gate, skills, versioning, traceability) are in `system.md`.
> This file contains only project-specific information.

---

## Project

A centralized performance and stability monitoring tool for the Orcanos system. Records user interaction scenarios once using Playwright and automatically runs them across all customer accounts, tracking response times and identifying bottlenecks. Admin-only web app that runs tests on schedule and provides dashboards with historical trends.

**Account Model:**
- Each account has a unique password (stored encrypted with AES-256/Fernet)
- All accounts use the same shared user: `orcanos.tech`
- Account name extracted from URL: `https://app.orcanos.com/{ACCOUNT}/web/`
- Example: `https://app.orcanos.com/orcanos/web/` → account name is `orcanos`

**Git repo:** https://github.com/zoharp/orcanos-performance

---

## Tech Stack

- **Backend:** FastAPI (Python 3.14)
- **Frontend:** React + Vite
- **Database:** SQLite (can migrate to PostgreSQL/Supabase later)
- **Browser Automation:** Playwright (Chromium)
- **AI/LLM:** None

---

## Deployment

- **Frontend:** Vercel (auto-deploys on push to main)
- **Backend:** Vercel Serverless Functions or separate service (Railway/Render)
- **Database:** SQLite file-based (can migrate to managed DB later)
- **Deploy:** run `GitPush.bat` — auto-deploys via Vercel

---

## Current versions

- **Backend:** `0.1.0` (MVP in progress)
- **Frontend:** `0.1.0` (MVP in progress)

---

## Build Status

### Done
- [x] Project structure, environment setup, `.env`, venv
- [x] FastAPI backend with CORS, `/health` endpoint, SQLite via SQLAlchemy
- [x] Auth service (JWT), encryption service (AES-256/Fernet)
- [x] Accounts API — CRUD with encrypted password storage
- [x] Scenario recorder service — runs Playwright in background thread, auto-captures clicks/fills/navigations
- [x] Scenarios API — record/start, record/stop, record/status, list, get, delete
- [x] React frontend with routing (react-router-dom v6)
- [x] Accounts page — add account by URL + password, auto-extracts account name, list/enable/disable/delete
- [x] Scenarios page — record new scenario via browser, live step feed, saved scenarios list
- [x] `run.bat` — kills previous processes, waits for backend + frontend, opens browser

### In Progress / Next
- [ ] Test runner — replay scenario on each account, measure step timings
- [ ] Run button on dashboard — trigger test run manually
- [ ] Results dashboard — per-account, per-step timings with green/yellow/red status
- [ ] Historical chart (Recharts)
- [ ] Scheduled runs (cron)

---

## Project Structure

```
orcanos-performance/
├── AGENTS.md                  ← this file (project-specific)
├── system.md                  ← global Orcanos rules
├── orcanos-performance-test.md ← design document
├── .env                       ← secrets (never commit)
├── .env.example               ← template (keys only)
├── .gitignore
├── accounts.json              ← legacy account list (replaced by DB)
├── GitPush.bat                ← git commit + push (Windows)
├── run.bat                    ← start backend + frontend, opens browser
├── run-backend.bat            ← start backend only
├── run_claude.bat             ← launch Codex
├── requirements.txt           ← Python dependencies (use >= versions, Python 3.14)
├── backend/
│   ├── api.py                 ← FastAPI app, lifespan, route registration
│   ├── models.py              ← SQLAlchemy models (Account, Scenario, TestRun, StepResult)
│   ├── scenarios/             ← saved scenario JSON files
│   ├── services/
│   │   ├── auth.py            ← JWT auth service
│   │   ├── database.py        ← SQLite engine, session, init_db
│   │   ├── encryption.py      ← Fernet AES-256 encrypt/decrypt
│   │   └── recorder.py        ← Playwright recording session (background thread)
│   └── routes/
│       ├── auth.py            ← POST /api/auth/login, /logout, /verify
│       ├── accounts.py        ← CRUD /api/accounts/
│       ├── scenarios.py       ← /api/scenarios/record/*, list, get, delete
│       ├── runs.py            ← (stub) test run endpoints
│       └── results.py         ← (stub) results endpoints
├── scripts/
│   └── record_scenario.py     ← CLI recorder (fallback; UI recorder preferred)
├── tests/
│   ├── test_runner.py
│   ├── test_encryption.py
│   └── conftest.py
└── frontend/
    ├── package.json
    ├── vite.config.js         ← Vite proxy: /api → localhost:8000 (no rewrite)
    ├── .env.local
    └── src/
        ├── App.jsx            ← BrowserRouter, Nav, routes
        ├── main.jsx
        ├── App.css / index.css
        └── pages/
            ├── Accounts.jsx   ← add/list/toggle/delete accounts
            └── Scenarios.jsx  ← record new scenario, live step feed, saved list
```

---

## Key Implementation Notes

**Vite proxy:** All frontend API calls use relative paths (`/api/...`). Vite proxies them to `http://localhost:8000` without rewriting. Never use `VITE_API_URL` for API calls — always use `const API = ''`.

**Recorder:** `backend/services/recorder.py` runs a `RecordingSession` singleton. Playwright runs in a background thread with its own asyncio loop. The API polls `/api/scenarios/record/status` every second during recording.

**Passwords:** Stored encrypted in SQLite. `{{PASSWORD}}` placeholder in scenario steps is replaced at test runtime with the account's decrypted password.

**Python 3.14:** Use `>=` version constraints in `requirements.txt` — pinned old versions don't have wheels for Python 3.14.

---

## Environment Variables (`.env`)

```bash
ADMIN_PASSWORD=your-secure-admin-password
ENCRYPTION_KEY=your-32-char-hex-encryption-key   # generate: python -c "import secrets; print(secrets.token_hex(16))"
ENVIRONMENT=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=sqlite:///./orcanos_performance.db
```

---

## How to Run

```bat
run.bat           ← full stack (kills previous, starts backend + frontend, opens browser)
run-backend.bat   ← backend only (FastAPI on port 8000)
GitPush.bat       ← commit & push to GitHub
```

**First-time setup:**
1. `setup.bat` — creates venv, installs dependencies, runs `playwright install chromium`
2. Copy `.env.example` → `.env` and fill in `ADMIN_PASSWORD` + `ENCRYPTION_KEY`
3. `run.bat`

---

## Common Issues

**Port 8000/5173 in use:** `run.bat` kills them automatically on startup.

**Python venv missing:** `python -m venv .venv` then `.venv\Scripts\pip install -r requirements.txt`

**Playwright browser missing:** `.venv\Scripts\python -m playwright install chromium`

**500 on /api/accounts/:** Usually means `init_db()` didn't run or models are misconfigured. Check backend console for traceback.

**CORS errors:** Frontend must use relative paths (`/api/...`), not `http://localhost:8000/api/...`.
