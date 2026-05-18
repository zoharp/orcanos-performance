"""
Test results routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
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


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    runs = db.query(TestRun).filter(
        TestRun.status.in_(["completed", "stopped"])
    ).order_by(TestRun.started_at.asc()).limit(30).all()

    if not runs:
        return {"trend": [], "slowest_account": None, "avg_scenario_seconds": None, "slowest_step": None}

    run_ids = [r.id for r in runs]
    step_results = db.query(StepResult).filter(StepResult.run_id.in_(run_ids)).all()

    account_ids = {sr.account_id for sr in step_results}
    accounts_map = {}
    if account_ids:
        accounts_map = {a.id: a.name for a in db.query(Account).filter(Account.id.in_(account_ids)).all()}

    run_totals = {r.id: {"run_id": r.id, "scenario_name": r.scenario_name, "started_at": r.started_at, "total": 0.0} for r in runs}
    account_times: dict = {}
    account_step_counts: dict = {}
    step_times: dict = {}
    step_counts: dict = {}

    for sr in step_results:
        dur = sr.duration_seconds or 0.0
        if sr.run_id in run_totals:
            run_totals[sr.run_id]["total"] += dur
        if sr.status not in ("failed", "timeout") and dur > 0:
            name = accounts_map.get(sr.account_id, f"account_{sr.account_id}")
            account_times[name] = account_times.get(name, 0.0) + dur
            account_step_counts[name] = account_step_counts.get(name, 0) + 1
            step_times[sr.step_name] = step_times.get(sr.step_name, 0.0) + dur
            step_counts[sr.step_name] = step_counts.get(sr.step_name, 0) + 1

    trend = [
        {
            "run_id": v["run_id"],
            "scenario_name": v["scenario_name"],
            "started_at": v["started_at"].isoformat() if v["started_at"] else None,
            "total_seconds": round(v["total"], 1),
        }
        for v in run_totals.values()
    ]

    run_total_values = [v["total"] for v in run_totals.values() if v["total"] > 0]
    avg_scenario_seconds = round(sum(run_total_values) / len(run_total_values), 1) if run_total_values else None

    slowest_account = None
    if account_times:
        avg_by_acct = {k: account_times[k] / account_step_counts[k] for k in account_times}
        top = max(avg_by_acct, key=avg_by_acct.__getitem__)
        slowest_account = {"name": top, "avg_seconds": round(avg_by_acct[top], 1)}

    slowest_step = None
    if step_times:
        avg_by_step = {k: step_times[k] / step_counts[k] for k in step_times}
        top = max(avg_by_step, key=avg_by_step.__getitem__)
        slowest_step = {"name": top, "avg_seconds": round(avg_by_step[top], 1)}

    return {
        "trend": trend,
        "slowest_account": slowest_account,
        "avg_scenario_seconds": avg_scenario_seconds,
        "slowest_step": slowest_step,
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
