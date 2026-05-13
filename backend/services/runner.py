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

SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"

PASS_THRESHOLD = 3.0
WARN_THRESHOLD = 8.0


def _step_status(duration: float) -> str:
    if duration < PASS_THRESHOLD:
        return "pass"
    elif duration < WARN_THRESHOLD:
        return "warning"
    return "critical"


class RunnerSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.active = False
        self._runs: Dict[int, dict] = {}
        self._thread: Optional[threading.Thread] = None

    def start(self, run_id: int, scenario_name: str, accounts: List[dict]):
        with self._lock:
            if self.active:
                raise RuntimeError("A test run is already in progress")
            self.active = True
            self._runs[run_id] = {
                "status": "running",
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
        from playwright.async_api import async_playwright
        from backend.services.database import SessionLocal
        from backend.models import StepResult, TestRun
        from backend.services.encryption import get_encryption_service

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

                        try:
                            if action == "navigate":
                                await page.goto(target, wait_until="networkidle", timeout=30000)
                            elif action == "fill":
                                await page.fill(target, value or "", timeout=10000)
                            elif action == "click":
                                await page.click(target, timeout=10000)
                                try:
                                    await page.wait_for_load_state("networkidle", timeout=10000)
                                except Exception:
                                    pass
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
                            status="failed" if error_msg else _step_status(duration),
                            error_message=error_msg,
                        )
                        db.add(sr)
                        db.commit()

                    await browser.close()

                    with self._lock:
                        self._runs[run_id]["completed_accounts"] += 1

            run = db.query(TestRun).filter(TestRun.id == run_id).first()
            if run:
                run.status = "completed"
                run.completed_at = datetime.utcnow()
                db.commit()

            with self._lock:
                self._runs[run_id]["status"] = "completed"
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
