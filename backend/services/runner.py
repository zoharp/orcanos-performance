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
            loop.run_until_complete(self._async_run(run_id, scenario_name, accounts))
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
        base_url = scenario.get("base_url", "")

        try:
            src_account = urlparse(base_url).path.strip("/").split("/")[0]
        except Exception:
            src_account = ""

        enc = get_encryption_service()
        db = SessionLocal()

        try:
            async with async_playwright() as p:
                for acct in accounts:
                    with self._lock:
                        self._runs[run_id]["current_account"] = acct["name"]

                    password = enc.decrypt(acct["encrypted_password"])
                    tgt_account = acct["name"]

                    browser = await p.chromium.launch(headless=True)
                    page = await browser.new_page()
                    timed_out = False

                    for step in steps:
                        action = step["action"]
                        target = step["target"]
                        value = step.get("value")

                        if src_account and tgt_account != src_account:
                            target = target.replace(f"/{src_account}/", f"/{tgt_account}/")

                        if value:
                            value = (
                                value
                                .replace("{{PASSWORD}}", password)
                                .replace("{{USER}}", "orcanos.tech")
                            )

                        t_start = datetime.utcnow()
                        t0 = time.monotonic()
                        error_msg = None
                        step_timed_out = False

                        try:
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
                        except PlaywrightTimeout:
                            step_timed_out = True
                            error_msg = f"timeout({step_timeout_s}s)"
                        except Exception as e:
                            error_msg = str(e)[:500]

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
                        )
                        db.add(sr)
                        db.commit()

                        if step_timed_out or self._stop_event.is_set():
                            timed_out = True
                            break  # skip remaining steps for this account

                    await browser.close()

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
