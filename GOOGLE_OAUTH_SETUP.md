# Google OAuth Setup & Implementation Guide

## Quick Start

### 1. Create Google OAuth Credentials
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID** → **Web application**
5. Add authorized JavaScript origins:
   - `http://localhost:5173` (local dev)
   - `https://orcanos-performance.fly.dev` (production)
6. Copy the **Client ID** (format: `123456.apps.googleusercontent.com`)

### 2. Configure Environment Variables

**Local development (`.env`):**
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

**Frontend (`.env.local` in `frontend/` directory):**
```bash
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### 3. Run Locally
```bash
npm run dev  # Frontend shows both Google button + dev-only admin login
run.bat      # Full stack (backend + frontend + browser)
```

### 4. Deploy to Fly.io
```bash
flyctl secrets set GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
flyctl deploy
```

---

## How It Works

### Frontend Flow
- **Development mode** (`npm run dev`): Shows "Sign in with Google" button + collapsible "Admin login (development only)" section
- **Production mode** (after `npm run build`): Shows only Google button; admin login completely hidden
- Uses Google Identity Services (GIS) SDK for native "Sign in with Google" button
- On click, Google popup appears → user authenticates → browser sends ID token to backend

### Backend Flow
1. `POST /api/auth/google` receives `{credential: <id-token>}`
2. `verify_google_token()` in `auth.py`:
   - Verifies token with Google's public keys
   - Checks `email` ends with `@orcanos.com`
   - Returns `{email, name, sub}`
3. Upserts User record (find by email, create if new)
4. Issues JWT token (same format as password login)
5. Frontend stores token in `localStorage`

### User Model Changes
- Added `email` column (unique, nullable)
- Made `hashed_password` nullable (NULL for OAuth users, populated for password users)
- Google OAuth users: `email` set, `hashed_password = NULL`
- Password users: `email = NULL`, `hashed_password` set

### Admin Login (Fallback)
- Username/password login still works but is hidden on production
- Development only for testing when Google OAuth unavailable
- Seeded with `admin`/`ADMIN_PASSWORD` and `user`/`USER_PASSWORD` env vars

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| "Google Sign-In library failed to load" | `VITE_GOOGLE_CLIENT_ID` missing or script didn't load | Check `.env.local`, hard-refresh (Ctrl+Shift+R) |
| "Access restricted to Orcanos employees" | Non-@orcanos.com account used | Sign in with @orcanos.com Google account |
| "Token verification failed" | Client ID mismatch or authorized origins missing | Verify both backend/frontend have same Client ID; add origins to Google Cloud project |
| "Invalid Google token" | Browser popup blocked | Check browser console; ensure localhost:5173 in authorized origins |
| Admin login visible on production | Environment detection not working | Check `import.meta.env.MODE` in browser console (should be 'production' after build) |

---

## Implementation Details

### Database Migration
- Automatic on startup via `init_db()` in `database.py`
- Detects missing `email` column and adds it
- Detects `NOT NULL` constraint on `hashed_password` and rebuilds table to allow NULL
- No manual migration needed

### Endpoints
- `POST /api/auth/login` — username/password (existing)
- `POST /api/auth/google` — Google OAuth (new)
- `POST /api/auth/logout` — stateless (existing)

### Dependencies Added
- `google-auth>=2.29.0` — OAuth token verification

### Key Files Modified
- `backend/models.py` — added `email` column, made `hashed_password` nullable
- `backend/services/auth.py` — added `verify_google_token()`
- `backend/services/database.py` — added migration for schema changes
- `backend/routes/auth.py` — added `/api/auth/google` endpoint
- `frontend/index.html` — added Google GIS script tag
- `frontend/src/pages/Login.jsx` — redesigned login UI, environment-aware
- `requirements.txt` — added `google-auth`
- `.env.example` — documented `GOOGLE_CLIENT_ID`
