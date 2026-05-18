"""
Test results routes
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from backend.models import StepResult, TestRun, Account, SummaryCache
from backend.services.database import get_db, SessionLocal
from backend.services.auth import get_current_user
import logging

logger = logging.getLogger("results")

router = APIRouter(dependencies=[Depends(get_current_user)])


@router.get("/run/{run_id}")
def get_run_results(run_id: int, db: Session = Depends(get_db)):
    run = db.query(TestRun).filter(TestRun.id == run_id).first()
    if not run:
        raise HTTPException(404, "Run not found")

    step_results = db.query(StepResult).filter(StepResult.run_id == run_id).all()

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


@router.get("/summary")
def get_summary(db: Session = Depends(get_db)):
    cache = db.query(SummaryCache).filter(SummaryCache.id == 1).first()
    if cache and cache.data:
        return cache.data
    data = _compute_summary(db)
    _save_summary_cache(db, data)
    return data


# ── Internal helpers ──────────────────────────────────────────────────────────

def _compute_summary(db: Session) -> dict:
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

    # Per-run totals + distinct account sets for normalization
    run_totals: dict = {
        r.id: {"run_id": r.id, "scenario_name": r.scenario_name, "started_at": r.started_at, "total": 0.0, "acct_ids": set()}
        for r in runs
    }
    account_times: dict = {}
    account_step_counts: dict = {}
    step_times: dict = {}
    step_counts: dict = {}

    for sr in step_results:
        dur = sr.duration_seconds or 0.0
        if sr.run_id in run_totals:
            run_totals[sr.run_id]["total"] += dur
            run_totals[sr.run_id]["acct_ids"].add(sr.account_id)
        if sr.status not in ("failed", "timeout") and dur > 0:
            name = accounts_map.get(sr.account_id, f"account_{sr.account_id}")
            account_times[name] = account_times.get(name, 0.0) + dur
            account_step_counts[name] = account_step_counts.get(name, 0) + 1
            step_times[sr.step_name] = step_times.get(sr.step_name, 0.0) + dur
            step_counts[sr.step_name] = step_counts.get(sr.step_name, 0) + 1

    # Trend: avg per account so runs with different account counts are comparable
    trend = []
    for v in run_totals.values():
        n = max(len(v["acct_ids"]), 1)
        trend.append({
            "run_id": v["run_id"],
            "scenario_name": v["scenario_name"],
            "started_at": v["started_at"].isoformat() if v["started_at"] else None,
            "avg_per_account_seconds": round(v["total"] / n, 1),
            "account_count": n,
        })

    per_run_avgs = [round(v["total"] / max(len(v["acct_ids"]), 1), 1) for v in run_totals.values() if v["total"] > 0]
    avg_scenario_seconds = round(sum(per_run_avgs) / len(per_run_avgs), 1) if per_run_avgs else None

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


def _save_summary_cache(db: Session, data: dict):
    cache = db.query(SummaryCache).filter(SummaryCache.id == 1).first()
    if cache:
        cache.data = data
        cache.computed_at = datetime.utcnow()
    else:
        db.add(SummaryCache(id=1, data=data, computed_at=datetime.utcnow()))
    db.commit()


def refresh_summary_cache():
    """Recompute and persist summary cache. Called by runner after each run."""
    db = SessionLocal()
    try:
        data = _compute_summary(db)
        _save_summary_cache(db, data)
        logger.info("[SUMMARY] Cache refreshed")
    except Exception as e:
        logger.warning(f"[SUMMARY] Cache refresh failed: {e}")
    finally:
        db.close()
