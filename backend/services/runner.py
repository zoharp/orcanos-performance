"""
Test runner — replays a recorded scenario against all enabled accounts.
Runs Playwright headless in a background thread.
"""

import threading
import asyncio
import json
import time
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

logger = logging.getLogger("runner")

import os as _os
SCENARIOS_DIR = Path(_os.getenv("SCENARIOS_DIR", str(Path(__file__).parent.parent / "scenarios")))
CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

def _load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _step_status(duration: float, pass_t: float, warn_t: float) -> str:
    if duration < pass_t:
        return "pass"
    elif duration < warn_t:
        return "warning"
    return "critical"


class RunnerSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.active = False
        self._runs: Dict[int, dict] = {}
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._current_page = None
        self._current_browser = None

    def start(self, run_id: int, scenario_name: str, accounts: List[dict]):
        with self._lock:
            if self.active:
                raise RuntimeError("A test run is already in progress")
            self.active = True
            self._stop_event.clear()
            self._runs[run_id] = {
                "status": "running",
                "scenario_name": scenario_name,
                "current_account": None,
                "completed_accounts": 0,
                "total_accounts": len(accounts),
                "recent_requests": [],
                "error": None,
                "failed_at_account": None,
            }
        self._thread = threading.Thread(
            target=self._run,
            args=(run_id, scenario_name, accounts),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        # Force close current page/browser to interrupt any waiting operations
        if self._current_page:
            try:
                self._current_page.close()
            except Exception:
                pass
        if self._current_browser:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                loop.create_task(self._current_browser.close())
            except Exception:
                pass

    def get_progress(self, run_id: int) -> Optional[dict]:
        with self._lock:
            progress = dict(self._runs.get(run_id, {}))
            if progress:
                total = progress.get("total_accounts", 1)
                completed = progress.get("completed_accounts", 0)
                progress["completion_percent"] = int((completed / total) * 100) if total > 0 else 0
            return progress

    def _run(self, run_id: int, scenario_name: str, accounts: List[dict]):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            logger.info(f"[RUNNER] Starting run {run_id} with {len(accounts)} accounts")
            loop.run_until_complete(self._async_run(run_id, scenario_name, accounts))
        except Exception as e:
            logger.error(f"[RUNNER] Run {run_id} failed: {e}", exc_info=True)
            with self._lock:
                self._runs[run_id]["status"] = "failed"
                self._runs[run_id]["error"] = str(e)[:500]
        finally:
            loop.close()
            with self._lock:
                self.active = False
                logger.info(f"[RUNNER] Run {run_id} completed with status: {self._runs[run_id].get('status')}")

    async def _async_run(self, run_id: int, scenario_name: str, accounts: List[dict]):
        from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
        from backend.services.database import SessionLocal
        from backend.models import StepResult, TestRun
        from backend.services.encryption import get_encryption_service

        config = _load_config()
        step_timeout_s = int(config.get("step_timeout_seconds", 45))
        step_timeout_ms = step_timeout_s * 1000
        pass_t = float(config.get("pass_threshold_seconds", 3))
        warn_t = float(config.get("warn_threshold_seconds", 8))

        scenario_path = SCENARIOS_DIR / f"{scenario_name}.json"
        scenario = json.loads(scenario_path.read_text())
        steps = scenario["steps"]

        enc = get_encryption_service()

        # Extract source account name from first step target URL
        src_account = None
        for step in steps:
            target = step.get("target", "")
            if target.startswith("http"):
                try:
                    path = urlparse(target).path.strip("/").split("/")[0]
                    if path:
                        src_account = path
                        break
                except Exception:
                    pass

        try:
            async with async_playwright() as p:
                for idx, acct in enumerate(accounts):
                    account_name = acct["name"]
                    completed_before = idx
                    total = len(accounts)

                    with self._lock:
                        self._runs[run_id]["current_account"] = account_name

                    logger.info(f"[{account_name}] Starting ({completed_before}/{total})")

                    db = SessionLocal()  # Fresh session per account
                    try:
                        password = enc.decrypt(acct["encrypted_password"])
                        account_url = acct["url"]
                        tgt_account = account_name

                        # Extract domain from account URL
                        parsed_url = urlparse(account_url)
                        account_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

                        browser = await p.chromium.launch(headless=True)
                        page = await browser.new_page()
                        timed_out = False

                        with self._lock:
                            self._current_browser = browser
                            self._current_page = page

                        if account_url:
                            logger.info(f"[{account_name}] Navigating to {account_url}")
                            await page.goto(account_url, wait_until="load", timeout=step_timeout_ms)
                            logger.info(f"[{account_name}] Page loaded")

                        run_state_local = {'project_id': None}

                        # Try to extract project ID from page source: current_project: '37'
                        try:
                            pid = await page.evaluate("window.current_project || null")
                            if pid:
                                run_state_local['project_id'] = str(pid)
                                logger.info(f"[{account_name}] Found project ID: {run_state_local['project_id']}")
                        except Exception:
                            pass

                        for step in steps:
                            action = step["action"]
                            target = step["target"]
                            value = step.get("value")

                            # Replace domain and account name in target URLs
                            if target.startswith("http") and src_account and src_account != tgt_account:
                                target = target.replace(f"/{src_account}/", f"/{tgt_account}/")
                                # Replace domain
                                parsed_target = urlparse(target)
                                target_domain = f"{parsed_target.scheme}://{parsed_target.netloc}"
                                if target_domain != account_domain:
                                    target = target.replace(target_domain, account_domain)

                            # Replace project IDs in URLs: find any /web/{oldProjectId}/ and replace with current project ID
                            if target.startswith("http") and run_state_local['project_id']:
                                import re
                                target = re.sub(r'/web/\d+/', f'/web/{run_state_local["project_id"]}/', target)

                            logger.debug(f"[{account_name}] Step: {step['name']} (action={action})")

                            if value:
                                value = (
                                    value
                                    .replace("{{PASSWORD}}", password)
                                    .replace("{{USER}}", "orcanos.tech")
                                )

                            # Per-step network capture
                            step_req_starts: dict = {}
                            step_requests: list = []

                            def on_request(req, _starts=step_req_starts):
                                if req.resource_type in ("xhr", "fetch") and "app.orcanos.com" in req.url:
                                    _starts[req] = time.monotonic()

                            def on_response(resp, _starts=step_req_starts, _reqs=step_requests, _step=step["name"], _acct=account_name):
                                req = resp.request
                                if req in _starts:
                                    dur = round((time.monotonic() - _starts.pop(req)) * 1000)
                                    path = urlparse(req.url).path
                                    entry = {"method": req.method, "url": path, "status": resp.status, "duration_ms": dur}
                                    _reqs.append(entry)
                                    run_state = self._runs.get(run_id)
                                    if run_state is not None and len(run_state["recent_requests"]) < 500:
                                        run_state["recent_requests"].append({**entry, "step": _step, "account": _acct})

                            page.on("request", on_request)
                            page.on("response", on_response)

                            t_start = datetime.utcnow()
                            t0 = time.monotonic()
                            error_msg = None
                            step_timed_out = False

                            try:
                                logger.debug(f"[{account_name}] Executing {action}...")
                                if action == "navigate":
                                    await page.goto(target, wait_until="load", timeout=step_timeout_ms)
                                    # Try to extract project ID from page source after navigate
                                    try:
                                        pid = await page.evaluate("window.current_project || null")
                                        if pid:
                                            run_state_local['project_id'] = str(pid)
                                            logger.debug(f"[{account_name}] Updated project ID: {run_state_local['project_id']}")
                                    except Exception:
                                        pass
                                elif action == "fill":
                                    await page.wait_for_selector(target, state="visible", timeout=step_timeout_ms)
                                    await page.fill(target, value or "", timeout=step_timeout_ms)
                                elif action == "click":
                                    # Add delay for menu popups to appear/animate
                                    await page.wait_for_timeout(800)
                                    # Wait for element to be visible before clicking
                                    try:
                                        await page.wait_for_selector(target, state="visible", timeout=5000)
                                    except PlaywrightTimeout:
                                        # Try without visibility requirement
                                        await page.wait_for_selector(target, timeout=5000)
                                    await page.click(target, timeout=step_timeout_ms)
                                    try:
                                        await page.wait_for_load_state("load", timeout=step_timeout_ms)
                                    except PlaywrightTimeout:
                                        pass
                                logger.debug(f"[{account_name}] {action} completed")
                            except PlaywrightTimeout:
                                step_timed_out = True
                                error_msg = f"timeout({step_timeout_s}s)"
                                logger.error(f"[{account_name}] TIMEOUT: {error_msg}")
                            except Exception as e:
                                error_msg = str(e)[:500]
                                logger.error(f"[{account_name}] Step failed: {error_msg}")

                            page.remove_listener("request", on_request)
                            page.remove_listener("response", on_response)

                            duration = time.monotonic() - t0
                            status = "timeout" if step_timed_out else ("failed" if error_msg else _step_status(duration, pass_t, warn_t))
                            logger.info(f"[{account_name}] Step '{step['name']}': {duration:.2f}s ({status})")

                            sr = StepResult(
                                run_id=run_id,
                                account_id=acct["id"],
                                step_name=step["name"],
                                start_time=t_start,
                                end_time=datetime.utcnow(),
                                duration_seconds=round(duration, 3),
                                status=status,
                                error_message=error_msg,
                                requests=step_requests or None,
                            )
                            db.add(sr)
                            db.commit()

                            if step_timed_out or self._stop_event.is_set():
                                timed_out = True
                                break  # skip remaining steps for this account

                        # Clean up browser for this account
                        try:
                            if page:
                                await page.close()
                        except Exception:
                            pass

                        try:
                            await asyncio.wait_for(browser.close(), timeout=3)
                        except asyncio.TimeoutError:
                            logger.warning(f"[{account_name}] Browser close timeout, force killing")
                        except Exception as e:
                            logger.warning(f"[{account_name}] Browser cleanup error: {e}")

                        with self._lock:
                            self._runs[run_id]["completed_accounts"] += 1
                            self._current_browser = None
                            self._current_page = None

                        logger.info(f"[{account_name}] Completed")

                        if self._stop_event.is_set():
                            break

                    except Exception as e:
                        error_msg = f"Account {account_name}: {str(e)[:500]}"
                        logger.error(f"[RUNNER] {error_msg}", exc_info=True)
                        with self._lock:
                            self._runs[run_id]["error"] = error_msg
                            self._runs[run_id]["failed_at_account"] = account_name
                        raise
                    finally:
                        db.close()

                stopped = self._stop_event.is_set()
                final_status = "stopped" if stopped else "completed"

                db_final = SessionLocal()
                try:
                    run = db_final.query(TestRun).filter(TestRun.id == run_id).first()
                    if run:
                        run.status = final_status
                        run.completed_at = datetime.utcnow()
                        db_final.commit()
                finally:
                    db_final.close()

                with self._lock:
                    self._runs[run_id]["status"] = final_status
                    self._runs[run_id]["current_account"] = None

        except Exception as e:
            logger.error(f"[RUNNER] FATAL: {e}", exc_info=True)
            with self._lock:
                self._runs[run_id]["status"] = "failed"
                self._runs[run_id]["error"] = str(e)[:500]

            db_final = SessionLocal()
            try:
                run = db_final.query(TestRun).filter(TestRun.id == run_id).first()
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.utcnow()
                    db_final.commit()
            finally:
                db_final.close()
        finally:
            with self._lock:
                self._current_browser = None
                self._current_page = None


runner = RunnerSession()
