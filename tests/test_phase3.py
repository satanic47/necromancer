"""
tests/test_phase3.py
Comprehensive Verification Suite for Phase 3:
- Resurrection Strategies & Data Contracts (4 tests)
- LLM Client Mock & Error Boundary (3 tests)
- Agent Orchestration & Baseline Execution (4 tests)
- Test Integrity Enforcement in Agent Loop (3 tests)
- Sentry Initialization & Fallback (2 tests)
Total: 16 Unit Tests
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from core.agent import (
    AgentStepLog,
    LLMClient,
    ResurrectionAgent,
    ResurrectionResult,
    ResurrectionStrategy,
)
from core.era_detect import EraProfile
from core.exhume import RepositoryTombstone
from core.sandbox import DockerSandbox, SandboxResult, SandboxSecurityConfig
from core.test_integrity import ParsedSummary


# ============================================================================
# 1. Strategies & Data Contracts (4 tests)
# ============================================================================

def test_resurrection_strategy_enum():
    assert ResurrectionStrategy.PIN_THE_PAST.value == "PIN_THE_PAST"
    assert ResurrectionStrategy.PORT_TO_PRESENT.value == "PORT_TO_PRESENT"
    assert ResurrectionStrategy.AUTO.value == "AUTO"


def test_agent_step_log_dataclass():
    step = AgentStepLog(
        step_number=1,
        action="TEST_ACTION",
        thought="Thinking about code",
        tool_call="run_command(pytest)",
        observation="5 passed",
        duration_seconds=1.23,
    )
    assert step.step_number == 1
    assert step.action == "TEST_ACTION"
    assert step.duration_seconds == 1.23
    assert step.timestamp is not None


def test_resurrection_result_to_dict():
    era = EraProfile(
        year=2014,
        era_name="Legacy",
        language="python",
        recommended_runtime_version="2.7",
        docker_base_image="python:2.7-slim",
    )
    init_sum = ParsedSummary(runner="pytest", total_run=5, passed=3, failed=2)
    fin_sum = ParsedSummary(runner="pytest", total_run=5, passed=5, failed=0)

    result = ResurrectionResult(
        repo_name="old-lib",
        success=True,
        strategy_used=ResurrectionStrategy.PIN_THE_PAST,
        era_profile=era,
        initial_summary=init_sum,
        final_summary=fin_sum,
        total_steps=3,
        steps=[],
        patches_applied=[{"file": "app.py", "action": "updated"}],
        total_duration_seconds=4.5,
    )

    data = result.to_dict()
    assert data["repo_name"] == "old-lib"
    assert data["success"] is True
    assert data["strategy_used"] == "PIN_THE_PAST"
    assert data["initial_summary"]["failed"] == 2
    assert data["final_summary"]["failed"] == 0
    assert len(data["patches_applied"]) == 1


def test_resurrection_result_failure_contract():
    era = EraProfile(
        year=2015,
        era_name="Early Py3",
        language="python",
        recommended_runtime_version="3.6",
        docker_base_image="python:3.6-slim",
    )
    summary = ParsedSummary(runner="pytest", total_run=4, passed=2, failed=2)

    res = ResurrectionResult(
        repo_name="failing-repo",
        success=False,
        strategy_used=ResurrectionStrategy.PORT_TO_PRESENT,
        era_profile=era,
        initial_summary=summary,
        final_summary=summary,
        total_steps=5,
        steps=[],
        patches_applied=[],
        total_duration_seconds=10.0,
        error_message="Could not resolve all failures",
    )
    assert res.success is False
    assert "Could not resolve" in res.error_message


# ============================================================================
# 2. LLM Client Mock & Error Boundaries (3 tests)
# ============================================================================

def test_llm_client_mock_generator():
    mock_fn = lambda prompt: json.dumps({"thought": "Mock fix", "files_to_modify": []})
    client = LLMClient(mock_response_generator=mock_fn)
    resp = client.generate_patch("some failure prompt", "system prompt")
    parsed = json.loads(resp)
    assert parsed["thought"] == "Mock fix"


def test_llm_client_default_parameters():
    client = LLMClient()
    assert "11434" in client.base_url or "localhost" in client.base_url
    assert client.model is not None


def test_llm_client_unreachable_endpoint_handling():
    # Points to an unreachable port to verify graceful error return rather than unhandled exception
    client = LLMClient(base_url="http://127.0.0.1:59999/v1")
    resp = client.generate_patch("prompt", "system prompt")
    assert "[ERROR: Failed to connect" in resp


# ============================================================================
# 3. Agent Orchestration & Baseline Execution (4 tests)
# ============================================================================

class MockSandbox(DockerSandbox):
    """Sandbox simulator returning predefined command outputs."""

    def __init__(self, responses: list[SandboxResult]):
        self.responses = list(responses)
        self.invocations: list[str] = []
        self.base_image = "python:3.10-slim"
        self.config = SandboxSecurityConfig()

    def run_command(self, repo_path: Path, command: str, image: str | None = None) -> SandboxResult:
        self.invocations.append(command)
        if self.responses:
            return self.responses.pop(0)
        return SandboxResult(command=command, exit_code=0, stdout="================= 1 passed in 0.1s =================")


def test_agent_already_passing_repo(tmp_path: Path):
    passing_run = SandboxResult(
        command="pytest",
        exit_code=0,
        stdout="======================== 10 passed in 0.45s ========================",
    )
    sandbox = MockSandbox([passing_run])
    agent = ResurrectionAgent(sandbox=sandbox)

    tombstone = RepositoryTombstone(
        repo_name="clean-repo",
        repo_path=tmp_path,
        last_commit_date=datetime(2021, 5, 1),
        days_dormant=1500,
        primary_language="python",
    )

    result = agent.resurrect(tombstone)
    assert result.success is True
    assert result.initial_summary.passed == 10
    assert result.initial_summary.failed == 0
    assert len(result.patches_applied) == 0
    assert result.total_steps == 2  # Era detection + baseline test execution


def test_agent_successful_resurrection_loop(tmp_path: Path):
    # Step 1: Failing baseline
    fail_run = SandboxResult(
        command="pytest",
        exit_code=1,
        stdout="""
  File "app.py", line 10
    print "Deprecated print"
