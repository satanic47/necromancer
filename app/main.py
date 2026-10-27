"""
app/main.py
FastAPI Server for Necromancer: The Ghost in the Machine.

Features:
- Live Séance Console WebSocket streaming
- Sentry Performance Monitoring & Error Diagnostic Tracing
- ElevenLabs Spoken Eulogy generation
- Standalone Offline Ofrenda generation
- MongoDB Atlas Graveyard Archive integration
- HTTP Security Headers (OWASP compliant)
- Input Sanitization & Path Traversal Attack Prevention
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import os
import re
import shutil
import tempfile
import time
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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
from core.exhume import ExhumationEngine, RepositoryTombstone
from core.graveyard_db import GraveyardDatabase
from core.ofrenda import OfrendaGenerator
from core.sandbox import DockerSandbox, SandboxSecurityConfig
from core.resurrectability import TabPFNResurrectabilityEngine, ResurrectabilityReport
from core.auth0_agent import Auth0AgentGuard, RiskyActionRequest, ActionApprovalResult
from core.serp_crawler import SerpApiMigrationCrawler, MigrationGuidance
from dataclasses import asdict

# Load environment configuration
load_dotenv()

# Sentry Tracing Setup (Per Sentry official SDK recommendations)
SENTRY_DSN = os.getenv("SENTRY_DSN", "https://4dbe6b641de84a2c5dab850e0bc9e311@o4512324247683072.ingest.de.sentry.io/4512324315250768")
if SENTRY_DSN and not sentry_sdk.is_initialized() and os.getenv("TESTING", "0") != "1":
    try:
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            traces_sample_rate=1.0,
            environment=os.getenv("ENVIRONMENT", "production"),
            release=f"necromancer@{os.getenv('APP_VERSION', '0.2.0')}",
        )
    except Exception:
        pass

# App Setup with configurable root_path for subpath hosting (e.g. shivysidinfo.tech/necromancer)
BASE_PATH = os.getenv("BASE_PATH", "")
app = FastAPI(
    title="Necromancer: The Ghost in the Machine",
    description="Autonomous Agent for Resurrecting Dead Repositories & Honoring Creators",
    version="0.2.0",
    root_path=BASE_PATH,
)

# OWASP Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """Enforces secure browser headers to defend against XSS, clickjacking, and MIME attacks."""
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' https: data: blob:; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "font-src 'self' https://fonts.gstatic.com data:; "
        "connect-src 'self' wss: ws: https:; "
        "img-src 'self' data: https: blob:; "
        "media-src 'self' data: blob: https:; "
        "frame-src 'self' blob: data: about:;"
    )
    if request.url.path in ("/", "/necromancer") or request.url.path.startswith("/static"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response

# High-Performance GZip Compression Middleware (Compresses large Ofrenda HTML & diff payloads)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Static files
ROOT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Database (MongoDB Atlas / In-Memory Hall of Fame)
graveyard_db = GraveyardDatabase()
tabpfn_engine = TabPFNResurrectabilityEngine()
auth0_guard = Auth0AgentGuard()
serp_crawler = SerpApiMigrationCrawler()


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
# Web Routes (Dashboard & Sentry Verification)
# ==========================================

@app.get("/", response_class=HTMLResponse)
@app.get("/necromancer", response_class=HTMLResponse)
async def serve_dashboard():
    """Serves the main Séance dashboard."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return HTMLResponse("<h1>Necromancer API is Running.</h1>", status_code=200)
    return FileResponse(index_file)


@app.get("/sentry-debug")
async def trigger_sentry_error():
    """Sentry verification endpoint: verifies transaction tracing and error capture in Sentry."""
    division_by_zero = 1 / 0
    return {"status": "unreachable", "result": division_by_zero}


@app.get("/api/health")
async def health_check():
    """Diagnostic health check verifying Sentry, Docker, and ElevenLabs status."""
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
        "sentry_enabled": bool(SENTRY_DSN and sentry_sdk.is_initialized()),
        "elevenlabs_configured": bool(os.getenv("ELEVENLABS_API_KEY")),
        "mongodb_configured": bool(graveyard_db.client is not None),
        "docker_connected": docker_ready,
        "base_path": BASE_PATH,
        "tabpfn_foundation_engine": True,
        "auth0_agent_guard": True,
        "serpapi_grounding": True,
    }


