"""
Test run routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from backend.models import TestRun, Account
from backend.services.database import get_db

router = APIRouter()


class StartRunRequest(BaseModel):
    scenario_name: str


class TestRunResponse(BaseModel):
    id: int
    scenario_id: int
    status: str
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


@router.post("/", response_model=TestRunResponse)
def start_run(request: StartRunRequest, db: Session = Depends(get_db)):
    from backend.services.runner import runner
    from pathlib import Path

    if not request.scenario_name.strip():
        raise HTTPException(400, "Scenario name is required")

    scenario_path = Path(__file__).parent.parent / "scenarios" / f"{request.scenario_name}.json"
    if not scenario_path.exists():
        raise HTTPException(404, f"Scenario '{request.scenario_name}' not found")

    if runner.active:
        raise HTTPException(409, "A test run is already in progress. Wait for it to finish.")

    accounts = db.query(Account).filter(Account.enabled == True).all()
    if not accounts:
        raise HTTPException(400, "No enabled accounts found. Add and enable accounts first.")

    run = TestRun(scenario_id=0, scenario_name=request.scenario_name, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    accounts_data = [
        {"id": a.id, "name": a.name, "encrypted_password": a.encrypted_password}
        for a in accounts
    ]

    try:
        runner.start(run.id, request.scenario_name, accounts_data)
    except Exception as e:
        run.status = "failed"
        db.commit()
        raise HTTPException(500, f"Failed to start runner: {e}")

    return run


@router.get("/{run_id}/progress")
def get_run_progress(run_id: int):
    from backend.services.runner import runner
    progress = runner.get_progress(run_id)
    if not progress:
        return {"status": "unknown", "run_id": run_id}
    return progress


@router.get("/", response_model=List[TestRunResponse])
def list_runs(db: Session = Depends(get_db)):
    return db.query(TestRun).order_by(TestRun.started_at.desc()).all()


@router.get("/{run_id}", response_model=TestRunResponse)
def get_run(run_id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(404, f"Run #{run_id} not found")
    return run
