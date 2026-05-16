"""
Manual test session — return app URL. Simple and works everywhere.
"""


class ManualTesterSession:
    def __init__(self):
        self.active_sessions = {}

    def start(self, account_id: int, account_url: str, email: str, password: str):
        """Start manual test — return app URL."""
        if account_id in self.active_sessions:
            del self.active_sessions[account_id]

        app_url = account_url.rstrip('/') + '/'

        self.active_sessions[account_id] = {
            "status": "success",
            "app_url": app_url,
            "error": None,
        }

        print(f"[Account {account_id}] Test ready: {app_url}")

    def stop(self, account_id: int):
        """Stop/cleanup a session."""
        if account_id in self.active_sessions:
            del self.active_sessions[account_id]

    def get_status(self, account_id: int):
        """Get session status."""
        session = self.active_sessions.get(account_id)
        if not session:
            return {"status": "inactive", "app_url": None, "error": None}
        return {
            "status": session.get("status"),
            "error": session.get("error"),
            "app_url": session.get("app_url"),
        }


_session = ManualTesterSession()


def get_manual_tester_session():
    return _session
