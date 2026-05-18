"""
Scenario management routes — recording and listing
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pathlib import Path
from sqlalchemy.orm import Session
import json
from backend.services.auth import get_current_user, require_admin
from backend.services.database import get_db
from backend.models import Account

router = APIRouter(dependencies=[Depends(get_current_user)])

import os
SCENARIOS_DIR = Path(os.getenv("SCENARIOS_DIR", str(Path(__file__).parent.parent / "scenarios")))


class StartRequest(BaseModel):
    name: str
    url: str = "https://app.orcanos.com/orcanos/web/"
    version: str = "6.0"


class EditScenarioRequest(BaseModel):
    name: str
    version: str = ""


@router.post("/record/start")
def start_recording(req: StartRequest):
    from backend.services.recorder import session
    if session.active:
        raise HTTPException(400, "Recording already in progress")
    try:
        session.start(req.name, req.url, req.version)
    except RuntimeError as e:
        raise HTTPException(400, str(e))
    return {"status": "recording", "name": req.name, "url": req.url}


@router.post("/record/stop")
def stop_recording():
    from backend.services.recorder import session
    if not session.active:
        raise HTTPException(400, "No active recording session")
    filepath = session.stop()
    status = session.get_status()
    return {"status": "saved", "filepath": filepath, "steps": status["steps"], "step_count": len(status["steps"])}


@router.get("/record/status")
def recording_status():
    from backend.services.recorder import session
    return session.get_status()


@router.get("")
def list_scenarios(db: Session = Depends(get_db)):
    if not SCENARIOS_DIR.exists():
        return []
    result = []
    for f in sorted(SCENARIOS_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text())
            version = data.get("version", "")
            q = db.query(Account).filter(Account.enabled == True)
            if version:
                q = q.filter(Account.version == version)
            result.append({
                "name": data["name"],
                "version": version,
                "base_url": data.get("base_url", ""),
                "step_count": len(data.get("steps", [])),
                "created_at": data.get("created_at", ""),
                "account_count": q.count(),
            })
        except Exception:
            pass
    return result


@router.get("/{name}")
def get_scenario(name: str):
    filepath = SCENARIOS_DIR / f"{name}.json"
    if not filepath.exists():
        raise HTTPException(404, f"Scenario '{name}' not found")
    return json.loads(filepath.read_text())


@router.put("/{name}")
def edit_scenario(name: str, req: EditScenarioRequest):
    filepath = SCENARIOS_DIR / f"{name}.json"
    if not filepath.exists():
        raise HTTPException(404, f"Scenario '{name}' not found")

    new_name = req.name.strip()
    if not new_name:
        raise HTTPException(400, "Name is required")

    data = json.loads(filepath.read_text())
    data["name"] = new_name
    data["version"] = req.version

    if new_name != name:
        new_filepath = SCENARIOS_DIR / f"{new_name}.json"
        if new_filepath.exists():
            raise HTTPException(400, f"Scenario '{new_name}' already exists")
        filepath.unlink()
        filepath = new_filepath

    filepath.write_text(json.dumps(data, indent=2))
    return {"name": new_name, "version": req.version}


@router.delete("/{name}", dependencies=[Depends(require_admin)])
def delete_scenario(name: str):
    filepath = SCENARIOS_DIR / f"{name}.json"
    if not filepath.exists():
        raise HTTPException(404, f"Scenario '{name}' not found")
    filepath.unlink()
    return {"status": "deleted", "name": name}
