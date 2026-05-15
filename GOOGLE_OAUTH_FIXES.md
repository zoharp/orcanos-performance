# Google OAuth Implementation — Issues & Fixes

## Issue: NOT NULL constraint failed on hashed_password

**Problem:** The original User table had `hashed_password` marked as `NOT NULL`, but Google OAuth users don't have passwords (they use Google's auth instead).

**Fix Applied:**
1. Updated `backend/models.py` to set `hashed_password` as `nullable=True`
2. Added a database migration in `backend/services/database.py` that:
   - Detects when the `hashed_password` column still has a NOT NULL constraint
   - Rebuilds the users table without the constraint
   - Preserves all existing user data
   - Automatically runs on next app startup

**Schema Change:**
```sql
-- Before
hashed_password VARCHAR(256) NOT NULL

-- After
hashed_password VARCHAR(256)  -- now nullable
```

## Testing Checklist

✓ Google-auth library imports successfully  
✓ Auth module imports without errors  
✓ Routes module imports without errors  
✓ User model has email column  
✓ hashed_password column is nullable in new database  
✓ Google OAuth users can be created without passwords  
✓ JWT tokens can be generated for Google OAuth users  

## Next Steps

1. **Get your Google OAuth Client ID** (see GOOGLE_OAUTH_SETUP.md)
2. **Update .env and .env.local** with the Client ID
3. **Run `run.bat`** to start the app
4. **Test sign in** with your @orcanos.com Google account

The database will auto-migrate on startup if needed.
