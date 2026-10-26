"""
core/agent.py
Autonomous Resurrection Agent Harness for Necromancer.

Orchestrates the multi-turn resurrection loop:
1. Baseline test execution in hardened Docker sandbox.
2. Era detection & failure taxonomy categorization.
3. Resurrection strategy branching:
   - Branch A: "Pin the Past" (retro runtime, historical pip flags, legacy resolver)
   - Branch B: "Port to Present" (syntax modernization, stdlib imports, contemporary dependencies)
4. LLM patch generation (Ollama / vLLM / OpenAI API).
5. Strict Test Integrity Invariant Verification (prevents regression and cheating).
6. Sentry observability tracing (spans, token usage, latency, sandbox diagnostics).
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx
import sentry_sdk

from core.era_detect import EraDetector, EraProfile
from core.exhume import ExhumationEngine, RepositoryTombstone
from core.repo_map import RepoMapper
from core.sandbox import DockerSandbox, SandboxResult, SandboxSecurityConfig
from core.taxonomy import FailureReport, FailureTaxonomyEngine
from core.test_integrity import IntegrityAssessment, ParsedSummary, TestIntegrityParser


class ResurrectionStrategy(str, Enum):
    PIN_THE_PAST = "PIN_THE_PAST"
    PORT_TO_PRESENT = "PORT_TO_PRESENT"
    AUTO = "AUTO"


@dataclass
class AgentStepLog:
    step_number: int
    action: str
    thought: str
    tool_call: Optional[str] = None
    observation: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    duration_seconds: float = 0.0


@dataclass
class ResurrectionResult:
    repo_name: str
    success: bool
    strategy_used: ResurrectionStrategy
    era_profile: EraProfile
    initial_summary: ParsedSummary
    final_summary: ParsedSummary
    total_steps: int
    steps: List[AgentStepLog]
    patches_applied: List[Dict[str, str]]
    total_duration_seconds: float
    error_message: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "success": self.success,
            "strategy_used": self.strategy_used.value,
            "era_profile": self.era_profile.to_dict(),
            "initial_summary": self.initial_summary.to_dict(),
            "final_summary": self.final_summary.to_dict(),
            "total_steps": self.total_steps,
            "patches_applied": self.patches_applied,
            "total_duration_seconds": self.total_duration_seconds,
            "error_message": self.error_message,
        }


class LLMClient:
    """Interface to local vLLM / Ollama or OpenAI-compatible endpoints."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = "qwen2.5-coder:7b",
        api_key: str = "EMPTY",
        mock_response_generator: Optional[Callable[[str], str]] = None,
    ):
        self.base_url = base_url or os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
        self.model = os.getenv("LLM_MODEL", model)
        self.api_key = api_key
        self.mock_generator = mock_response_generator

    def generate_patch(self, prompt: str, system_prompt: str) -> str:
        """Invokes the model to generate file diffs or source patches."""
        if self.mock_generator:
            return self.mock_generator(prompt)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 2048,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                res = client.post(f"{self.base_url}/chat/completions", headers=headers, json=payload)
                res.raise_for_status()
                data = res.json()
                return data["choices"][0]["message"]["content"]
        except Exception as err:
            return f"[ERROR: Failed to connect to LLM backend at {self.base_url}: {err}]"


SYSTEM_PROMPT = """You are Necromancer, a Staff Software Engineer specialized in resurrecting legacy open-source projects.
Your goal is to inspect compiler/test failures and generate clean, surgical patches to restore test suites.

Strict rules:
1. Do NOT delete or comment out existing tests.
2. Maintain backward-compatibility and original intent.
3. Emit your response in JSON format:
{
  "thought": "Analysis of the failure and plan",
  "files_to_modify": [
    {
      "file_path": "path/to/file.py",
      "action": "replace",
      "content": "Full file content or targeted replacement"
    }
  ]
}
"""


