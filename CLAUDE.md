# Orcanos Performance Testing Tool — Claude Code Instructions

> For feature specs, UI mockups, and architecture decisions see `design/orcanos-performance-test.md`.

---

## Project

A centralized performance and stability monitoring tool for the Orcanos system. Records user interaction scenarios once using Playwright and automatically runs them across all customer accounts, tracking response times and identifying bottlenecks. Admin-only web app.

**Account Model:**
- Each account has a unique password (stored encrypted with AES-256/Fernet)
- All accounts use the same shared user: `orcanos.tech`
- Account name extracted from URL: `https://app.orcanos.com/{ACCOUNT}/web/`
- Example: `https://app.orcanos.com/orcanos/web/` → account name is `orcanos`

**Git repo:** https://github.com/zoharp/orcanos-performance

---

## Tech Stack

- **Backend:** FastAPI (Python 3.12)
- **Frontend:** React + Vite
- **Database:** SQLite (SQLAlchemy)
- **Browser Automation:** Playwright (Chromium)
- **Hosting:** Fly.io (single machine, Amsterdam region, persistent volume at `/data`)

---

## Current versions

- **Backend:** `0.2.0`
- **Frontend:** `0.2.0`

---

## Build Status

### Done
- [x] Project structure, environment setup, `.env`, venv
- [x] FastAPI backend with CORS, `/health` endpoint, SQLite via SQLAlchemy
- [x] Auth service (JWT), encryption service (AES-256/Fernet)
- [x] Accounts API — CRUD with encrypted password storage, version field
- [x] Scenario recorder service — runs Playwright in background thread, auto-captures clicks/fills/navigations
- [x] Scenarios API — record/start, record/stop, record/status, list, get, delete, edit (name + version)
- [x] React frontend with routing (react-router-dom v6)
- [x] Login page + JWT auth (localStorage token) — all routes protected, redirect to `/login` if unauthenticated
- [x] Accounts page — add (URL + password + version), list, edit all fields, enable/disable, delete
- [x] Scenarios page — record new scenario, live step feed, edit name/version, run button + progress
- [x] Settings page — configurable pass/warn/timeout thresholds, saved to `config.json`
- [x] Config API — `GET/PUT /api/config/` reads and writes `config.json` thresholds
- [x] `run.bat` — kills previous processes, waits for backend + frontend, opens browser
- [x] Test runner (`backend/services/runner.py`) — replays scenario headless per account, measures per-step timing, saves StepResult rows
- [x] Runs API — `POST /api/runs/` starts run in background thread, `GET /api/runs/{id}/progress` for live polling
- [x] Results API — `GET /api/results/runs` list, `GET /api/results/run/{id}` grouped by account
- [x] Dashboard page — runs list + color-coded matrix (account × step), green/yellow/red by timing thresholds
- [x] Run button on Scenarios page — triggers run, shows live progress bar per account
- [x] Clear error messages — global exception handler returns actual error text; routes raise specific HTTPExceptions
- [x] Fly.io deployment — Dockerfile (multi-stage), `fly.toml`, persistent volume `orcanos_data` at `/data`
- [x] SPA routing fix — catch-all route in `api.py` serves `index.html` for all non-API paths (F5 refresh works)

### Next
- [ ] Historical chart (Recharts) — trend over time per account/step
- [ ] Scheduled runs (cron) — auto-run scenarios on a schedule

---

## Project Structure

```
orcanos-performance/
├── CLAUDE.md                  ← this file
├── design/
│   └── orcanos-performance-test.md  ← full design doc (features, architecture, mockups)
├── .env                       ← secrets (never commit)
├── .env.example               ← template (keys only)
├── Dockerfile                 ← multi-stage build (Node → React dist, Python + Playwright)
├── fly.toml                   ← Fly.io config (app=orcanos-performance, region=ams, volume at /data)
├── fly_import.ps1             ← one-time script to upload local DB + scenarios to Fly volume
├── config.json                ← runtime thresholds (pass/warn/timeout seconds) — not committed
├── GitPush.bat                ← git commit + push to GitHub
├── run.bat                    ← start backend + frontend locally, opens browser
├── run-backend.bat            ← backend only (FastAPI on port 8000)
├── requirements.txt           ← Python dependencies (use >= versions, Python 3.12)
├── backend/
│   ├── api.py                 ← FastAPI app, lifespan, SPA catch-all, route registration
│   ├── models.py              ← SQLAlchemy models (Account, Scenario, TestRun, StepResult, User)
│   ├── scenarios/             ← saved scenario JSON files (local); /data/scenarios/ on Fly
│   ├── services/
│   │   ├── auth.py            ← JWT auth + get_current_user + require_admin dependencies
│   │   ├── database.py        ← SQLite engine, session, init_db (create_all + ALTER TABLE migrations)
│   │   ├── encryption.py      ← Fernet AES-256 encrypt/decrypt
│   │   ├── recorder.py        ← Playwright recording session (background thread)
│   │   └── runner.py          ← Playwright headless replay, per-step timing, StepResult persistence
│   └── routes/
│       ├── auth.py            ← POST /api/auth/login, /logout, /verify
│       ├── accounts.py        ← CRUD /api/accounts/
│       ├── scenarios.py       ← /api/scenarios/record/*, list, get, edit, delete
│       ├── runs.py            ← POST /api/runs/, GET /api/runs/{id}/progress
│       ├── results.py         ← GET /api/results/runs, GET /api/results/run/{id}
│       └── config.py          ← GET/PUT /api/config/ (reads/writes config.json thresholds)
├── scripts/
│   └── record_scenario.py     ← CLI recorder (fallback; UI recorder preferred)
├── tests/
│   ├── test_runner.py
│   ├── test_encryption.py
│   └── conftest.py
└── frontend/
    ├── package.json
    ├── vite.config.js         ← Vite proxy: /api → localhost:8000 (no rewrite)
    └── src/
        ├── App.jsx            ← BrowserRouter, protected routes, Nav, logout
        ├── auth.js            ← localStorage token helpers (getToken, setAuth, clearAuth, fetchWithAuth)
        └── pages/
            ├── Login.jsx      ← login form, calls /api/auth/login, stores JWT
            ├── Dashboard.jsx  ← runs list + account×step timing matrix
            ├── Accounts.jsx   ← add/edit/list/toggle/delete accounts
            ├── Scenarios.jsx  ← record, edit, run scenarios
            └── Settings.jsx   ← pass/warn/timeout threshold editor
```

