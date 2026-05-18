"""
Config routes — read and update config.json thresholds
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from pathlib import Path
import json
from backend.services.auth import get_current_user, require_admin

router = APIRouter(dependencies=[Depends(get_current_user)])

CONFIG_PATH = Path(__file__).parent.parent.parent / "config.json"

DEFAULTS = {
    "step_timeout_seconds": 45,
    "run_timeout_seconds": 300,
    "pass_threshold_seconds": 3,
    "warn_threshold_seconds": 8,
}


def _read() -> dict:
    if CONFIG_PATH.exists():
        return {**DEFAULTS, **json.loads(CONFIG_PATH.read_text())}
    return dict(DEFAULTS)


class ConfigModel(BaseModel):
    step_timeout_seconds: int
    run_timeout_seconds: int
    pass_threshold_seconds: float
    warn_threshold_seconds: float


@router.get("/")
def get_config():
    return _read()


@router.put("/", dependencies=[Depends(require_admin)])
def update_config(body: ConfigModel):
    if body.pass_threshold_seconds >= body.warn_threshold_seconds:
        raise HTTPException(400, "Pass threshold must be less than warn threshold")
    if body.warn_threshold_seconds >= body.step_timeout_seconds:
        raise HTTPException(400, "Warn threshold must be less than step timeout")
    if body.run_timeout_seconds < body.step_timeout_seconds:
        raise HTTPException(400, "Run timeout must be at least as large as step timeout")
    CONFIG_PATH.write_text(json.dumps(body.model_dump(), indent=2))
    return body
