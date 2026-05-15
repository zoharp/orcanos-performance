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
                "status": "starting",
                "browser": None,
                "page": None,
                "last_activity": time.time(),
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
                return {"status": "inactive"}

            last_activity = session.get("last_activity", 0)
            elapsed = time.time() - last_activity
            inactivity_seconds = int(300 - elapsed)  # 5 min = 300s

            return {
                "status": session.get("status"),
                "error": session.get("error"),
                "inactivity_seconds": max(0, inactivity_seconds),
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
            loop.run_until_complete(self._run_async(account_id, account_url, email, password))
        except Exception as e:
            logger.error(f"[Account {account_id}] Manual test error: {e}")
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
            # Open headed Chromium browser (user can see it)
            try:
                browser = await p.chromium.launch(headless=False)
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
                    await page.goto(login_url, wait_until="domcontentloaded", timeout=15000)
                except Exception as e:
                    # Try alternate login path with capital A
                    logger.warning(f"[Account {account_id}] Failed to load {login_url}, trying /Account/Login")
                    login_url_alt = account_url.rstrip('/') + '/Account/Login'
                    await page.goto(login_url_alt, wait_until="domcontentloaded", timeout=15000)

                logger.info(f"[Account {account_id}] Page loaded, URL: {page.url}")

                # Fill email
                logger.info(f"[Account {account_id}] Waiting for login email field...")
                await page.wait_for_selector("#kabab-login", state="visible", timeout=5000)
                await page.fill("#kabab-login", email)
                logger.info(f"[Account {account_id}] Email filled")

                # Fill password
                logger.info(f"[Account {account_id}] Waiting for password field...")
                await page.wait_for_selector("#kabab-password", state="visible", timeout=5000)
                await page.fill("#kabab-password", password)
                logger.info(f"[Account {account_id}] Password filled")

                # Click login
                logger.info(f"[Account {account_id}] Waiting for login button...")
                await page.wait_for_selector("#kabab-btn-loading", state="visible", timeout=5000)
                logger.info(f"[Account {account_id}] Clicking login button")
                await page.click("#kabab-btn-loading")

                # Wait for page to load
                logger.info(f"[Account {account_id}] Waiting for page to load after login...")
                await page.wait_for_load_state("domcontentloaded", timeout=15000)
                logger.info(f"[Account {account_id}] Login successful, final URL: {page.url}")

                with self._lock:
                    self.active_sessions[account_id]["status"] = "ready"
                    self.active_sessions[account_id]["last_activity"] = time.time()

                logger.info(f"[Account {account_id}] Manual test session ready")

                # Monitor inactivity — close after 5 min (300s) with no activity
                # Track activity via page interactions or user closing the window
                last_title = None
                while True:
                    await asyncio.sleep(5)  # Check every 5s

                    with self._lock:
                        if account_id not in self.active_sessions:
                            break  # Session was stopped

                    # Check if page is still alive (user hasn't closed it)
                    try:
                        title = await page.title()
                        # If title changed, user is interacting - reset inactivity timer
                        if title != last_title:
                            last_title = title
                            with self._lock:
                                if account_id in self.active_sessions:
                                    self.active_sessions[account_id]["last_activity"] = time.time()
                    except Exception:
                        logger.info(f"[Account {account_id}] Browser was closed by user")
                        break

                    # Check inactivity timeout
                    with self._lock:
                        if account_id in self.active_sessions:
                            elapsed = time.time() - self.active_sessions[account_id]["last_activity"]
                            if elapsed > 300:  # 5 minutes
                                logger.info(f"[Account {account_id}] Closing session due to inactivity")
                                break

            except Exception as e:
                logger.error(f"[Account {account_id}] Login failed: {e}")
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