class ResurrectionAgent:
    """Autonomous agent engine guiding repository resurrection."""

    def __init__(
        self,
        sandbox: DockerSandbox,
        llm_client: Optional[LLMClient] = None,
        max_iterations: int = 5,
        sentry_dsn: Optional[str] = None,
    ):
        self.sandbox = sandbox
        self.llm_client = llm_client or LLMClient()
        self.max_iterations = max_iterations
        self._init_sentry(sentry_dsn or os.getenv("SENTRY_DSN"))

    def _init_sentry(self, dsn: Optional[str]):
        if dsn and not sentry_sdk.is_initialized() and os.getenv("TESTING", "0") != "1":
            try:
                sentry_sdk.init(
                    dsn=dsn,
                    traces_sample_rate=1.0,
                    environment="production",
                    release=f"necromancer@{os.getenv('APP_VERSION', '0.2.0')}",
                )
            except Exception:
                pass

    def resurrect(
        self,
        tombstone: RepositoryTombstone,
        preferred_strategy: ResurrectionStrategy = ResurrectionStrategy.AUTO,
    ) -> ResurrectionResult:
        """Executes the closed-loop resurrection lifecycle."""
        start_time = time.time()
        steps: List[AgentStepLog] = []
        patches: List[Dict[str, str]] = []

        repo_path = Path(tombstone.repo_path)

        with sentry_sdk.start_transaction(op="resurrection.run", name=f"Resurrect {tombstone.repo_name}"):
            sentry_sdk.set_tag("repo_name", tombstone.repo_name)
            sentry_sdk.set_tag("language", tombstone.primary_language)

            # Step 1: Detect Era
            s1_start = time.time()
            era_profile = EraDetector.detect_era(
                repo_path=repo_path,
                last_commit_date=tombstone.last_commit_date,
                language=tombstone.primary_language,
            )
            strategy = (
                preferred_strategy
                if preferred_strategy != ResurrectionStrategy.AUTO
                else (
                    ResurrectionStrategy.PIN_THE_PAST
                    if era_profile.recommended_runtime_version == "2.7"
                    else ResurrectionStrategy.PORT_TO_PRESENT
                )
            )
            sentry_sdk.set_tag("era_year", era_profile.year)
            sentry_sdk.set_tag("strategy", strategy.value)

            steps.append(
                AgentStepLog(
                    step_number=1,
                    action="ERA_DETECTION",
                    thought=f"Detected vintage {era_profile.year} ({era_profile.era_name}). Selected strategy: {strategy.value}",
                    observation=f"Image: {era_profile.docker_base_image}, Flags: {era_profile.compatibility_flags}",
                    duration_seconds=round(time.time() - s1_start, 3),
                )
            )

            # Step 2: Run Baseline Tests
            s2_start = time.time()
            test_cmd = "pytest" if tombstone.primary_language == "python" else "npm test"
            base_run = self.sandbox.run_command(repo_path, test_cmd, image=era_profile.docker_base_image)
            baseline_summary = TestIntegrityParser.parse_output(base_run.stdout + "\n" + base_run.stderr)

            steps.append(
                AgentStepLog(
                    step_number=2,
                    action="BASELINE_TEST_EXECUTION",
                    thought="Establishing pre-resurrection test benchmark.",
                    tool_call=f"sandbox.run({test_cmd})",
                    observation=f"Passed: {baseline_summary.passed}, Failed: {baseline_summary.failed}, Total: {baseline_summary.total_run}",
                    duration_seconds=round(time.time() - s2_start, 3),
                )
            )

            current_summary = baseline_summary

            # Check if repo was already passing without any resurrection needed
            if baseline_summary.failed == 0 and baseline_summary.total_run > 0:
                return ResurrectionResult(
                    repo_name=tombstone.repo_name,
                    success=True,
                    strategy_used=strategy,
                    era_profile=era_profile,
                    initial_summary=baseline_summary,
                    final_summary=baseline_summary,
                    total_steps=len(steps),
                    steps=steps,
                    patches_applied=[],
                    total_duration_seconds=round(time.time() - start_time, 3),
                )

            # Iterative agent repair loop
            repo_map = RepoMapper.generate_map(repo_path)
            skeleton_summary = repo_map.to_condensed_prompt_outline(max_chars=3000)

            for iteration in range(1, self.max_iterations + 1):
                step_idx = len(steps) + 1
                loop_start = time.time()

                # Parse failure taxonomy
                raw_logs = base_run.stdout + "\n" + base_run.stderr
                taxonomy_report = FailureTaxonomyEngine.classify(raw_logs)
                prompt_failures = taxonomy_report.to_llm_prompt_summary()

                llm_prompt = (
                    f"Repository: {tombstone.repo_name}\n"
                    f"Era: {era_profile.era_name}\n"
                    f"Selected Strategy: {strategy.value}\n\n"
                    f"{skeleton_summary}\n\n"
                    f"{prompt_failures}\n\n"
                    "Generate a surgical JSON fix for the top failing targets."
                )

                llm_response = self.llm_client.generate_patch(llm_prompt, SYSTEM_PROMPT)

                # Attempt applying patches
                applied_files = []
                thought = "Analyzing compiler failures"
                try:
                    # Clean markdown fence if present
                    clean_json = llm_response.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json[7:]
                    if clean_json.endswith("```"):
                        clean_json = clean_json[:-3]
                    parsed_json = json.loads(clean_json.strip())
                    thought = parsed_json.get("thought", thought)

                    for mod_file in parsed_json.get("files_to_modify", []):
                        rel_p = mod_file["file_path"]
                        content = mod_file["content"]
                        target_path = repo_path / rel_p
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        target_path.write_text(content, encoding="utf-8")
                        applied_files.append(rel_p)
                        patches.append({"file": rel_p, "action": "updated"})
                except Exception as err:
                    steps.append(
                        AgentStepLog(
                            step_number=step_idx,
                            action="PATCH_APPLICATION_ERROR",
                            thought=f"Failed to parse LLM patch: {err}",
                            observation=llm_response[:200],
                            duration_seconds=round(time.time() - loop_start, 3),
                        )
                    )
                    continue

                # Re-run sandbox test evaluation
                eval_run = self.sandbox.run_command(repo_path, test_cmd, image=era_profile.docker_base_image)
                candidate_summary = TestIntegrityParser.parse_output(eval_run.stdout + "\n" + eval_run.stderr)
                integrity = TestIntegrityParser.evaluate_integrity(baseline_summary, candidate_summary)

                steps.append(
                    AgentStepLog(
                        step_number=step_idx,
                        action=f"REPAIR_CYCLE_{iteration}",
                        thought=thought,
                        tool_call=f"Applied patches to: {', '.join(applied_files)}",
                        observation=f"Result: {candidate_summary.passed} passed, {candidate_summary.failed} failed. Valid: {integrity.is_valid} ({integrity.reason})",
                        duration_seconds=round(time.time() - loop_start, 3),
                    )
                )

                base_run = eval_run
                current_summary = candidate_summary

                if integrity.is_valid and candidate_summary.failed == 0 and candidate_summary.passed > 0:
                    sentry_sdk.capture_message(f"Resurrection successful for {tombstone.repo_name}")
                    return ResurrectionResult(
                        repo_name=tombstone.repo_name,
                        success=True,
                        strategy_used=strategy,
                        era_profile=era_profile,
                        initial_summary=baseline_summary,
                        final_summary=candidate_summary,
                        total_steps=len(steps),
                        steps=steps,
                        patches_applied=patches,
                        total_duration_seconds=round(time.time() - start_time, 3),
                    )

            # Max iterations reached without clean passing tests
            return ResurrectionResult(
                repo_name=tombstone.repo_name,
                success=False,
                strategy_used=strategy,
                era_profile=era_profile,
                initial_summary=baseline_summary,
                final_summary=current_summary,
                total_steps=len(steps),
                steps=steps,
                patches_applied=patches,
                total_duration_seconds=round(time.time() - start_time, 3),
                error_message="Exceeded max repair iterations without achieving 100% test pass integrity.",
            )
