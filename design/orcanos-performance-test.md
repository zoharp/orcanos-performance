# Orcanos Performance Testing Tool — Design Document

## Executive Summary

Build a centralized performance and stability monitoring tool for the Orcanos system. The tool records user interaction scenarios and automatically runs them across multiple customer accounts, tracking response times and identifying performance bottlenecks.

---

## Project Overview

**Goal:** Create a web-based tool to monitor performance across all Orcanos accounts on a schedule and alert on degradation.

**Key Users:** Orcanos DevOps/QA team (admin access only)

**Scope:** Single-tenant monitoring tool that tests multiple account instances

---

## How It Works

### 1. Account Configuration

A JSON file contains all accounts to be tested:

```json
{
  "accounts": [
    {
      "name": "Account Name",
      "url": "https://app.orcanos.com/ACCOUNT/web",
      "password": "[ENCRYPTED]",
      "enabled": true
    }
  ],
  "thresholds": {
    "warning": 3,
    "critical": 10
  }
}
```

**Account URL Format:**
- `https://us.orcanos.com/ACCOUNT/web` (primary)
- `https://app.orcanos.com/ACCOUNT/web` (alternate)

Each account must use the correct base URL for its region.

**Security:** Passwords are encrypted at rest; decrypted only at runtime.

### 2. Test Scenario Recording

- **Process:** Manually perform a test sequence once on a representative account
  - System records each step (name, URL, action, expected result)
  - Developer reviews and approves the scenario
  - Scenario is locked and reused for all accounts

- **Shared User:** Use `orcanos.tech` account for all test runs
- **Data:** Scenario stored as structured steps (not video/screenshot)

### 3. Test Execution

- **Trigger:** Manual button or scheduled (e.g., hourly, daily)
- **Process:**
  1. Load JSON file with account list
  2. For each account:
     - Log in with `orcanos.tech` credentials
     - Execute recorded scenario
     - Record timing for each step
     - Logout
  3. Aggregate results and store in SQLite

---

## Features

### Feature 1: Admin Login Screen
- Single admin password (configured in environment)
- Session-based authentication
- No user management (admin-only for now)

### Feature 2: Main Dashboard
**Left Panel:**
- List of all accounts from JSON
- Account name, last run status (✓ pass, ⚠ warning, ✗ failure), last run time

**Right Panel:**
- Quick stats: Total accounts, Last run time, Pass/Warn/Fail counts
- Run Test button (starts test scenario)

### Feature 3: Test Execution & Monitoring
**During test run:**
- Show real-time progress (current account, current step)
- Display step name, elapsed time, live counter

**Result Display:**
- Each step shows:
  - Step name
  - Start time, end time, duration (seconds)
  - Status indicator:
    - 🟢 Green: < 3 seconds
    - 🟡 Yellow: 3–10 seconds
    - 🔴 Red: > 10 seconds
  - Account name

### Feature 4: Results Dashboard
**Summary View:**
- Step averages (e.g., "Login: avg 2.1s")
- Accounts with critical issues (> 10s steps)
- Scenario-level average (e.g., "Total avg: 45 seconds")
- Count of steps: green / yellow / red

**Historical Chart:**
- X-axis: Time (day / week / month, depending on data density)
- Y-axis: Duration (seconds)
- One line per step, showing trend over time
- Allows filtering by account or step

### Feature 5: History View
- Table of all past test runs
  - Run ID, timestamp, duration, pass/warn/fail counts
  - Click to view detailed results of that run
- Ability to compare two runs side-by-side (optional MVP+)

### Feature 6: Manual Test (Accounts Page)
- "Test" button next to each account
- Automatically logs in with stored credentials and opens the app in a new tab
- Employees can manually test and explore account behavior
- Available on both local development and production

---

## Architecture

### Tech Stack
- **Frontend:** React + Vite (or Next.js)
- **Backend:** FastAPI (Python) or Node.js/Express
- **Database:** SQLite (local; can migrate to PostgreSQL/Supabase later)
- **Hosting:** Vercel (frontend); backend can be on same Vercel instance or separate service

