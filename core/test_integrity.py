"""
core/test_integrity.py
Parses and validates test execution output (Pytest / Unittest).
Guarantees that test integrity is maintained:
- Tests passed cannot decrease.
- Total tests executed cannot drop below baseline.
"""

from __future__ import annotations

import re
from typing import NamedTuple, Optional
from pydantic import BaseModel


class ParsedSummary(BaseModel):
    runner: str  # "pytest" or "unittest"
    total_run: int = 0
    passed: int = 0
    failed: int = 0
    errors: int = 0
    skipped: int = 0
    raw_summary: str = ""


class IntegrityAssessment(BaseModel):
    is_valid: bool
    reason: str
    baseline_passed: int
    current_passed: int
    delta: int


class TestIntegrityParser:
    """
    Parses Pytest and standard library Unittest outputs into structured metrics.
    """

    @staticmethod
    def parse_output(output_text: str) -> ParsedSummary:
        """
        Detects runner type and extracts test metrics from console logs.
        """
        # 1. Try Pytest pattern
        # Look for summary lines ending with "=... in ...s =..."
        pytest_summary_match = re.search(r"=+ (.*?) in [\d\.]+s =+", output_text)
        if pytest_summary_match:
            summary_content = pytest_summary_match.group(1)
            passed = 0
            failed = 0
            errors = 0
            skipped = 0

            p_m = re.search(r"(\d+)\s+passed", summary_content)
            if p_m:
                passed = int(p_m.group(1))

            f_m = re.search(r"(\d+)\s+failed", summary_content)
            if f_m:
                failed = int(f_m.group(1))

            e_m = re.search(r"(\d+)\s+error", summary_content)
            if e_m:
                errors = int(e_m.group(1))

            s_m = re.search(r"(\d+)\s+skipped", summary_content)
            if s_m:
                skipped = int(s_m.group(1))

            total = passed + failed + errors + skipped
            return ParsedSummary(
                runner="pytest",
                total_run=total,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                raw_summary=pytest_summary_match.group(0),
            )

        # 2. Try Python unittest pattern
        unittest_ran_regex = re.compile(r"Ran (?P<total>\d+) tests? in [\d\.]+s", re.MULTILINE)
        ran_match = unittest_ran_regex.search(output_text)

        if ran_match:
            total = int(ran_match.group("total") or 0)
            failed = 0
            errors = 0
            skipped = 0

            fail_match = re.search(r"FAILED \((?:failures=(?P<fails>\d+))?(?:, )?(?:errors=(?P<errs>\d+))?\)", output_text)
            ok_match = re.search(r"^OK(?: \(skipped=(?P<skips>\d+)\))?", output_text, re.MULTILINE)

            if ok_match:
                skipped = int(ok_match.group("skips") or 0)
                passed = total - skipped
            elif fail_match:
                failed = int(fail_match.group("fails") or 0)
                errors = int(fail_match.group("errs") or 0)
                passed = max(0, total - failed - errors)
            else:
                passed = 0

            return ParsedSummary(
                runner="unittest",
                total_run=total,
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                raw_summary=ran_match.group(0),
            )

        return ParsedSummary(
            runner="unknown",
            total_run=0,
            passed=0,
            failed=0,
            errors=0,
            skipped=0,
            raw_summary="No recognized test summary matched.",
        )

    @staticmethod
    def evaluate_integrity(
        baseline: ParsedSummary,
        candidate: ParsedSummary,
    ) -> IntegrityAssessment:
        """
        Enforces test integrity invariants:
        - candidate.passed must be >= baseline.passed
        - candidate.total_run must be >= baseline.total_run (no deletion of tests)
        - candidate.failed must be 0 for a certified resurrection
        """
        delta = candidate.passed - baseline.passed

        if candidate.total_run < baseline.total_run:
            return IntegrityAssessment(
                is_valid=False,
                reason=(
                    f"Test regression detected: total tests decreased from "
                    f"{baseline.total_run} to {candidate.total_run}. "
                    f"Tests may have been improperly deleted or skipped."
                ),
                baseline_passed=baseline.passed,
                current_passed=candidate.passed,
                delta=delta,
            )

        if candidate.passed < baseline.passed:
            return IntegrityAssessment(
                is_valid=False,
                reason=(
                    f"Passing test count degraded: previously passing {baseline.passed}, "
                    f"now passing {candidate.passed} (delta: {delta})."
                ),
                baseline_passed=baseline.passed,
                current_passed=candidate.passed,
                delta=delta,
            )

        if candidate.failed > 0 or candidate.errors > 0:
            return IntegrityAssessment(
                is_valid=False,
                reason=(
                    f"Candidate still has failing tests: {candidate.failed} failures, "
                    f"{candidate.errors} errors."
                ),
                baseline_passed=baseline.passed,
                current_passed=candidate.passed,
                delta=delta,
            )

        return IntegrityAssessment(
            is_valid=True,
            reason=f"Integrity verified: all {candidate.passed} tests passed successfully.",
            baseline_passed=baseline.passed,
            current_passed=candidate.passed,
            delta=delta,
        )