---

## Key Implementation Notes

**Vite proxy:** All frontend API calls use relative paths (`/api/...`). Vite proxies them to `http://localhost:8000` without rewriting. Never use `VITE_API_URL` — always use `const API = ''`.

**Scenarios storage:** Scenarios are JSON files in `backend/scenarios/`, not DB rows. The `Scenario` SQLAlchemy model exists but is unused. Editing a scenario name renames the file.

**Recorder:** `backend/services/recorder.py` runs a `RecordingSession` singleton. Playwright runs in a background thread with its own asyncio loop. The API polls `/api/scenarios/record/status` every second during recording.

**Runner:** `backend/services/runner.py` runs a `RunnerSession` singleton. Replays scenario steps headless per account. Timing thresholds are read from `config.json` (defaults: < 3s = pass, 3–8s = warning, > 8s = critical). Replaces account name in navigation URLs automatically (e.g. `/orcanos/` → `/acme/`).

**Passwords:** Stored encrypted in SQLite. `{{PASSWORD}}` placeholder in scenario steps is replaced at test runtime with the account's decrypted password.

**DB migrations:** `init_db()` in `database.py` calls `create_all` then manually checks for missing columns via `PRAGMA table_info` and runs `ALTER TABLE`. Always add new column migrations there — SQLAlchemy `create_all` does not alter existing tables.

**Config thresholds:** `config.json` at repo root stores pass/warn/timeout seconds. Read by `routes/config.py` and the runner. File is not committed (gitignored); defaults apply if missing.

**Auth:** JWT tokens stored in browser `localStorage`. All API routes (except `/api/auth/login`) require `Authorization: Bearer <token>`. `get_current_user` dependency in `auth.py` validates the token. `require_admin` dependency gates admin-only endpoints.

**SPA routing:** `api.py` has a catch-all `GET /{full_path:path}` that serves real files from `frontend/dist/` if they exist, otherwise returns `index.html`. This makes F5/refresh work for all React routes.

**Fly.io deployment:** App is live at `https://orcanos-performance.fly.dev/`. Single machine (`d8dd330b71d198`) in Amsterdam with auto-stop/start. Persistent volume `orcanos_data` mounted at `/data` — DB at `/data/orcanos_performance.db`, scenarios at `/data/scenarios/`. Deploy with `flyctl deploy`. The `/data` directory must have `chmod 777` for SQLite writes (set once via SSH; persists on the volume).

**Python 3.12:** Dockerfile uses `python:3.12-slim`. Use `>=` version constraints in `requirements.txt`.

---

## Environment Variables (`.env`)

```bash
ADMIN_PASSWORD=your-secure-admin-password
ENCRYPTION_KEY=your-32-char-hex-encryption-key   # python -c "import secrets; print(secrets.token_hex(16))"
ENVIRONMENT=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000
DATABASE_URL=sqlite:///./orcanos_performance.db
```

**On Fly.io** — secrets are set via `flyctl secrets set KEY=value`. The `[env]` section in `fly.toml` holds non-secret env vars (`DATABASE_URL`, `SCENARIOS_DIR`, `ENVIRONMENT`, `LOG_LEVEL`).

---

## How to Run

**Locally:**
```bat
run.bat           ← full stack (kills previous, starts backend + frontend, opens browser)
run-backend.bat   ← backend only (FastAPI on port 8000)
GitPush.bat       ← commit & push to GitHub
```

**Deploy to Fly.io:**
```bat
flyctl deploy     ← builds Docker image, pushes, rolls out (takes ~2 min)
```

**First-time local setup:**
1. `setup.bat` — creates venv, installs deps, runs `playwright install chromium`
2. Copy `.env.example` → `.env` and fill in `ADMIN_PASSWORD` + `ENCRYPTION_KEY`
3. `run.bat`

---

## Common Issues

**Port in use:** `run.bat` kills ports 8000/5173 automatically on startup.

**Playwright browser missing:** `.venv\Scripts\python -m playwright install chromium`

**500 errors:** Global exception handler in `api.py` returns the real error. Check backend console for traceback.

**Missing DB column:** Add `ALTER TABLE` migration in `init_db()` in `database.py`.

**CORS errors:** Frontend must use relative paths (`/api/...`), not `http://localhost:8000/api/...`.

**Fly SQLite readonly:** The `/data` volume must be writable. Run once via SSH: `flyctl ssh console --app orcanos-performance -C "chmod 777 /data"`. This persists on the volume across restarts.

**Fly machine stopped:** The machine auto-stops when idle and auto-starts on first request (cold start ~5s). Use `flyctl machine start d8dd330b71d198` to pre-warm it.