### File Structure
```
orcanos-performance/
├── CLAUDE.md                   # Project-specific instructions
├── .env                        # Secrets (ADMIN_PASSWORD, encryption key)
├── .env.example                # Template
├── accounts.json               # Account list (generated from table)
├── backend/
│   ├── api.py                  # FastAPI app
│   ├── models.py               # SQLite models
│   ├── services/
│   │   ├── auth.py
│   │   ├── scenario.py
│   │   ├── test_runner.py
│   │   └── encryption.py
│   └── routes/
│       ├── auth.py
│       ├── accounts.py
│       ├── runs.py
│       └── results.py
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── Login.jsx
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Results.jsx
│   │   │   └── History.jsx
│   │   ├── components/
│   │   │   ├── StepTable.jsx
│   │   │   ├── HistoricalChart.jsx
│   │   │   └── AccountList.jsx
│   │   └── App.jsx
├── tests/
│   ├── test_runner.py          # Unit tests for scenario execution
│   └── test_encryption.py
└── requirements.txt
```

### Data Model

**Accounts Table:**
```sql
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY,
  name TEXT UNIQUE,
  url TEXT,
  encrypted_password TEXT,
  enabled BOOLEAN,
  created_at TIMESTAMP
);
```

**Scenarios Table:**
```sql
CREATE TABLE scenarios (
  id INTEGER PRIMARY KEY,
  name TEXT,
  steps JSON,  -- Array of step definitions
  created_at TIMESTAMP,
  updated_at TIMESTAMP
);
```

**Test Runs Table:**
```sql
CREATE TABLE test_runs (
  id INTEGER PRIMARY KEY,
  scenario_id INTEGER,
  started_at TIMESTAMP,
  completed_at TIMESTAMP,
  status TEXT  -- 'pass', 'warning', 'critical'
);
```

**Step Results Table:**
```sql
CREATE TABLE step_results (
  id INTEGER PRIMARY KEY,
  run_id INTEGER,
  account_id INTEGER,
  step_name TEXT,
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  duration_seconds FLOAT,
  status TEXT,  -- 'pass', 'warning', 'critical'
  error_message TEXT
);
```

---

## Implementation Phases

### Phase 1: MVP (Core Functionality)
- [ ] Admin login screen
- [ ] Account JSON configuration
- [ ] Basic scenario recording interface
- [ ] Single test run execution
- [ ] Results dashboard with basic table
- [ ] SQLite persistence

### Phase 2: Polish
- [ ] Historical chart (Recharts or similar)
- [ ] Scheduled test runs (cron)
- [ ] Account status indicators
- [ ] Error handling & logging
- [ ] Password encryption (AES-256)

### Phase 3: Enhancement (Post-MVP)
- [ ] Slack/email notifications on critical failures
- [ ] Two-run comparison view
- [ ] Custom threshold per account
- [ ] Test run API for external triggers
- [ ] Multi-user support with RBAC

---

## Data Input: Accounts Table

The user will provide a table with account details. Claude will then:
1. Create the `accounts.json` file
2. Encrypt the passwords
3. Validate URLs

**Example User Table:**

| Account Name | URL | Password |
|---|---|---|
| Acme Corp | https://app.orcanos.com/acme/web | MyPassword123! |
| TechStart Inc | https://us.orcanos.com/techstart/web | SecurePass#99 |

---

## Security Considerations

1. **Admin Password:** Store in `.env`, never commit
2. **Encryption:** Use AES-256 for password storage; key in `.env`
3. **Session:** Use JWT or session cookies; expire after 1 hour of inactivity
4. **HTTPS:** Required in production
5. **Audit Log:** Log all test runs and admin actions (username, timestamp, action)

---

## Deployment

**Frontend:** Vercel (auto-deploy on push to main)
**Backend:** Vercel Serverless Functions or separate service (e.g., Railway, Render)
**Database:** SQLite (file-based) for MVP; can migrate to managed DB later

**Deploy Command:**
```bash
./deploy.sh  (or deploy.bat on Windows)
```

---

## Next Steps

1. **Confirm tech stack** (FastAPI vs. Node.js?)
2. **Provide accounts table** with all account details
3. **Define scenario** (which steps to record?)
4. **Set up project structure** and environment variables
5. **Build Phase 1** features
