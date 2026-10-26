"""
core/era_detect.py
Historical Era Detection Engine for Necromancer.

Analyzes dormant repository artifacts, commit timestamps, and legacy AST/syntax patterns
to deduce the precise runtime era, recommending historical Docker base images,
compiler/interpreter versions, and historical package index configurations.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


@dataclass
class EraProfile:
    """Represents the historical runtime profile for a dormant codebase."""
    year: int
    era_name: str
    language: str
    recommended_runtime_version: str
    docker_base_image: str
    compatibility_flags: List[str] = field(default_factory=list)
    pypi_index_url: Optional[str] = None
    indicators: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "year": self.year,
            "era_name": self.era_name,
            "language": self.language,
            "recommended_runtime_version": self.recommended_runtime_version,
            "docker_base_image": self.docker_base_image,
            "compatibility_flags": self.compatibility_flags,
            "pypi_index_url": self.pypi_index_url,
            "indicators": self.indicators,
        }


# Signature patterns indicative of specific runtime eras
PY2_PRINT_PATTERN = re.compile(r'^\s*print\s+["\']', re.MULTILINE)
PY2_EXCEPT_COMMA_PATTERN = re.compile(r'^\s*except\s+\w+\s*,\s*\w+\s*:', re.MULTILINE)
PY_FUTURE_IMPORT_PATTERN = re.compile(r'^\s*from\s+__future__\s+import\s+', re.MULTILINE)
PY3_YIELD_FROM_PATTERN = re.compile(r'\byield\s+from\b')
PY3_ASYNC_DEF_PATTERN = re.compile(r'^\s*async\s+def\s+', re.MULTILINE)
PY3_MATCH_CASE_PATTERN = re.compile(r'^\s*match\s+\w+:', re.MULTILINE)


class EraDetector:
    """Inspects file contents and timestamps to classify repository vintage."""

    @classmethod
    def scan_python_indicators(cls, repo_path: Path) -> List[str]:
        """Scans representative python files for syntax markers."""
        indicators: List[str] = []
        py_files = list(repo_path.glob("*.py")) + list(repo_path.glob("**/*.py"))[:20]

        has_py2_print = False
        has_py2_except = False
        has_future_import = False
        has_async_def = False
        has_match_case = False

        for py_file in py_files:
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            if not has_py2_print and PY2_PRINT_PATTERN.search(content):
                has_py2_print = True
                indicators.append(f"Python 2 print statement in {py_file.name}")

            if not has_py2_except and PY2_EXCEPT_COMMA_PATTERN.search(content):
                has_py2_except = True
                indicators.append(f"Python 2 comma-except syntax in {py_file.name}")

            if not has_future_import and PY_FUTURE_IMPORT_PATTERN.search(content):
                has_future_import = True
                indicators.append(f"__future__ compatibility imports in {py_file.name}")

            if not has_async_def and PY3_ASYNC_DEF_PATTERN.search(content):
                has_async_def = True
                indicators.append(f"Modern async/await syntax in {py_file.name}")

            if not has_match_case and PY3_MATCH_CASE_PATTERN.search(content):
                has_match_case = True
                indicators.append(f"Python 3.10+ match/case syntax in {py_file.name}")

        return indicators

    @classmethod
    def detect_era(
        cls,
        repo_path: Path,
        last_commit_date: Optional[datetime] = None,
        language: str = "python",
    ) -> EraProfile:
        """Determines the era profile from commit date, build files, and syntax indicators."""
        now = datetime.now()
        commit_year = last_commit_date.year if last_commit_date else now.year
        indicators: List[str] = []

        if last_commit_date:
            indicators.append(f"Last commit recorded in {commit_year}")

        if language == "python":
            syntax_indicators = cls.scan_python_indicators(repo_path)
            indicators.extend(syntax_indicators)

            # Check if pyproject.toml exists (PEP 518/621 - modern)
            if (repo_path / "pyproject.toml").exists():
                indicators.append("pyproject.toml present (modern packaging)")

            # Check setup.py
            setup_py = repo_path / "setup.py"
            if setup_py.exists():
                indicators.append("Legacy setup.py detected")

            # Classification logic
            has_py2_syntax = any("Python 2" in ind for ind in indicators)
            has_match_case = any("Python 3.10+" in ind for ind in indicators)
            has_async = any("Modern async" in ind for ind in indicators)

            if has_py2_syntax or commit_year <= 2014:
                return EraProfile(
                    year=commit_year,
                    era_name="Python 2.7 Sunset Era (Legacy)",
                    language="python",
                    recommended_runtime_version="2.7",
                    docker_base_image="python:2.7-slim",
                    compatibility_flags=[
                        "--no-build-isolation",
                        "--use-deprecated=legacy-resolver",
                    ],
                    indicators=indicators,
                )
            elif commit_year <= 2018:
                return EraProfile(
                    year=commit_year,
                    era_name="Early Python 3 Transition Era (Py3.5-3.6)",
                    language="python",
                    recommended_runtime_version="3.6",
                    docker_base_image="python:3.6-slim",
                    compatibility_flags=["--no-build-isolation"],
                    indicators=indicators,
                )
            elif commit_year <= 2021 and not has_match_case:
                return EraProfile(
                    year=commit_year,
                    era_name="Mature Python 3 Era (Py3.8)",
                    language="python",
                    recommended_runtime_version="3.8",
                    docker_base_image="python:3.8-slim",
                    compatibility_flags=[],
                    indicators=indicators,
                )
            else:
                return EraProfile(
                    year=commit_year,
                    era_name="Modern Python Era (Py3.10+)",
                    language="python",
                    recommended_runtime_version="3.11",
                    docker_base_image="python:3.11-slim",
                    compatibility_flags=[],
                    indicators=indicators,
                )

        elif language == "node":
            # Node era evaluation
            pkg_json = repo_path / "package.json"
            if pkg_json.exists():
                indicators.append("package.json detected")

            if commit_year <= 2014:
                return EraProfile(
                    year=commit_year,
                    era_name="Legacy Node.js Era (0.10/0.12)",
                    language="node",
                    recommended_runtime_version="0.12",
                    docker_base_image="node:0.12-slim",
                    compatibility_flags=["--legacy-peer-deps"],
                    indicators=indicators,
                )
            elif commit_year <= 2018:
                return EraProfile(
                    year=commit_year,
                    era_name="Early Node LTS Era (Node 8-10)",
                    language="node",
                    recommended_runtime_version="10",
                    docker_base_image="node:10-slim",
                    compatibility_flags=["--legacy-peer-deps"],
                    indicators=indicators,
                )
            else:
                return EraProfile(
                    year=commit_year,
                    era_name="Modern Node.js Era (Node 18/20)",
                    language="node",
                    recommended_runtime_version="20",
                    docker_base_image="node:20-slim",
                    compatibility_flags=[],
                    indicators=indicators,
                )

        # Fallback for unknown language
        return EraProfile(
            year=commit_year,
            era_name="Generic Legacy Era",
            language=language,
            recommended_runtime_version="unknown",
            docker_base_image="alpine:3.18",
            compatibility_flags=[],
            indicators=indicators,
        )