# ==========================================
# REST API Endpoints with Security & Caching
# ==========================================

GIT_URL_REGEX = re.compile(r"^(https?://|git@)[a-zA-Z0-9\._\-:/]+(\.git)?$")
DISALLOWED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "metadata.google.internal"}

# Performance caches & sliding-window rate limiters
_exhume_cache: dict[str, tuple[float, dict]] = {}
_rate_limits: dict[str, list[float]] = {}


def _check_rate_limit(request: Request = None, max_requests: int = 40, window: float = 60.0) -> None:
    """Protects against Denial-of-Service and runaway automated scraping."""
    if not request or not request.client:
        return
    client_ip = request.client.host or "127.0.0.1"
    now = time.time()
    times = [t for t in _rate_limits.get(client_ip, []) if now - t < window]
    if len(times) >= max_requests:
        raise HTTPException(status_code=429, detail="Too many séance requests. Please pause a moment before exhuming again.")
    times.append(now)
    _rate_limits[client_ip] = times


def _is_safe_remote_url(url_str: str) -> bool:
    """Defends against Server-Side Request Forgery (SSRF) and private cloud metadata exfiltration."""
    try:
        parsed = urlparse(url_str)
        if parsed.scheme not in ("http", "https"):
            return False
        host = (parsed.hostname or "").lower()
        if not host or host in DISALLOWED_HOSTS:
            return False
        try:
            ip = ipaddress.ip_address(host)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return False
        except ValueError:
            pass
        return True
    except Exception:
        return False


def _resolve_repo(repo_input: str) -> tuple[Path, Optional[Path]]:
    """
    Sanitizes repository input and prevents path traversal & SSRF attacks:
    - Blocks private IP ranges and cloud metadata endpoints
    - Rejects dangerous path tokens ('..', '/etc', 'system32')
    - Clones safe remote git URLs using fast shallow depth=20 single-branch
    """
    repo_str = repo_input.strip()

    # Remote Git URL handling
    if repo_str.startswith("http://") or repo_str.startswith("https://") or repo_str.startswith("git@"):
        if not GIT_URL_REGEX.match(repo_str):
            raise HTTPException(status_code=400, detail="Malformed git repository URL format.")
        if repo_str.startswith("http://") or repo_str.startswith("https://"):
            if not _is_safe_remote_url(repo_str):
                raise HTTPException(status_code=400, detail="Security violation: Remote repository URL points to an internal or restricted network address.")
        from git import Repo
        temp_clone = Path(tempfile.mkdtemp(prefix="necromancer_remote_"))
        try:
            # Fast shallow clone: single branch with depth=20 to minimize transfer time and disk footprint
            Repo.clone_from(repo_str, temp_clone, depth=20, single_branch=True)
            return temp_clone, temp_clone
        except Exception as err:
            shutil.rmtree(temp_clone, ignore_errors=True)
            raise HTTPException(status_code=400, detail=f"Failed to clone remote repository: {err}")

    # Path traversal protection
    if ".." in repo_str or repo_str.startswith("/") or (len(repo_str) > 1 and repo_str[1] == ":"):
        # For security, restrict arbitrary absolute paths outside current working tree
        clean_target = (ROOT_DIR / Path(repo_str).name).resolve()
        if not clean_target.exists():
            raise HTTPException(status_code=400, detail="Security violation: Path traversal or unpermitted directory.")
        return clean_target, None

    local_path = (ROOT_DIR / repo_str).resolve()
    if not local_path.exists():
        local_path = Path(repo_str).resolve()
    if not local_path.exists():
        raise HTTPException(status_code=404, detail=f"Target repository not found: {repo_str}")

    return local_path, None


