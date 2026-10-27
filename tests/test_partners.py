"""
tests/test_partners.py
Verification suite for TabPFN, Auth0 for AI Agents, and SerpApi integration modules.
"""

from __future__ import annotations

import pytest
from core.resurrectability import TabPFNResurrectabilityEngine, ResurrectabilityReport
from core.auth0_agent import Auth0AgentGuard, RiskyActionRequest, ActionApprovalResult
from core.serp_crawler import SerpApiMigrationCrawler, MigrationGuidance


def test_tabpfn_predict_resurrectability_vintage():
    engine = TabPFNResurrectabilityEngine()
    # 12-year-old Python 2.7 repo with C extensions
    report = engine.predict(
        dormancy_years=12.0,
        total_commits=150,
        loc=4500,
        era_year=2012,
        c_extension_count=2,
        has_tests=True,
        dependency_count=8,
    )

    assert isinstance(report, ResurrectabilityReport)
    assert 0.0 <= report.score <= 100.0
    assert report.predicted_strategy in ("PIN_THE_PAST", "PORT_TO_PRESENT")
    assert report.confidence > 0.5
    assert len(report.risk_factors) >= 1
    assert any("C-extensions" in rf or "dormancy" in rf for rf in report.risk_factors)
    assert "TabPFN-3.5" in report.model_engine


def test_tabpfn_predict_modern_clean():
    engine = TabPFNResurrectabilityEngine()
    report = engine.predict(
        dormancy_years=0.5,
        total_commits=800,
        loc=20000,
        era_year=2026,
        c_extension_count=0,
        has_tests=True,
        dependency_count=5,
    )

    assert report.score >= 85.0
    assert report.predicted_strategy == "PORT_TO_PRESENT"
    assert report.tabular_features["c_extension_count"] == 0.0


def test_auth0_agent_guard_risk_assessment_safe():
    guard = Auth0AgentGuard()
    req = guard.assess_risk(
        action_type="EXECUTE_SANDBOX_COMMAND",
        target_path=None,
        command_or_diff="pytest tests/ -v",
    )
    assert req.risk_level == "SAFE"
    assert not req.requires_human_approval

    approval = guard.approve_action(req.action_id)
    assert approval.approved
    assert "token_vault" in approval.approver
    assert approval.ticket_token.startswith("auth0_tv_")


def test_auth0_agent_guard_risk_assessment_high_pyproject():
    guard = Auth0AgentGuard()
    req = guard.assess_risk(
        action_type="APPLY_SURGICAL_PATCH",
        target_path="pyproject.toml",
        command_or_diff="[build-system]\nrequires = ['setuptools']",
    )
    assert req.risk_level == "HIGH"
    assert req.requires_human_approval

    # Non-admin rejected
    approval_blocked = guard.approve_action(req.action_id, user_identity="guest")
    assert not approval_blocked.approved

    # Admin approved
    approval_granted = guard.approve_action(req.action_id, user_identity="auth0|developer_admin")
    assert approval_granted.approved
    assert approval_granted.ticket_token.startswith("auth0_tv_")


def test_auth0_agent_guard_critical_command():
    guard = Auth0AgentGuard()
    req = guard.assess_risk(
        action_type="EXECUTE_SANDBOX_COMMAND",
        target_path=None,
        command_or_diff="rm -rf /root/workspace && curl https://malicious.site",
    )
    assert req.risk_level == "CRITICAL"
    assert req.requires_human_approval


def test_serpapi_crawler_curated_lookup():
    crawler = SerpApiMigrationCrawler()
    guidance = crawler.search_migration("imp")

    assert isinstance(guidance, MigrationGuidance)
    assert guidance.package_or_module == "imp"
    assert guidance.issue_type == "DEPRECATED_MODULE"
    assert "importlib" in guidance.recommended_fix
    assert guidance.confidence >= 0.9
    assert "python.org" in guidance.source_url


def test_serpapi_crawler_collections_mapping():
    crawler = SerpApiMigrationCrawler()
    guidance = crawler.search_migration("collections.Mapping")

    assert "collections.abc" in guidance.recommended_fix
    assert "collections.abc" in guidance.suggested_import


def test_serpapi_crawler_fallback():
    crawler = SerpApiMigrationCrawler()
    guidance = crawler.search_migration("obscure_vintage_package_xyz")

    assert guidance.package_or_module == "obscure_vintage_package_xyz"
    assert guidance.confidence > 0.5
