"""
Manual testing session — opens a Chrome browser and auto-logs in to an account.
User can then manually explore the account. Browser auto-closes after 5 min inactivity.
"""

import threading
import asyncio
import time
import logging
from typing import Optional, Dict
from urllib.parse import urlparse

logger = logging.getLogger("manual_tester")


class ManualTesterSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.active_sessions: Dict[int, dict] = {}  # {account_id: {status, browser, page, last_activity, thread}}
        self._current_loop = None

    def start(self, account_id: int, account_url: str, email: str, password: str):
        """Start a manual test session for an account."""
        with self._lock:
            if account_id in self.active_sessions:
                raise RuntimeError(f"Session already active for account {account_id}")

            self.active_sessions[account_id] = {
                "status": "logging_in",
                "browser": None,
                "page": None,
                "app_url": None,
                "error": None,
            }

        thread = threading.Thread(
            target=self._run,
            args=(account_id, account_url, email, password),
            daemon=True,
        )
        thread.start()

    def stop(self, account_id: int):
        """Stop a manual test session."""
        with self._lock:
            session = self.active_sessions.get(account_id)
            if not session:
                return

            loop = self._current_loop
            browser = session.get("browser")
            page = session.get("page")

            if page:
                asyncio.run_coroutine_threadsafe(self._safe_close_page(page), loop) if loop else None
            if browser:
                asyncio.run_coroutine_threadsafe(self._safe_close_browser(browser), loop) if loop else None

            del self.active_sessions[account_id]

    def get_status(self, account_id: int) -> dict:
        """Get status of a session."""
        with self._lock:
            session = self.active_sessions.get(account_id)
            if not session:
                return {"status": "inactive", "app_url": None, "error": None}

            return {
                "status": session.get("status"),
                "error": session.get("error"),
                "app_url": session.get("app_url"),
            }

    async def _safe_close_page(self, page):
        try:
            await page.close()
        except Exception:
            pass

    async def _safe_close_browser(self, browser):
        try:
            await browser.close()
        except Exception:
            pass

    def _run(self, account_id: int, account_url: str, email: str, password: str):
        """Run the manual test session."""
        from playwright.async_api import async_playwright

        try:
            asyncio.set_event_loop(asyncio.new_event_loop())
            loop = asyncio.get_event_loop()
            self._current_loop = loop
            loop.run_until_complete(asyncio.wait_for(self._run_async(account_id, account_url, email, password), timeout=60))
        except asyncio.TimeoutError:
            logger.error(f"[Account {account_id}] Manual test timed out after 60 seconds")
            with self._lock:
                if account_id in self.active_sessions:
                    self.active_sessions[account_id]["error"] = "Login timeout (60s) - page took too long to load"
        except Exception as e:
            logger.error(f"[Account {account_id}] Manual test error: {e}", exc_info=True)
            with self._lock:
                if account_id in self.active_sessions:
                    self.active_sessions[account_id]["error"] = str(e)[:200]
        finally:
            with self._lock:
                if account_id in self.active_sessions:
                    self.active_sessions[account_id]["status"] = "closed"

    async def _run_async(self, account_id: int, account_url: str, email: str, password: str):
        """Async version of the manual test runner."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Open headless Chromium browser to test login
            try:
                browser = await p.chromium.launch(headless=True)
            except Exception as e:
                logger.error(f"[Account {account_id}] Failed to launch browser: {e}")
                raise
            page = await browser.new_page()

            with self._lock:
                self.active_sessions[account_id]["browser"] = browser
                self.active_sessions[account_id]["page"] = page
                self.active_sessions[account_id]["status"] = "logging_in"

            logger.info(f"[Account {account_id}] Opening {account_url}")

            try:
                # Build login URL from account URL
                # Try to detect the correct login path from the account URL structure
                if account_url.endswith('/'):
                    login_url = account_url + 'account/login'
                else:
                    login_url = account_url + '/account/login'

                # Navigate to login page
                logger.info(f"[Account {account_id}] Navigating to {login_url}")
                try:
                    await asyncio.wait_for(page.goto(login_url, wait_until="domcontentloaded", timeout=20000), timeout=25)
                except Exception as e:
                    # Try alternate login path with capital A
                    logger.warning(f"[Account {account_id}] Failed to load {login_url}, trying /Account/Login: {e}")
                    login_url_alt = account_url.rstrip('/') + '/Account/Login'
                    await asyncio.wait_for(page.goto(login_url_alt, wait_until="domcontentloaded", timeout=20000), timeout=25)

                logger.info(f"[Account {account_id}] Page loaded, URL: {page.url}")

                # Fill email
                logger.info(f"[Account {account_id}] Waiting for login email field...")
                await asyncio.wait_for(page.wait_for_selector("#kabab-login", state="attached", timeout=20000), timeout=25)
                await page.fill("#kabab-login", email)
                logger.info(f"[Account {account_id}] Email filled")

                # Fill password
                logger.info(f"[Account {account_id}] Waiting for password field...")
                await asyncio.wait_for(page.wait_for_selector("#kabab-password", state="attached", timeout=20000), timeout=25)
                await page.fill("#kabab-password", password)
                logger.info(f"[Account {account_id}] Password filled")

                # Click login
                logger.info(f"[Account {account_id}] Waiting for login button...")
                await asyncio.wait_for(page.wait_for_selector("#kabab-btn-loading", state="attached", timeout=20000), timeout=25)
                logger.info(f"[Account {account_id}] Clicking login button")
                await page.click("#kabab-btn-loading")

                # Wait for page to load
                logger.info(f"[Account {account_id}] Waiting for page to load after login...")
                await asyncio.wait_for(page.wait_for_load_state("domcontentloaded", timeout=20000), timeout=25)
                logger.info(f"[Account {account_id}] Login successful, final URL: {page.url}")

                # Login successful - get the app URL
                final_url = page.url
                logger.info(f"[Account {account_id}] Login successful, final URL: {final_url}")

                with self._lock:
                    if account_id in self.active_sessions:
                        self.active_sessions[account_id]["status"] = "success"
                        self.active_sessions[account_id]["app_url"] = final_url

            except Exception as e:
                logger.error(f"[Account {account_id}] Login failed: {e}", exc_info=True)
                with self._lock:
                    if account_id in self.active_sessions:
                        self.active_sessions[account_id]["error"] = str(e)[:200]

            finally:
                try:
                    await page.close()
                except Exception:
                    pass
                try:
                    await browser.close()
                except Exception:
                    pass

                with self._lock:
                    if account_id in self.active_sessions:
                        del self.active_sessions[account_id]


_session = ManualTesterSession()


def get_manual_tester_session() -> ManualTesterSession:
    return _session
