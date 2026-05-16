"""
Manual test — silent login with Playwright, then return authenticated app URL.
"""

import tempfile
import os
import subprocess
import sys


class ManualTesterSession:
    def __init__(self):
        self.active_sessions = {}

    def start(self, account_id: int, account_url: str, email: str, password: str):
        """Start manual test — log in silently and return app URL."""
        if account_id in self.active_sessions:
            del self.active_sessions[account_id]

        self.active_sessions[account_id] = {
            "status": "running",
            "app_url": None,
            "error": None,
        }

        print(f"[Account {account_id}] Starting login...")

        # Write script to temp file
        script = f'''
import os
from playwright.sync_api import sync_playwright

try:
    is_production = os.getenv("ENVIRONMENT") == "production"
    print(f"Starting browser (headless={{is_production}})...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=is_production)
        page = browser.new_page()

        # Build login URL
        base_url = "{account_url}".rstrip("/")
        if base_url.endswith("/account/login") or base_url.endswith("/Account/Login"):
            login_url = base_url
        else:
            login_url = base_url + "/account/login"

        print(f"Navigating to {{login_url}}")
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)

        print("Filling email...")
        page.fill("#kabab-login", "{email}")
        page.fill("#kabab-password", "{password}")

        print("Clicking login...")
        page.click("#kabab-btn-loading")

        print("Waiting for login...")
        page.wait_for_load_state("domcontentloaded", timeout=30000)

        final_url = page.url

        # Extract cookies
        cookies = page.context.cookies()
        cookies_str = '|'.join([f"{{c['name']}}={{c['value']}}" for c in cookies])

        print(f"SUCCESS:{{final_url}}|||{{cookies_str}}")

        print("Browser stays open - close manually when done")
        import time
        time.sleep(3600)  # Keep browser open for 1 hour

except Exception as e:
    print(f"ERROR:{{str(e)[:150]}}")
'''

        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(script)
            script_path = f.name

        try:
            env = os.environ.copy()
            process = subprocess.Popen(
                [sys.executable, script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
            )

            try:
                stdout, stderr = process.communicate(timeout=40)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                self.active_sessions[account_id]["status"] = "closed"
                self.active_sessions[account_id]["error"] = "Timeout (40s)"
                print(f"[Account {account_id}] Timeout")
                return

            print(f"[Account {account_id}] Output: {stdout}")
            if stderr:
                print(f"[Account {account_id}] Error output: {stderr}")

            # Parse output
            for line in stdout.split('\n'):
                if line.startswith('SUCCESS:'):
                    parts = line[8:].split('|||')
                    app_url = parts[0]
                    cookies_str = parts[1] if len(parts) > 1 else ""
                    self.active_sessions[account_id]["status"] = "success"
                    self.active_sessions[account_id]["app_url"] = app_url
                    self.active_sessions[account_id]["cookies"] = cookies_str
                    print(f"[Account {account_id}] Login success: {app_url}")
                    return
                elif line.startswith('ERROR:'):
                    error = line[6:]
                    self.active_sessions[account_id]["status"] = "closed"
                    self.active_sessions[account_id]["error"] = error
                    print(f"[Account {account_id}] Login failed: {error}")
                    return

            # No success/error in output
            self.active_sessions[account_id]["status"] = "closed"
            self.active_sessions[account_id]["error"] = "No response"
            print(f"[Account {account_id}] No response from login")

        except Exception as e:
            self.active_sessions[account_id]["status"] = "closed"
            self.active_sessions[account_id]["error"] = str(e)[:150]
            print(f"[Account {account_id}] Exception: {e}")
        finally:
            try:
                os.unlink(script_path)
            except:
                pass

    def stop(self, account_id: int):
        """Stop/cleanup a session."""
        if account_id in self.active_sessions:
            del self.active_sessions[account_id]

    def get_status(self, account_id: int):
        """Get session status."""
        session = self.active_sessions.get(account_id)
        if not session:
            return {"status": "inactive", "app_url": None, "error": None, "cookies": None}
        return {
            "status": session.get("status"),
            "error": session.get("error"),
            "app_url": session.get("app_url"),
            "cookies": session.get("cookies"),
        }


_session = ManualTesterSession()


def get_manual_tester_session():
    return _session
