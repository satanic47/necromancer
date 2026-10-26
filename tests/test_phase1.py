"""
tests/test_phase1.py
Comprehensive 28-test verification suite for Phase 1:
- Pytest Output Parsing (8 tests)
- Unittest Output Parsing (6 tests)
- Unknown / Edge Cases (2 tests)
- Test-Integrity Invariant Evaluations (6 tests)
- Sandbox Security Configurations (3 tests)
- Language Detection Heuristics (3 tests)
"""

from pathlib import Path
import pytest
from core.test_integrity import TestIntegrityParser, ParsedSummary, IntegrityAssessment
from core.sandbox import SandboxSecurityConfig, SandboxResult
from core.exhume import detect_language


# ==========================================
# 1. Pytest Output Parsing (8 tests)
# ==========================================

def test_parse_pytest_all_passed():
    raw = "======================== 15 passed in 0.32s ========================"
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.runner == "pytest"
    assert summary.passed == 15
    assert summary.failed == 0
    assert summary.total_run == 15


def test_parse_pytest_single_failure():
    raw = "=================== 1 failed, 9 passed in 0.42s ===================="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.runner == "pytest"
    assert summary.passed == 9
    assert summary.failed == 1
    assert summary.total_run == 10


def test_parse_pytest_multiple_failures():
    raw = "=================== 4 failed, 6 passed in 1.20s ===================="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 6
    assert summary.failed == 4
    assert summary.total_run == 10


def test_parse_pytest_with_errors():
    raw = "============= 2 failed, 10 passed, 3 errors in 2.15s ============="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 10
    assert summary.failed == 2
    assert summary.errors == 3
    assert summary.total_run == 15


def test_parse_pytest_with_skipped():
    raw = "============= 8 passed, 2 skipped, 1 failed in 0.90s ============="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 8
    assert summary.skipped == 2
    assert summary.failed == 1
    assert summary.total_run == 11


def test_parse_pytest_mixed_order_summary():
    raw = "============= 5 failed, 2 errors, 14 passed in 0.85s ============="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 14
    assert summary.failed == 5
    assert summary.errors == 2
    assert summary.total_run == 21


def test_parse_pytest_complex_decimal_time():
    raw = "======================= 100 passed in 14.892s ======================="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 100
    assert summary.total_run == 100


def test_parse_pytest_zero_tests():
    raw = "======================= 0 passed in 0.01s ======================="
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 0
    assert summary.total_run == 0


# ==========================================
# 2. Unittest Output Parsing (6 tests)
# ==========================================

def test_parse_unittest_all_ok():
    raw = """
test_a (tests.Test) ... ok
test_b (tests.Test) ... ok
----------------------------------------------------------------------
Ran 2 tests in 0.005s

OK
"""
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.runner == "unittest"
    assert summary.passed == 2
    assert summary.failed == 0
    assert summary.total_run == 2


def test_parse_unittest_single_failure():
    raw = """
test_a (tests.Test) ... FAIL
----------------------------------------------------------------------
Ran 5 tests in 0.012s

FAILED (failures=1)
"""
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.runner == "unittest"
    assert summary.passed == 4
    assert summary.failed == 1
    assert summary.total_run == 5


def test_parse_unittest_errors_only():
    raw = """
test_err (tests.Test) ... ERROR
----------------------------------------------------------------------
Ran 4 tests in 0.020s

FAILED (errors=2)
"""
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.runner == "unittest"
    assert summary.passed == 2
    assert summary.errors == 2
    assert summary.total_run == 4


def test_parse_unittest_failures_and_errors():
    raw = """
Ran 10 tests in 0.050s

FAILED (failures=3, errors=2)
"""
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 5
    assert summary.failed == 3
    assert summary.errors == 2
    assert summary.total_run == 10


def test_parse_unittest_with_skipped():
    raw = """
Ran 8 tests in 0.030s

OK (skipped=3)
"""
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 5
    assert summary.skipped == 3
    assert summary.total_run == 8


def test_parse_unittest_single_test_grammar():
    raw = """
Ran 1 test in 0.001s

OK
"""
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.passed == 1
    assert summary.total_run == 1


# ==========================================
# 3. Unknown / Edge Cases (2 tests)
# ==========================================

def test_parse_unknown_runner():
    raw = "Compilation error: syntax error in main.c line 42"
    summary = TestIntegrityParser.parse_output(raw)
    assert summary.runner == "unknown"
    assert summary.total_run == 0
    assert summary.passed == 0


