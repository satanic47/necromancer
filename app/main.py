"""
app/main.py
FastAPI Server for Necromancer: The Ghost in the Machine.

Features:
- Live Séance Console WebSocket streaming
- Sentry Performance Monitoring & Error Diagnostic Tracing
- ElevenLabs Spoken Eulogy generation
- Standalone Offline Ofrenda generation
- Flexible reverse-proxy support (serves at / or /necromancer)
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import tempfile
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import sentry_sdk

from core.agent import (
    LLMClient,
    ResurrectionAgent,
    ResurrectionResult,
    ResurrectionStrategy,
)
from core.eulogy import EulogyEngine
from core.exhume import ExhumationEngine, ExhumationEngine as ExhumeService, RepositoryTombstone
from core.ofrenda import OfrendaGenerator
from core.sandbox import DockerSandbox, SandboxSecurityConfig

# Load environment configuration
load_dotenv()

# Sentry Tracing Setup
def init_sentry():
    dsn = os.getenv("SENTRY_DSN", "")
    if dsn and not sentry_sdk.is_initialized() and os.getenv("TESTING", "0") != "1":
        try:
            from sentry_sdk.integrations.fastapi import FastApiIntegration
            sentry_sdk.init(
                dsn=dsn,
                integrations=[FastApiIntegration()],
                traces_sample_rate=1.0,
                environment=os.getenv("ENVIRONMENT", "production"),
                release=f"necromancer@{os.getenv('APP_VERSION', '0.2.0')}",
            )
        except Exception:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    if os.getenv("TESTING", "0") != "1":
        init_sentry()
    yield

# App Setup with configurable root_path for subpath hosting (e.g. shivysidinfo.tech/necromancer)
BASE_PATH = os.getenv("BASE_PATH", "")
app = FastAPI(
    title="Necromancer: The Ghost in the Machine",
    description="Autonomous Agent for Resurrecting Dead Repositories & Honoring Creators",
    version="0.2.0",
    root_path=BASE_PATH,
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# Pydantic Schemas
class ExhumeRequest(BaseModel):
    repo_path: str


class ResurrectRequest(BaseModel):
    repo_path: str
    strategy: ResurrectionStrategy = ResurrectionStrategy.AUTO


class OfrendaRequest(BaseModel):
    repo_path: str
    strategy: ResurrectionStrategy = ResurrectionStrategy.AUTO
    generate_audio: bool = True


# ==========================================
# Web Routes (Dashboard)
# ==========================================

@app.get("/", response_class=HTMLResponse)
@app.get("/necromancer", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the main Séance dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Necromancer API is Running.</h1>", status_code=200)
    return FileResponse(index_file)


@app.get("/api/health")
async def health_check():
    """Diagnostic health check verifying Sentry, Docker, and ElevenLabs status."""
    print("ENTER HEALTH CHECK")
    docker_ready = False
    if os.getenv("CHECK_DOCKER_HEALTH", "false").lower() == "true":
        try:
            import docker
            client = docker.from_env(timeout=1)
            client.ping()
            docker_ready = True
        except Exception:
            docker_ready = False

    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "sentry_enabled": bool(os.getenv("SENTRY_DSN") and sentry_sdk.is_initialized()),
        "elevenlabs_configured": bool(os.getenv("ELEVENLABS_API_KEY")),
        "docker_connected": docker_ready,
        "base_path": BASE_PATH,
    }


# ==========================================
# REST API Endpoints
# ==========================================

def _resolve_repo(repo_input: str) -> tuple[Path, Optional[Path]]:
    """Resolves local directory or clones remote git repository into a temporary folder."""
    repo_str = repo_input.strip()
    if repo_str.startswith("http://") or repo_str.startswith("https://") or repo_str.startswith("git@"):
        from git import Repo
        temp_clone = Path(tempfile.mkdtemp(prefix="necromancer_remote_"))
        Repo.clone_from(repo_str, temp_clone, depth=50)
        return temp_clone, temp_clone

    local_path = Path(repo_str).resolve()
    if not local_path.exists():
        # Fallback: check relative to root directory
        local_path = (ROOT_DIR / repo_str).resolve()
    if not local_path.exists():
        raise HTTPException(status_code=404, detail=f"Target repository not found: {repo_str}")
    return local_path, None


@app.post("/api/exhume")
async def exhume_repo_endpoint(req: ExhumeRequest):
    """Exhumes repository metadata, contributors, and commit era."""
    try:
        repo_path, temp_clone = _resolve_repo(req.repo_path)
        metadata = ExhumationEngine.exhume(str(repo_path))
        data = metadata.model_dump() if hasattr(metadata, "model_dump") else metadata.dict()
        return data
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))


@app.post("/api/resurrect")
async def resurrect_endpoint(req: ResurrectRequest):
    """Executes the closed-loop agent resurrection harness."""
    try:
        repo_path, temp_clone = _resolve_repo(req.repo_path)
        tombstone = ExhumationEngine.exhume(str(repo_path))

        sandbox = DockerSandbox()
        agent = ResurrectionAgent(sandbox=sandbox)
        result = agent.resurrect(tombstone, preferred_strategy=req.strategy)
        return result.to_dict()
    except Exception as err:
        sentry_sdk.capture_exception(err)
        raise HTTPException(status_code=500, detail=str(err))


@app.post("/api/ofrenda")
async def generate_ofrenda_endpoint(req: OfrendaRequest):
    """Generates a standalone commemorative HTML Ofrenda and ElevenLabs audio tribute."""
    try:
        repo_path, temp_clone = _resolve_repo(req.repo_path)
        tombstone = ExhumationEngine.exhume(str(repo_path))

        sandbox = DockerSandbox()
        agent = ResurrectionAgent(sandbox=sandbox)
        result = agent.resurrect(tombstone, preferred_strategy=req.strategy)

        # Generate eulogy and speech
        eulogy_text = EulogyEngine.compose_text(tombstone)
        audio = None
        if req.generate_audio:
            audio = EulogyEngine.synthesize_speech(eulogy_text)

        html_content = OfrendaGenerator.render_html(tombstone, result, audio=audio)

        return {
            "repo_name": tombstone.repo_name,
            "eulogy_text": eulogy_text,
            "has_audio": bool(audio and audio.audio_bytes),
            "html": html_content,
        }
    except Exception as err:
        sentry_sdk.capture_exception(err)
        raise HTTPException(status_code=500, detail=str(err))


# ==========================================
# Live Séance Console WebSocket
# ==========================================

@app.websocket("/ws/seance")
async def websocket_seance_endpoint(websocket: WebSocket):
    """Streams live step-by-step agent logs, tool calls, and vital signs."""
    await websocket.accept()
    try:
        raw_msg = await websocket.receive_text()
        req_data = json.loads(raw_msg)
        repo_input = req_data.get("repo_path", ".")
        strategy_str = req_data.get("strategy", "AUTO")
        strategy = ResurrectionStrategy(strategy_str)

        repo_path, temp_clone = _resolve_repo(repo_input)
        tombstone = ExhumationEngine.exhume(str(repo_path))

        # Send initial step
        await websocket.send_json({
            "type": "step",
            "step_number": 1,
            "action": "EXHUMATION_COMMENCED",
            "thought": f"Exhuming tombstone for '{tombstone.repo_name}' ({tombstone.dormant_years:.1f} years dormant)",
            "observation": f"Contributors: {len(tombstone.top_contributors)}, Commits: {tombstone.total_commits}",
        })

        # Run agent in background executor to prevent blocking event loop
        sandbox = DockerSandbox()
        agent = ResurrectionAgent(sandbox=sandbox)

        # Execute resurrection
        loop = asyncio.get_event_loop()
        res: ResurrectionResult = await loop.run_in_executor(
            None, agent.resurrect, tombstone, strategy
        )

        for step in res.steps:
            await websocket.send_json({
                "type": "step",
                "step_number": step.step_number,
                "action": step.action,
                "thought": step.thought,
                "tool_call": step.tool_call,
                "observation": step.observation,
                "duration_seconds": step.duration_seconds,
            })

        # Generate memorial Ofrenda
        eulogy_text = EulogyEngine.compose_text(tombstone)
        audio = EulogyEngine.synthesize_speech(eulogy_text)
        ofrenda_html = OfrendaGenerator.render_html(tombstone, res, audio=audio)

        await websocket.send_json({
            "type": "complete",
            "success": res.success,
            "error_message": res.error_message,
            "total_steps": res.total_steps,
            "ofrenda_html": ofrenda_html,
        })

    except WebSocketDisconnect:
        pass
    except Exception as err:
        sentry_sdk.capture_exception(err)
        try:
            await websocket.send_json({
                "type": "complete",
                "success": False,
                "error_message": str(err),
            })
        except Exception:
            pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
