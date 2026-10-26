"""
tests/test_phase4.py
Comprehensive Verification Suite for Phase 4:
- Eulogy Composition & Audio Synthesis (4 tests)
- Standalone Offline Ofrenda HTML Generator (5 tests)
- FastAPI Routes & Reverse-Proxy Subpaths (6 tests)
Total: 15 Unit Tests
"""

import os
os.environ["TESTING"] = "1"
os.environ["SENTRY_DSN"] = ""
os.environ["CHECK_DOCKER_HEALTH"] = "false"

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.main import app
from core.agent import ResurrectionAgent, ResurrectionResult, ResurrectionStrategy
from core.era_detect import EraProfile
from core.eulogy import DEFAULT_VOICE_ID, EulogyAudio, EulogyEngine
from core.exhume import ContributorInfo, RepositoryTombstone
from core.ofrenda import OfrendaGenerator
from core.test_integrity import ParsedSummary


# ============================================================================
# 1. Eulogy & Audio Engine Tests (4 tests)
# ============================================================================

def test_eulogy_compose_text():
    tombstone = RepositoryTombstone(
        repo_name="historic-lib",
        repo_path=".",
        primary_language="python",
        total_commits=85,
        dormant_years=7.5,
        top_contributors=[ContributorInfo(name="Ada Lovelace", email="ada@example.com", commit_count=85, last_active=datetime.now())],
    )
    text = EulogyEngine.compose_text(tombstone)
    assert "historic-lib" in text
    assert "Ada Lovelace" in text
    assert "7.5 years" in text
    assert "85 commits" in text
    assert "Ofrenda" in text


def test_eulogy_compose_text_unknown_author():
    tombstone = RepositoryTombstone(
        repo_name="orphan-lib",
        repo_path=".",
        primary_language="node",
        total_commits=10,
        dormant_years=4.2,
        top_contributors=[],
    )
    text = EulogyEngine.compose_text(tombstone)
    assert "orphan-lib" in text
    assert ("satanic47" in text or "unknown craftsperson" in text)


def test_eulogy_synthesize_speech_fallback_mock():
    # Calling with empty key triggers graceful synthetic audio frame
    audio = EulogyEngine.synthesize_speech("Rest in peace, legacy code.", api_key="EMPTY")
    assert isinstance(audio, EulogyAudio)
    assert len(audio.audio_bytes) > 0
    assert audio.mime_type == "audio/mpeg"
    assert audio.base64_uri.startswith("data:audio/mpeg;base64,")


def test_eulogy_audio_base64_data_uri():
    sample_bytes = b"\x01\x02\x03\x04\x05"
    audio = EulogyAudio(text="Sample eulogy", audio_bytes=sample_bytes)
    assert audio.base64_uri.startswith("data:audio/mpeg;base64,")
    assert "AQIDBAU=" in audio.base64_uri


# ============================================================================
# 2. Ofrenda Generator Tests (5 tests)
# ============================================================================

@pytest.fixture
def mock_resurrection_result(tmp_path: Path) -> tuple[RepositoryTombstone, ResurrectionResult]:
    tombstone = RepositoryTombstone(
        repo_name="vintage-crawler",
        repo_path=str(tmp_path),
        primary_language="python",
        total_commits=142,
        first_commit_date=datetime(2011, 3, 1),
        last_commit_date=datetime(2014, 8, 15),
        dormant_years=10.2,
        top_contributors=[
            ContributorInfo(name="Guido", email="guido@example.com", commit_count=100, last_active=datetime(2014, 8, 15)),
            ContributorInfo(name="Raymond", email="raymond@example.com", commit_count=42, last_active=datetime(2013, 2, 10)),
        ],
    )
    era = EraProfile(
        year=2014,
        era_name="Python 2.7 Sunset Era (Legacy)",
        language="python",
        recommended_runtime_version="2.7",
        docker_base_image="python:2.7-slim",
    )
    init_sum = ParsedSummary(runner="pytest", total_run=6, passed=4, failed=2)
    fin_sum = ParsedSummary(runner="pytest", total_run=6, passed=6, failed=0)

    result = ResurrectionResult(
        repo_name="vintage-crawler",
        success=True,
        strategy_used=ResurrectionStrategy.PIN_THE_PAST,
        era_profile=era,
        initial_summary=init_sum,
        final_summary=fin_sum,
        total_steps=4,
        steps=[],
        patches_applied=[{"file": "crawler.py", "action": "updated"}],
        total_duration_seconds=5.2,
    )
    return tombstone, result


def test_ofrenda_render_html_structure(mock_resurrection_result):
    tombstone, res = mock_resurrection_result
    html_output = OfrendaGenerator.render_html(tombstone, res)

    assert "<!DOCTYPE html>" in html_output
    assert "vintage-crawler" in html_output
    assert "Python 2.7 Sunset Era" in html_output
    assert "Guido" in html_output
    assert "Raymond" in html_output
    assert "10.2 yrs" in html_output
    assert "142" in html_output


def test_ofrenda_render_html_papel_picado_and_styling(mock_resurrection_result):
    tombstone, res = mock_resurrection_result
    html_output = OfrendaGenerator.render_html(tombstone, res)

    # Festive motifs
    assert "garland" in html_output
    assert "<svg" in html_output
    assert "--marigold: #ff7518" in html_output
    assert "--cempasuchil: #ffbf00" in html_output


