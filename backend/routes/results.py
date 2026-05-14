"""
Test results routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from backend.models import StepResult, TestRun, Account
from backend.services.database import get_db
from backend.services.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/run/{run_id}")
def get_run_results(run_id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")

    step_results = db.query(StepResult).filter(StepResult.run_id == run_id).all()

    # Group by account
    accounts_map = {}
    for sr in step_results:
        acct = db.query(Account).filter(Account.id == sr.account_id).first()
        acct_name = acct.name if acct else f"account_{sr.account_id}"
        acct_url = acct.url if acct else ""
        if acct_name not in accounts_map:
            accounts_map[acct_name] = {"url": acct_url, "steps": []}
        accounts_map[acct_name]["steps"].append({
            "step_name": sr.step_name,
            "duration_seconds": sr.duration_seconds,
            "status": sr.status,
            "error_message": sr.error_message,
        })

    return {
        "run_id": run.id,
        "scenario_name": run.scenario_name,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
        "status": run.status,
        "accounts": [
            {"name": name, "url": data["url"], "steps": data["steps"]}
            for name, data in accounts_map.items()
        ],
    }


@router.get("/runs")
def list_runs_summary(db: Session = Depends(get_db)):
    runs = db.query(TestRun).order_by(TestRun.started_at.desc()).limit(50).all()
    return [
        {
            "id": r.id,
            "scenario_name": r.scenario_name,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        }
        for r in runs
    ]