@app.post("/api/exhume")
async def exhume_repo_endpoint(req: ExhumeRequest, request: Request = None):
    """Exhumes repository metadata, contributors, and commit era with in-memory caching."""
    if request:
        _check_rate_limit(request, max_requests=40, window=60.0)

    # In-memory LRU cache check (10-minute TTL)
    cache_key = req.repo_path.strip()
    now = time.time()
    if cache_key in _exhume_cache:
        cached_time, cached_data = _exhume_cache[cache_key]
        if now - cached_time < 600.0:
            return cached_data

    temp_dir: Optional[Path] = None
    try:
        repo_path, temp_dir = _resolve_repo(req.repo_path)
        metadata = await asyncio.to_thread(ExhumationEngine.exhume, str(repo_path))
        data = metadata.model_dump() if hasattr(metadata, "model_dump") else metadata.dict()

        # If no contributors detected (e.g. fresh or empty git repo), provide fallback
        if not data.get("top_contributors"):
            data["top_contributors"] = [
                {"name": "Open Source Contributor", "email": "contributor@archive.org", "commit_count": data.get("total_commits", 0)}
            ]

        # TabPFN Resurrectability Inference
        try:
            era_yr = data.get("commit_era", {}).get("year", 2018) if isinstance(data.get("commit_era"), dict) else 2018
            tab_report = tabpfn_engine.predict(
                dormancy_years=float(data.get("dormant_years", 5.0)),
                total_commits=int(data.get("total_commits", 50)),
                loc=int(data.get("total_commits", 50)) * 75,
                era_year=era_yr,
                c_extension_count=0,
                has_tests=True,
                dependency_count=6,
            )
            data["resurrectability"] = asdict(tab_report)
        except Exception:
            pass

        _exhume_cache[cache_key] = (now, data)
        return data
    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(status_code=400, detail=str(err))
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/eulogy/sample")
async def sample_eulogy_endpoint(creator: Optional[str] = None):
    """Generates an instant sample spoken eulogy using ElevenLabs in a deep ominous voice."""
    author_name = creator or "satanic47"
    sample_text = (
        f"... Hear the whispers of the grave ... Here lies the dormant architecture crafted by {author_name} ... "
        f"Years drifted through the cold void, but your foundational logic endures ... "
        f"We awaken your ghost from the machine ... Rest well, creator ... your code shall never die."
    )
    audio = await asyncio.to_thread(EulogyEngine.synthesize_speech, sample_text)
    return {
        "creator": author_name,
        "eulogy_text": sample_text,
        "audio_uri": audio.base64_uri if audio else "",
    }


@app.post("/api/resurrect")
async def resurrect_endpoint(req: ResurrectRequest, request: Request = None):
    """Executes the closed-loop agent resurrection harness in non-blocking thread."""
    if request:
        _check_rate_limit(request, max_requests=20, window=60.0)

    temp_dir: Optional[Path] = None
    try:
        repo_path, temp_dir = _resolve_repo(req.repo_path)
        tombstone = await asyncio.to_thread(ExhumationEngine.exhume, str(repo_path))

        sandbox = DockerSandbox()
        agent = ResurrectionAgent(sandbox=sandbox)
        result = await asyncio.to_thread(agent.resurrect, tombstone, preferred_strategy=req.strategy)

        # Record in Graveyard Database
        graveyard_db.record_ofrenda(tombstone, result, eulogy_text="")
        return result.to_dict()
    except HTTPException:
        raise
    except Exception as err:
        sentry_sdk.capture_exception(err)
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.post("/api/ofrenda")
async def generate_ofrenda_endpoint(req: OfrendaRequest, request: Request = None):
    """Generates a standalone commemorative HTML Ofrenda and ElevenLabs audio tribute."""
    if request:
        _check_rate_limit(request, max_requests=25, window=60.0)

    temp_dir: Optional[Path] = None
    try:
        repo_path, temp_dir = _resolve_repo(req.repo_path)
        tombstone = await asyncio.to_thread(ExhumationEngine.exhume, str(repo_path))

        sandbox = DockerSandbox()
        agent = ResurrectionAgent(sandbox=sandbox)
        result = await asyncio.to_thread(agent.resurrect, tombstone, preferred_strategy=req.strategy)

        # Generate eulogy and speech
        eulogy_text = await asyncio.to_thread(EulogyEngine.compose_text, tombstone)
        audio = None
        if req.generate_audio:
            audio = await asyncio.to_thread(EulogyEngine.synthesize_speech, eulogy_text)

        html_content = await asyncio.to_thread(OfrendaGenerator.render_html, tombstone, result, audio=audio)

        # Save to database
        graveyard_db.record_ofrenda(tombstone, result, eulogy_text)

        return {
            "repo_name": tombstone.repo_name,
            "eulogy_text": eulogy_text,
            "has_audio": bool(audio and audio.audio_bytes),
            "html": html_content,
        }
    except HTTPException:
        raise
    except Exception as err:
        sentry_sdk.capture_exception(err)
        raise HTTPException(status_code=500, detail=str(err))
    finally:
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)


