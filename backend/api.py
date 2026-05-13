"""
Orcanos Performance Testing Tool — FastAPI Backend
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import traceback
import os
from dotenv import load_dotenv

load_dotenv()

from backend.services.database import init_db
from backend.routes.scenarios import router as scenarios_router
from backend.routes.auth import router as auth_router
from backend.routes.accounts import router as accounts_router
from backend.routes.runs import router as runs_router
from backend.routes.results import router as results_router
from backend.routes.config import router as config_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="Orcanos Performance Testing Tool",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    tb = traceback.format_exc()
    print(f"[ERROR] {request.method} {request.url.path}\n{tb}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


# Routes
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(accounts_router, prefix="/api/accounts", tags=["Accounts"])
app.include_router(scenarios_router, prefix="/api/scenarios", tags=["Scenarios"])
app.include_router(runs_router, prefix="/api/runs", tags=["Runs"])
app.include_router(results_router, prefix="/api/results", tags=["Results"])
app.include_router(config_router, prefix="/api/config", tags=["Config"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "backend_version": "0.1.0"}


@app.get("/healthz")
async def health_check_alt():
    return {"status": "ok"}


# Serve React frontend in production (when dist/ exists)
from pathlib import Path as _Path
from fastapi.staticfiles import StaticFiles as _StaticFiles

_dist = _Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    app.mount("/", _StaticFiles(directory=_dist, html=True), name="frontend")