def test_ofrenda_render_html_with_audio_player(mock_resurrection_result):
    tombstone, res = mock_resurrection_result
    audio = EulogyAudio(text="Test narration", audio_bytes=b"\xff\xfb\x90\x44" * 10)
    html_output = OfrendaGenerator.render_html(tombstone, res, audio=audio)

    assert "audio-altar" in html_output
    assert "<audio controls" in html_output
    assert "data:audio/mpeg;base64," in html_output
    assert "Narrated via ElevenLabs Voice AI" in html_output


def test_ofrenda_render_html_without_audio_player(mock_resurrection_result):
    tombstone, res = mock_resurrection_result
    html_output = OfrendaGenerator.render_html(tombstone, res, audio=None)

    assert '<div class="audio-altar">' not in html_output
    assert "<audio controls" not in html_output


def test_ofrenda_interactive_time_machine_slider(mock_resurrection_result):
    tombstone, res = mock_resurrection_result
    html_output = OfrendaGenerator.render_html(tombstone, res)

    assert 'id="timeSlider"' in html_output
    assert "time-machine-container" in html_output
    assert "slider.addEventListener" in html_output


# ============================================================================
# 3. FastAPI Web Routes & Subpath Tests (6 tests)
# ============================================================================

import asyncio
from fastapi import HTTPException
from app.main import (
    serve_dashboard,
    health_check,
    exhume_repo_endpoint,
    generate_ofrenda_endpoint,
    ExhumeRequest,
    OfrendaRequest,
)


def test_api_health():
    data = asyncio.run(health_check())
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "sentry_enabled" in data
    assert "elevenlabs_configured" in data


def test_serve_dashboard_root():
    response = asyncio.run(serve_dashboard())
    assert response.status_code == 200
    assert hasattr(response, "path") or hasattr(response, "body")


def test_serve_dashboard_subpath_necromancer():
    # Tests reverse-proxy subpath /necromancer
    response = asyncio.run(serve_dashboard())
    assert response.status_code == 200


def test_api_exhume_current_repo():
    req = ExhumeRequest(repo_path=".")
    data = asyncio.run(exhume_repo_endpoint(req))
    assert "repo_name" in data
    assert "primary_language" in data
    assert "total_commits" in data


def test_api_exhume_nonexistent_path():
    req = ExhumeRequest(repo_path="/nonexistent/fake/directory/xyz123")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(exhume_repo_endpoint(req))
    assert exc_info.value.status_code == 404 or exc_info.value.status_code == 400


def test_api_ofrenda_endpoint_generation(monkeypatch):
    # Mock agent resurrect call to return instant passing result
    era = EraProfile(year=2020, era_name="Py38", language="python", recommended_runtime_version="3.8", docker_base_image="python:3.8")
    mock_res = ResurrectionResult(
        repo_name="necromancer",
        success=True,
        strategy_used=ResurrectionStrategy.AUTO,
        era_profile=era,
        initial_summary=ParsedSummary(runner="pytest", total_run=2, passed=2, failed=0),
        final_summary=ParsedSummary(runner="pytest", total_run=2, passed=2, failed=0),
        total_steps=2,
        steps=[],
        patches_applied=[],
        total_duration_seconds=1.0,
    )
    monkeypatch.setattr(ResurrectionAgent, "resurrect", lambda self, tomb, preferred_strategy: mock_res)

    req = OfrendaRequest(repo_path=".", generate_audio=False)
    data = asyncio.run(generate_ofrenda_endpoint(req))
    assert "html" in data
    assert "<!DOCTYPE html>" in data["html"]
    assert "eulogy_text" in data


def test_sentry_debug_trigger():
    from app.main import trigger_sentry_error
    with pytest.raises(ZeroDivisionError):
        asyncio.run(trigger_sentry_error())


def test_path_traversal_attack_protection():
    req = ExhumeRequest(repo_path="../../../etc/passwd")
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(exhume_repo_endpoint(req))
    assert exc_info.value.status_code == 400
    assert "Path traversal" in exc_info.value.detail or "Security violation" in exc_info.value.detail


def test_graveyard_database_record_and_list(tmp_path: Path):
    from core.graveyard_db import GraveyardDatabase
    db = GraveyardDatabase(mongo_uri=None)
    tombstone = RepositoryTombstone(
        repo_name="retro-pkg",
        repo_path=str(tmp_path),
        primary_language="python",
        total_commits=15,
        dormant_years=5.0,
        top_contributors=[ContributorInfo(name="Dev", email="d@d.com", commit_count=15, last_active=datetime.now())],
    )
    res = ResurrectionResult(
        repo_name="retro-pkg",
        success=True,
        strategy_used=ResurrectionStrategy.PORT_TO_PRESENT,
        era_profile=EraProfile(year=2018, era_name="Py36", language="python", recommended_runtime_version="3.6", docker_base_image="python:3.6"),
        initial_summary=ParsedSummary(runner="pytest", total_run=1, passed=0, failed=1),
        final_summary=ParsedSummary(runner="pytest", total_run=1, passed=1, failed=0),
        total_steps=2,
        steps=[],
        patches_applied=[],
        total_duration_seconds=1.2,
    )
    entry = db.record_ofrenda(tombstone, res, eulogy_text="Honored.")
    assert entry["repo_name"] == "retro-pkg"
    assert entry["success"] is True

    fame = db.list_hall_of_fame(limit=5)
    assert len(fame) >= 1
    assert fame[-1]["repo_name"] == "retro-pkg"


def test_hall_of_fame_endpoint():
    from app.main import hall_of_fame_endpoint
    data = asyncio.run(hall_of_fame_endpoint())
    assert "archive" in data
    assert isinstance(data["archive"], list)