def test_parse_empty_string():
    summary = TestIntegrityParser.parse_output("")
    assert summary.runner == "unknown"
    assert summary.total_run == 0


# ==========================================
# 4. Test-Integrity Invariants (6 tests)
# ==========================================

def test_evaluate_integrity_perfect_resurrection():
    baseline = ParsedSummary(runner="pytest", total_run=10, passed=7, failed=3)
    candidate = ParsedSummary(runner="pytest", total_run=10, passed=10, failed=0)
    res = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert res.is_valid is True
    assert res.delta == 3


def test_evaluate_integrity_partial_progress_still_failing():
    baseline = ParsedSummary(runner="pytest", total_run=10, passed=5, failed=5)
    candidate = ParsedSummary(runner="pytest", total_run=10, passed=8, failed=2)
    res = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert res.is_valid is False
    assert "still has failing tests" in res.reason


def test_evaluate_integrity_regression_test_count_dropped():
    baseline = ParsedSummary(runner="pytest", total_run=10, passed=10, failed=0)
    # 2 tests deleted to bypass failures
    candidate = ParsedSummary(runner="pytest", total_run=8, passed=8, failed=0)
    res = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert res.is_valid is False
    assert "total tests decreased" in res.reason


def test_evaluate_integrity_regression_passed_count_dropped():
    baseline = ParsedSummary(runner="pytest", total_run=10, passed=8, failed=2)
    candidate = ParsedSummary(runner="pytest", total_run=10, passed=6, failed=4)
    res = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert res.is_valid is False
    assert "Passing test count degraded" in res.reason


def test_evaluate_integrity_same_counts_no_failures():
    baseline = ParsedSummary(runner="unittest", total_run=5, passed=5, failed=0)
    candidate = ParsedSummary(runner="unittest", total_run=5, passed=5, failed=0)
    res = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert res.is_valid is True
    assert res.delta == 0


def test_evaluate_integrity_zero_baseline_to_all_passed():
    baseline = ParsedSummary(runner="pytest", total_run=0, passed=0, failed=0)
    candidate = ParsedSummary(runner="pytest", total_run=4, passed=4, failed=0)
    res = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert res.is_valid is True
    assert res.delta == 4


# ==========================================
# 5. Sandbox Security Configs (3 tests)
# ==========================================

def test_sandbox_security_config_defaults():
    config = SandboxSecurityConfig()
    assert config.memory_limit == "1g"
    assert config.cpu_quota == 100000
    assert config.network_disabled is True
    assert config.pids_limit == 128


def test_sandbox_security_config_custom_limits():
    config = SandboxSecurityConfig(memory_limit="512m", pids_limit=64, timeout_seconds=45)
    assert config.memory_limit == "512m"
    assert config.pids_limit == 64
    assert config.timeout_seconds == 45


def test_sandbox_result_dataclass():
    res = SandboxResult(
        command="pytest",
        exit_code=0,
        stdout="passed",
        stderr="",
        execution_time_seconds=1.5,
        timed_out=False,
    )
    assert res.exit_code == 0
    assert res.timed_out is False
    assert res.execution_time_seconds == 1.5


def test_sandbox_subprocess_fallback(tmp_path: Path):
    from core.sandbox import DockerSandbox
    (tmp_path / "hello.txt").write_text("world")
    sandbox = DockerSandbox()
    sandbox.docker_available = False
    res = sandbox.execute_in_sandbox(tmp_path, "python -c \"print('isolated output')\"")
    assert res.exit_code == 0
    assert "isolated output" in res.stdout


# ==========================================
# 6. Language Detection Heuristics (3 tests)
# ==========================================

def test_detect_language_python_indicators(tmp_path: Path):
    (tmp_path / "setup.py").write_text("from setuptools import setup; setup()")
    (tmp_path / "requirements.txt").write_text("requests==2.20.0")
    lang, files = detect_language(tmp_path)
    assert lang == "python"
    assert "setup.py" in files
    assert "requirements.txt" in files


def test_detect_language_node_indicators(tmp_path: Path):
    (tmp_path / "package.json").write_text('{"name": "legacy-app", "version": "1.0.0"}')
    lang, files = detect_language(tmp_path)
    assert lang == "node"
    assert "package.json" in files


def test_detect_language_unknown_empty_dir(tmp_path: Path):
    lang, files = detect_language(tmp_path)
    assert lang == "unknown"
    assert files == []
