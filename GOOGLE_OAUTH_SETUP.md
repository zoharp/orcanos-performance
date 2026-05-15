# Google OAuth Setup Guide

## Step 1: Create Google Cloud Project & OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or use an existing one)
3. Go to **APIs & Services** → **Credentials**
4. Click **Create Credentials** → **OAuth 2.0 Client ID**
5. Choose **Web application**
6. Add authorized JavaScript origins:
   - `http://localhost:5173` (local Vite dev server)
   - `https://orcanos-performance.fly.dev` (production)
7. Click **Create**
8. Copy the **Client ID** (something like `123456.apps.googleusercontent.com`)

## Step 2: Configure `.env` Files

### Backend (`.env`)
Add or update:
```bash
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

### Frontend (`.env.local`)
Add:
```bash
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

**Note:** The Client ID is the same for both backend and frontend.

## Step 3: Deploy to Fly.io

Once working locally, deploy the secrets to production:
```bash
flyctl secrets set GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Then deploy:
```bash
flyctl deploy
```

---

## How It Works

**Google Sign-In Button** (Primary)
- Click → Google popup (same Google account list)
- Authenticate with your @orcanos.com Google account
- Backend verifies the ID token and checks @orcanos.com domain
- Auto-creates user if first login
- Redirects to Dashboard

**Admin Login** (Fallback)
- Expand "Admin login" section
- Enter username + password (same as before)
- Useful for non-Google accounts or offline scenarios

---

## Troubleshooting

**"Google Sign-In library failed to load"**
- Check `VITE_GOOGLE_CLIENT_ID` is set in `.env.local`
- Reload the page (Ctrl+Shift+R to clear cache)

**"Access restricted to Orcanos employees"**
- Only @orcanos.com email addresses are allowed
- Make sure you're signing in with your Orcanos Google account

**"Token verification failed"**
- Your Google Client ID doesn't match the one in the .env
- Make sure both frontend and backend have the same Client ID

**"Invalid Google token"**
- The browser blocked the popup (check console)
- Make sure localhost:5173 is in Google authorized origins

---

## Database Migration

When you start the app, it automatically adds an `email` column to the `users` table if it doesn't exist. No manual migration needed.
