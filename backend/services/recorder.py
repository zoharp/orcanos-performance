"""
Recording session manager.
Runs Playwright in a background thread so the FastAPI server stays responsive.
"""

import threading
import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

_RECORDER_JS = """
(function() {
    if (window.__orcanosRecorder) return;
    window.__orcanosRecorder = true;

    function bestSelector(el) {
        if (el.id && !/^\\d/.test(el.id)) return '#' + el.id;
        const name = el.getAttribute('name');
        if (name) return el.tagName.toLowerCase() + '[name="' + name + '"]';
        const ariaLabel = el.getAttribute('aria-label');
        if (ariaLabel) return el.tagName.toLowerCase() + '[aria-label="' + ariaLabel + '"]';
        const dataAction = el.getAttribute('data-action');
        if (dataAction) return el.tagName.toLowerCase() + '[data-action="' + dataAction + '"]';
        if ((el.tagName === 'BUTTON' || el.tagName === 'A') && el.textContent.trim()) {
            return el.tagName.toLowerCase() + ':has-text("' + el.textContent.trim().slice(0, 40).replace(/"/g, "'") + '")';
        }
        if (el.className && typeof el.className === 'string') {
            const cls = el.className.trim().split(/\\s+/)
                .filter(c => c.length > 2 && !/^(ng-|active|focus|hover|open|show|selected)/.test(c))
                .slice(0, 2).join('.');
            if (cls) return el.tagName.toLowerCase() + '.' + cls;
        }
        return el.tagName.toLowerCase();
    }

    document.addEventListener('click', function(e) {
        const el = e.target.closest('button, a, [role="button"], [role="link"], input[type="submit"], input[type="button"], input[type="checkbox"], input[type="radio"]') || e.target;
        if (!el || ['HTML','BODY','INPUT','TEXTAREA','SELECT'].includes(el.tagName)) return;
        const sel = bestSelector(el);
        const lbl = el.textContent.trim().slice(0, 50) || el.getAttribute('aria-label') || el.getAttribute('title') || sel;
        window.__recordAction({ type: 'click', selector: sel, label: lbl });
    }, true);

    document.addEventListener('blur', function(e) {
        const el = e.target;
        if (!el || (el.tagName !== 'INPUT' && el.tagName !== 'TEXTAREA')) return;
        if (el.type === 'submit' || el.type === 'button') return;
        if (!el.value) return;
        const sel = bestSelector(el);
        const isPassword = el.type === 'password';
        const isEmail = el.type === 'email' || (el.name || '').toLowerCase().includes('email') || (el.id || '').toLowerCase().includes('email');
        const placeholder = el.getAttribute('placeholder') || el.getAttribute('name') || 'input';
        window.__recordAction({
            type: 'fill',
            selector: sel,
            value: isPassword ? '{{PASSWORD}}' : (isEmail ? '{{USER}}' : el.value),
            label: placeholder
        });
    }, true);
})();
"""


class RecordingSession:
    def __init__(self):
        self._lock = threading.Lock()
        self.active = False
        self.steps: List[Dict] = []
        self.name: Optional[str] = None
        self.url: Optional[str] = None
        self.version: str = ""
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    def start(self, name: str, url: str, version: str = ""):
        with self._lock:
            if self.active:
                raise RuntimeError("Recording already in progress")
            self.active = True
            self.steps = []
            self.name = name
            self.url = url
            self.version = version
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> Optional[str]:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=15)
        with self._lock:
            self.active = False
            steps_snapshot = list(self.steps)
        return self._save(steps_snapshot) if steps_snapshot else None

    def get_status(self) -> Dict:
        with self._lock:
            return {
                "active": self.active,
                "name": self.name,
                "step_count": len(self.steps),
                "steps": list(self.steps),
            }

    def _add_step(self, data: Dict):
        t = data.get("type", "")
        sel = data.get("selector", "")
        lbl = data.get("label", sel)
        val = data.get("value")

        name = {"click": f"Click: {lbl}", "fill": f"Fill: {lbl}", "navigate": f"Navigate to {lbl}"}.get(t, f"{t}: {lbl}")

        with self._lock:
            # Deduplicate consecutive fills to the same field
            if t == "fill" and self.steps and self.steps[-1]["action"] == "fill" and self.steps[-1]["target"] == sel:
                self.steps[-1]["value"] = val
                return
            self.steps.append({"name": name, "action": t, "target": sel, "value": val, "expected_result": None})

    def _run(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._async_run())
        finally:
            loop.close()
            with self._lock:
                self.active = False

    async def _async_run(self):
        from playwright.async_api import async_playwright
        prev_url = [self.url]

        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=False)
                context = await browser.new_context()

                async def on_action(source, data):
                    self._add_step(data)

                await context.expose_binding("__recordAction", on_action)
                await context.add_init_script(script=_RECORDER_JS)

                page = await context.new_page()

                def on_navigated(frame):
                    if frame != page.main_frame:
                        return
                    url = frame.url
                    if not url or url == prev_url[0] or url.startswith("about:") or url.startswith("data:"):
                        return
                    try:
                        from urllib.parse import urlparse
                        parts = [seg for seg in urlparse(url).path.rstrip("/").split("/") if seg]
                        label = parts[-1] if parts else url
                    except Exception:
                        label = url[:50]
                    self._add_step({"type": "navigate", "selector": url, "label": label, "value": None})
                    prev_url[0] = url

                page.on("framenavigated", on_navigated)
                await page.goto(self.url)

                while not self._stop_event.is_set():
                    await asyncio.sleep(0.3)
                    if not browser.is_connected():
                        break

                if browser.is_connected():
                    await browser.close()
        except Exception as e:
            print(f"[Recorder] Error: {e}")

    def _save(self, steps: List[Dict]) -> str:
        import os
        scenarios_dir = Path(os.getenv("SCENARIOS_DIR", str(Path(__file__).parent.parent / "scenarios")))
        scenarios_dir.mkdir(exist_ok=True)
        filepath = scenarios_dir / f"{self.name}.json"
        data = {
            "name": self.name,
            "version": self.version,
            "base_url": self.url,
            "user": "orcanos.tech",
            "created_at": datetime.utcnow().isoformat(),
            "steps": steps,
        }
        filepath.write_text(json.dumps(data, indent=2))
        return str(filepath)


session = RecordingSession()
