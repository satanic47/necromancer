"""
tests/test_phase1.py
Unit tests validating Phase 1 modules: Exhume, TestIntegrityParser, and Sandbox configuration.
"""

import pytest
from core.test_integrity import TestIntegrityParser, ParsedSummary


def test_parse_pytest_output():
    raw_output = """
============================= test session starts ==============================
collected 10 items

test_app.py ........F.                                                   [100%]

=================================== FAILURES ===================================
__________________________________ test_fail ___________________________________
>       assert 1 == 2
E       assert 1 == 2

======================== 1 failed, 9 passed in 0.42s =========================
"""
    summary = TestIntegrityParser.parse_output(raw_output)
    assert summary.runner == "pytest"
    assert summary.passed == 9
    assert summary.failed == 1
    assert summary.total_run == 10


def test_parse_unittest_output():
    raw_output = """
test_one (tests.TestApp) ... ok
test_two (tests.TestApp) ... FAIL

======================================================================
FAIL: test_two (tests.TestApp)
----------------------------------------------------------------------
AssertionError: True is not false

----------------------------------------------------------------------
Ran 8 tests in 0.015s

FAILED (failures=1)
"""
    summary = TestIntegrityParser.parse_output(raw_output)
    assert summary.runner == "unittest"
    assert summary.total_run == 8
    assert summary.passed == 7
    assert summary.failed == 1


def test_evaluate_integrity_pass():
    baseline = ParsedSummary(runner="pytest", total_run=5, passed=3, failed=2)
    candidate = ParsedSummary(runner="pytest", total_run=5, passed=5, failed=0)

    assessment = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert assessment.is_valid is True
    assert assessment.delta == 2


def test_evaluate_integrity_regression():
    baseline = ParsedSummary(runner="pytest", total_run=5, passed=4, failed=1)
    # Regression: test deleted
    candidate = ParsedSummary(runner="pytest", total_run=3, passed=3, failed=0)

    assessment = TestIntegrityParser.evaluate_integrity(baseline, candidate)
    assert assessment.is_valid is False
    assert "total tests decreased" in assessment.reason
