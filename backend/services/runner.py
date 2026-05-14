"""
Test runner — replays a recorded scenario against all enabled accounts.
Runs Playwright headless in a background thread.
"""

import threading
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse

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
            }
        self._thread = threading.Thread(
            target=self._run,
            args=(run_id, scenario_name, accounts),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        self._stop_event.set()

    def get_progress(self, run_id: int) -> Optional[dict]:
        with self._lock:
            return dict(self._runs.get(run_id, {}))

    def _run(self, run_id: int, scenario_name: str, accounts: List[dict]):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            config = _load_config()
            run_timeout_s = int(config.get("run_timeout_seconds", 300))  # 5 min per account by default
            total_timeout_s = run_timeout_s * len(accounts)
            loop.run_until_complete(asyncio.wait_for(self._async_run(run_id, scenario_name, accounts), timeout=total_timeout_s))
        except asyncio.TimeoutError:
            print(f"[RUNNER] RUN TIMEOUT after {total_timeout_s}s, marking as timed_out")
            with self._lock:
                self._runs[run_id]["status"] = "timed_out"
            from backend.services.database import SessionLocal
            from backend.models import TestRun
            db = SessionLocal()
            try:
                run = db.query(TestRun).filter(TestRun.id == run_id).first()
                if run:
                    run.status = "timed_out"
                    run.completed_at = datetime.utcnow()
                    db.commit()
            finally:
                db.close()
        finally:
            loop.close()
            with self._lock:
                self.active = False

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
        db = SessionLocal()

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
                for acct in accounts:
                    with self._lock:
                        self._runs[run_id]["current_account"] = acct["name"]

                    password = enc.decrypt(acct["encrypted_password"])
                    account_url = acct["url"]
                    tgt_account = acct["name"]

                    # Extract domain from account URL
                    parsed_url = urlparse(account_url)
                    account_domain = f"{parsed_url.scheme}://{parsed_url.netloc}"

                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    timed_out = False

                    if account_url:
                        print(f"[RUNNER] Navigating to {account_url}")
                        await page.goto(account_url, wait_until="load", timeout=step_timeout_ms)
                        print(f"[RUNNER] Page loaded")

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

                        print(f"[RUNNER] Step: {step['name']} (action={action}, target={target})")

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

                        def on_response(resp, _starts=step_req_starts, _reqs=step_requests, _step=step["name"], _acct=acct["name"]):
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
                            print(f"[RUNNER]   Executing {action}...")
                            if action == "navigate":
                                await page.goto(target, wait_until="load", timeout=step_timeout_ms)
                            elif action == "fill":
                                await page.fill(target, value or "", timeout=step_timeout_ms)
                            elif action == "click":
                                await page.click(target, timeout=step_timeout_ms)
                                try:
                                    await page.wait_for_load_state("load", timeout=step_timeout_ms)
                                except PlaywrightTimeout:
                                    pass
                            print(f"[RUNNER]   {action} completed")
                        except PlaywrightTimeout:
                            step_timed_out = True
                            error_msg = f"timeout({step_timeout_s}s)"
                            print(f"[RUNNER]   TIMEOUT: {error_msg}")
                        except Exception as e:
                            error_msg = str(e)[:500]
                            print(f"[RUNNER]   ERROR: {error_msg}")

                        page.remove_listener("request", on_request)
                        page.remove_listener("response", on_response)

                        duration = time.monotonic() - t0

                        sr = StepResult(
                            run_id=run_id,
                            account_id=acct["id"],
                            step_name=step["name"],
                            start_time=t_start,
                            end_time=datetime.utcnow(),
                            duration_seconds=round(duration, 3),
                            status="timeout" if step_timed_out else ("failed" if error_msg else _step_status(duration, pass_t, warn_t)),
                            error_message=error_msg,
                            requests=step_requests or None,
                        )
                        db.add(sr)
                        db.commit()

                        if step_timed_out or self._stop_event.is_set():
                            timed_out = True
                            break  # skip remaining steps for this account

                    try:
                        await asyncio.wait_for(browser.close(), timeout=10)
                    except (asyncio.TimeoutError, Exception) as e:
                        print(f"[RUNNER] browser.close() error (ignoring): {e}")

                    with self._lock:
                        self._runs[run_id]["completed_accounts"] += 1

                    if self._stop_event.is_set():
                        break

            stopped = self._stop_event.is_set()
            final_status = "stopped" if stopped else "completed"

            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if run:
                run.status = final_status
                run.completed_at = datetime.utcnow()
                db.commit()

            with self._lock:
                self._runs[run_id]["status"] = final_status
                self._runs[run_id]["current_account"] = None

        except Exception as e:
            print(f"[RUNNER] FATAL: {e}")
            import traceback; traceback.print_exc()
            with self._lock:
                self._runs[run_id]["status"] = "failed"

            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if run:
                run.status = "failed"
                run.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()


runner = RunnerSession()