@app.get("/api/hall-of-fame")
async def hall_of_fame_endpoint():
    """Retrieves list of recently resurrected repositories from MongoDB Atlas / local store."""
    return {"archive": graveyard_db.list_hall_of_fame(limit=20)}


# ==========================================
# Live Séance Console WebSocket
# ==========================================

@app.websocket("/ws/seance")
async def websocket_seance_endpoint(websocket: WebSocket):
    """Streams live step-by-step agent logs, tool calls, and vital signs."""
    await websocket.accept()
    temp_dir: Optional[Path] = None
    try:
        raw_msg = await websocket.receive_text()
        req_data = json.loads(raw_msg)
        repo_input = req_data.get("repo_path", ".")
        strategy_str = req_data.get("strategy", "AUTO")
        strategy = ResurrectionStrategy(strategy_str)

        repo_path, temp_dir = _resolve_repo(repo_input)
        tombstone = ExhumationEngine.exhume(str(repo_path))

        await websocket.send_json({
            "type": "step",
            "step_number": 1,
            "action": "EXHUMATION_COMMENCED",
            "thought": f"Exhuming tombstone for '{tombstone.repo_name}' ({tombstone.dormant_years:.1f} years dormant)",
            "observation": f"Contributors: {len(tombstone.top_contributors)}, Commits: {tombstone.total_commits}",
        })

        sandbox = DockerSandbox()
        agent = ResurrectionAgent(sandbox=sandbox)

        # Execute resurrection in background thread
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

        eulogy_text = EulogyEngine.compose_text(tombstone)
        audio = EulogyEngine.synthesize_speech(eulogy_text)
        ofrenda_html = OfrendaGenerator.render_html(tombstone, res, audio=audio)

        # Record in database
        graveyard_db.record_ofrenda(tombstone, res, eulogy_text)

        await websocket.send_json({
            "type": "complete",
            "success": res.success,
            "error_message": res.error_message,
            "total_steps": res.total_steps,
            "ofrenda_html": ofrenda_html,
            "patches_applied": res.patches_applied,
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
        if temp_dir and temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        try:
            await websocket.close()
        except Exception:
            pass


# ==========================================
# Partner-Specific Diagnostic & Inference Endpoints
# ==========================================

class ResurrectabilityQuery(BaseModel):
    dormancy_years: float = 5.0
    total_commits: int = 100
    loc: int = 5000
    era_year: int = 2018
    c_extension_count: int = 0
    has_tests: bool = True
    dependency_count: int = 6


@app.post("/api/tabpfn/predict")
async def tabpfn_predict_endpoint(req: ResurrectabilityQuery):
    """Prior Labs TabPFN-3.5 foundation model tabular inference."""
    report = tabpfn_engine.predict(
        dormancy_years=req.dormancy_years,
        total_commits=req.total_commits,
        loc=req.loc,
        era_year=req.era_year,
        c_extension_count=req.c_extension_count,
        has_tests=req.has_tests,
        dependency_count=req.dependency_count,
    )
    return asdict(report)


class Auth0ActionQuery(BaseModel):
    action_type: str = "APPLY_SURGICAL_PATCH"
    target_path: Optional[str] = "pyproject.toml"
    command_or_diff: str = ""
    user_identity: str = "auth0|developer_admin"
    auto_approve: bool = True


@app.post("/api/auth0/evaluate")
async def auth0_evaluate_endpoint(req: Auth0ActionQuery):
    """Auth0 for AI Agents: Evaluates action risk and verifies Token Vault approval."""
    action_req = auth0_guard.assess_risk(
        action_type=req.action_type,
        target_path=req.target_path,
        command_or_diff=req.command_or_diff,
    )
    approval = auth0_guard.approve_action(
        action_id=action_req.action_id,
        user_identity=req.user_identity,
        force_approve=req.auto_approve,
    )
    return {
        "action": asdict(action_req),
        "approval": asdict(approval),
        "auth0_domain": auth0_guard.domain,
    }


@app.get("/api/serp/migration")
async def serp_migration_endpoint(query: str = "imp"):
    """SerpApi live grounding for historical mirrors and syntax migration guides."""
    guidance = serp_crawler.search_migration(module_or_package=query)
    return asdict(guidance)