SyntaxError: Missing parentheses in call to 'print'.
======================== 1 failed in 0.20s ========================
""",
    )
    # Step 2: Passing after patch
    pass_run = SandboxResult(
        command="pytest",
        exit_code=0,
        stdout="======================== 2 passed in 0.35s ========================",
    )
    sandbox = MockSandbox([fail_run, pass_run])

    # LLM returns surgical fix
    patch_json = json.dumps({
        "thought": "Replace legacy print statement with print function",
        "files_to_modify": [
            {
                "file_path": "app.py",
                "content": "def run():\n    print('Fixed print')\n",
            }
        ],
    })
    llm = LLMClient(mock_response_generator=lambda p: patch_json)
    agent = ResurrectionAgent(sandbox=sandbox, llm_client=llm)

    tombstone = RepositoryTombstone(
        repo_name="resurrected-lib",
        repo_path=tmp_path,
        last_commit_date=datetime(2013, 4, 1),
        days_dormant=4000,
        primary_language="python",
    )

    result = agent.resurrect(tombstone)
    assert result.success is True
    assert result.final_summary.passed == 2
    assert result.final_summary.failed == 0
    assert len(result.patches_applied) == 1
    # Verify file was written to disk
    assert (tmp_path / "app.py").exists()
    assert "Fixed print" in (tmp_path / "app.py").read_text()


def test_agent_auto_strategy_selection_py2(tmp_path: Path):
    (tmp_path / "cli.py").write_text('print "vintage 2012"')
    passing_run = SandboxResult(command="pytest", exit_code=0, stdout="====== 1 passed in 0.1s ======")
    sandbox = MockSandbox([passing_run])
    agent = ResurrectionAgent(sandbox=sandbox)

    tombstone = RepositoryTombstone(
        repo_name="vintage-project",
        repo_path=tmp_path,
        last_commit_date=datetime(2012, 1, 1),
        days_dormant=5000,
        primary_language="python",
    )
    res = agent.resurrect(tombstone, preferred_strategy=ResurrectionStrategy.AUTO)
    assert res.strategy_used == ResurrectionStrategy.PIN_THE_PAST


def test_agent_auto_strategy_selection_modern(tmp_path: Path):
    passing_run = SandboxResult(command="pytest", exit_code=0, stdout="====== 5 passed in 0.1s ======")
    sandbox = MockSandbox([passing_run])
    agent = ResurrectionAgent(sandbox=sandbox)

    tombstone = RepositoryTombstone(
        repo_name="modern-project",
        repo_path=tmp_path,
        last_commit_date=datetime(2023, 1, 1),
        days_dormant=500,
        primary_language="python",
    )
    res = agent.resurrect(tombstone, preferred_strategy=ResurrectionStrategy.AUTO)
    assert res.strategy_used == ResurrectionStrategy.PORT_TO_PRESENT


# ============================================================================
# 4. Test Integrity Enforcement in Agent Loop (3 tests)
# ============================================================================

def test_agent_rejects_test_deletion_cheat(tmp_path: Path):
    # Baseline: 5 tests (3 passed, 2 failed)
    fail_run = SandboxResult(
        command="pytest",
        exit_code=1,
        stdout="==================== 2 failed, 3 passed in 0.5s ====================",
    )
    # Candidate run: 3 passed, 0 failed, but 2 tests were DELETED (total went 5 -> 3)
    cheat_run = SandboxResult(
        command="pytest",
        exit_code=0,
        stdout="======================== 3 passed in 0.3s ========================",
    )
    sandbox = MockSandbox([fail_run, cheat_run, cheat_run])

    # LLM produces patch
    patch_json = json.dumps({
        "thought": "Deleting the failing tests to pass",
        "files_to_modify": [{"file_path": "test_del.py", "content": "# deleted"}],
    })
    llm = LLMClient(mock_response_generator=lambda p: patch_json)
    agent = ResurrectionAgent(sandbox=sandbox, llm_client=llm, max_iterations=2)

    tombstone = RepositoryTombstone(
        repo_name="cheat-attempt-repo",
        repo_path=tmp_path,
        last_commit_date=datetime(2018, 1, 1),
        days_dormant=2000,
        primary_language="python",
    )

    result = agent.resurrect(tombstone)
    # Agent must reject the resurrection because test count decreased
    assert result.success is False
    assert "Exceeded max repair iterations" in result.error_message


def test_agent_handles_invalid_json_from_llm(tmp_path: Path):
    fail_run = SandboxResult(
        command="pytest",
        exit_code=1,
        stdout="==================== 1 failed, 1 passed in 0.5s ====================",
    )
    sandbox = MockSandbox([fail_run, fail_run, fail_run])
    # LLM outputs non-JSON prose
    llm = LLMClient(mock_response_generator=lambda p: "Sure, I think you should edit line 4.")
    agent = ResurrectionAgent(sandbox=sandbox, llm_client=llm, max_iterations=1)

    tombstone = RepositoryTombstone(
        repo_name="malformed-llm-repo",
        repo_path=tmp_path,
        last_commit_date=datetime(2019, 1, 1),
        days_dormant=1500,
        primary_language="python",
    )
    result = agent.resurrect(tombstone)
    assert result.success is False
    error_steps = [s for s in result.steps if s.action == "PATCH_APPLICATION_ERROR"]
    assert len(error_steps) >= 1


def test_agent_strips_markdown_fences_from_llm_json(tmp_path: Path):
    fail_run = SandboxResult(
        command="pytest",
        exit_code=1,
        stdout="==================== 1 failed, 1 passed in 0.5s ====================",
    )
    pass_run = SandboxResult(
        command="pytest",
        exit_code=0,
        stdout="======================== 2 passed in 0.2s ========================",
    )
    sandbox = MockSandbox([fail_run, pass_run])

    # LLM wraps valid json in markdown fences
    fenced_json = "```json\n" + json.dumps({
        "thought": "Fixing fence",
        "files_to_modify": [{"file_path": "fixed.py", "content": "x = 1"}],
    }) + "\n```"

    llm = LLMClient(mock_response_generator=lambda p: fenced_json)
    agent = ResurrectionAgent(sandbox=sandbox, llm_client=llm)

    tombstone = RepositoryTombstone(
        repo_name="fenced-json-repo",
        repo_path=tmp_path,
        last_commit_date=datetime(2020, 1, 1),
        days_dormant=1200,
        primary_language="python",
    )
    result = agent.resurrect(tombstone)
    assert result.success is True
    assert (tmp_path / "fixed.py").exists()


# ============================================================================
# 5. Sentry Initialization & Fallback (2 tests)
# ============================================================================

def test_sentry_initialization_no_dsn():
    # Passing None should not throw
    agent = ResurrectionAgent(sandbox=MockSandbox([]), sentry_dsn=None)
    assert agent is not None


def test_sentry_initialization_invalid_dsn():
    # Invalid DSN should be safely caught in try/except without crashing
    agent = ResurrectionAgent(sandbox=MockSandbox([]), sentry_dsn="invalid-dsn-string")
    assert agent is not None
