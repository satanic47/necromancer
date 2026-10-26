"""
core/taxonomy.py
Failure Taxonomy & Error Categorization Engine for Necromancer.

Parses build, installation, and test failure logs, classifies errors into
actionable categories, extracts root causes and suspect symbols, and produces
token-efficient summaries for LLM consumption.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class FailureCategory(str, Enum):
    SYNTAX_OBSOLETE = "SYNTAX_OBSOLETE"
    DEPRECATED_STDLIB_IMPORT = "DEPRECATED_STDLIB_IMPORT"
    MISSING_DEPENDENCY = "MISSING_DEPENDENCY"
    BUILD_SYSTEM_MISMATCH = "BUILD_SYSTEM_MISMATCH"
    TEST_ASSERTION_FAILURE = "TEST_ASSERTION_FAILURE"
    RUNTIME_CRASH = "RUNTIME_CRASH"
    UNKNOWN_FAILURE = "UNKNOWN_FAILURE"


@dataclass
class FailureItem:
    category: FailureCategory
    headline: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    suspect_target: Optional[str] = None
    suggested_action: Optional[str] = None
    snippet: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "category": self.category.value,
            "headline": self.headline,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "suspect_target": self.suspect_target,
            "suggested_action": self.suggested_action,
            "snippet": self.snippet,
        }


@dataclass
class FailureReport:
    total_failures: int
    category_counts: Dict[str, int]
    failures: List[FailureItem]

    def to_llm_prompt_summary(self, max_items: int = 5) -> str:
        """Formats a dense, token-frugal failure digest for the LLM agent prompt."""
        lines = [
            f"=== FAILURE TAXONOMY SUMMARY (Total: {self.total_failures}) ===",
            "Category breakdown: " + ", ".join(f"{k}: {v}" for k, v in self.category_counts.items() if v > 0),
            "",
            "Actionable Failure Targets:",
        ]

        for idx, item in enumerate(self.failures[:max_items], start=1):
            target_str = f" [Target: {item.suspect_target}]" if item.suspect_target else ""
            location_str = f" in {item.file_path}:{item.line_number}" if item.file_path else ""
            lines.append(f"{idx}. [{item.category.value}]{target_str}{location_str}")
            lines.append(f"   Reason: {item.headline}")
            if item.suggested_action:
                lines.append(f"   Hint: {item.suggested_action}")
            if item.snippet:
                lines.append("   Snippet:")
                for snip_line in item.snippet[-3:]:
                    lines.append(f"     | {snip_line}")
            lines.append("")

        if len(self.failures) > max_items:
            lines.append(f"... and {len(self.failures) - max_items} more errors truncated to save context.")

        return "\n".join(lines)


# Regex rules for diagnosing failures
PATTERNS = {
    "syntax_py2_print": re.compile(r"SyntaxError:\s*Missing parentheses in call to 'print'\.?"),
    "syntax_general": re.compile(r"SyntaxError:\s*(.+)"),
    "deprecated_collections": re.compile(
        r"cannot import name '(\w+)' from 'collections'\s*(?:\((?:.+)\))?", re.IGNORECASE
    ),
    "deprecated_imp": re.compile(r"No module named 'imp'", re.IGNORECASE),
    "missing_module": re.compile(
        r"(?:ModuleNotFoundError|ImportError):\s*No module named ['\"]?([a-zA-Z0-9_\.]+)['\"]?"
    ),
    "build_gcc": re.compile(r"error:\s*command ['\"]?gcc['\"]? failed with exit status \d+"),
    "build_pep517": re.compile(r"ERROR:\s*Failed to build installable wheels for.+"),
    "test_assertion": re.compile(r"AssertionError(?::\s*(.+))?"),
    "file_location": re.compile(r'File ["\']([^"\']+)["\'], line (\d+)(?:, in (.+))?'),
}


class FailureTaxonomyEngine:
    """Categorizes raw terminal / compiler outputs into structured taxonomy reports."""

    @classmethod
    def classify(cls, log_text: str) -> FailureReport:
        if not log_text or not log_text.strip():
            return FailureReport(total_failures=0, category_counts={}, failures=[])

        lines = log_text.splitlines()
        failures: List[FailureItem] = []
        category_counts: Dict[str, int] = {cat.value: 0 for cat in FailureCategory}

        # Sliding window / line inspection
        for i, line in enumerate(lines):
            line_strip = line.strip()

            # 1. Syntax: Python 2 print
            if PATTERNS["syntax_py2_print"].search(line_strip):
                file_path, line_no = cls._find_recent_location(lines, i)
                item = FailureItem(
                    category=FailureCategory.SYNTAX_OBSOLETE,
                    headline="Python 2 print statement without parentheses",
                    file_path=file_path,
                    line_number=line_no,
                    suggested_action="Convert `print statement` to `print()` function call.",
                    snippet=cls._extract_snippet(lines, i),
                )
                failures.append(item)
                category_counts[FailureCategory.SYNTAX_OBSOLETE.value] += 1
                continue

            # 2. Deprecated stdlib: collections.abc
            m_coll = PATTERNS["deprecated_collections"].search(line_strip)
            if m_coll:
                sub = m_coll.group(1)
                file_path, line_no = cls._find_recent_location(lines, i)
                item = FailureItem(
                    category=FailureCategory.DEPRECATED_STDLIB_IMPORT,
                    headline=f"Importing '{sub}' directly from 'collections' is deprecated in Python 3.3+ and removed in 3.10+",
                    file_path=file_path,
                    line_number=line_no,
                    suspect_target=f"collections.{sub}",
                    suggested_action=f"Update import from `collections.abc import {sub}` instead.",
                    snippet=cls._extract_snippet(lines, i),
                )
                failures.append(item)
                category_counts[FailureCategory.DEPRECATED_STDLIB_IMPORT.value] += 1
                continue

            # 3. Deprecated stdlib: imp
            if PATTERNS["deprecated_imp"].search(line_strip):
                file_path, line_no = cls._find_recent_location(lines, i)
                item = FailureItem(
                    category=FailureCategory.DEPRECATED_STDLIB_IMPORT,
                    headline="'imp' module removed in Python 3.12",
                    file_path=file_path,
                    line_number=line_no,
                    suspect_target="imp",
                    suggested_action="Replace `imp` usages with `importlib`.",
                    snippet=cls._extract_snippet(lines, i),
                )
                failures.append(item)
                category_counts[FailureCategory.DEPRECATED_STDLIB_IMPORT.value] += 1
                continue

            # 4. Missing dependency / module
            m_mod = PATTERNS["missing_module"].search(line_strip)
            if m_mod:
                mod_name = m_mod.group(1).split(".")[0]
                file_path, line_no = cls._find_recent_location(lines, i)
                item = FailureItem(
                    category=FailureCategory.MISSING_DEPENDENCY,
                    headline=f"Missing module '{mod_name}'",
                    file_path=file_path,
                    line_number=line_no,
                    suspect_target=mod_name,
                    suggested_action=f"Install dependency `{mod_name}` or pin historical version.",
                    snippet=cls._extract_snippet(lines, i),
                )
                failures.append(item)
                category_counts[FailureCategory.MISSING_DEPENDENCY.value] += 1
                continue

            # 5. Build system / gcc mismatch
            if PATTERNS["build_gcc"].search(line_strip) or PATTERNS["build_pep517"].search(line_strip):
                item = FailureItem(
                    category=FailureCategory.BUILD_SYSTEM_MISMATCH,
                    headline="C-extension compilation or wheel build failure (PEP 517 / GCC)",
                    suggested_action="Use pre-compiled binary wheel or pass `--no-build-isolation`.",
                    snippet=cls._extract_snippet(lines, i),
                )
                failures.append(item)
                category_counts[FailureCategory.BUILD_SYSTEM_MISMATCH.value] += 1
                continue

            # 6. Test assertion failure
            m_assert = PATTERNS["test_assertion"].search(line_strip)
            if m_assert:
                detail = m_assert.group(1) or "Assertion violated"
                file_path, line_no = cls._find_recent_location(lines, i)
                item = FailureItem(
                    category=FailureCategory.TEST_ASSERTION_FAILURE,
                    headline=f"Assertion failed: {detail}",
                    file_path=file_path,
                    line_number=line_no,
                    suggested_action="Review test logic or API behavioral difference.",
                    snippet=cls._extract_snippet(lines, i),
                )
                failures.append(item)
                category_counts[FailureCategory.TEST_ASSERTION_FAILURE.value] += 1
                continue

        # If failures detected, return
        if failures:
            return FailureReport(
                total_failures=len(failures),
                category_counts=category_counts,
                failures=failures,
            )

        # Fallback check for generic tracebacks or errors
        if "Traceback (most recent call last):" in log_text or "Error:" in log_text:
            return FailureReport(
                total_failures=1,
                category_counts={FailureCategory.RUNTIME_CRASH.value: 1},
                failures=[
                    FailureItem(
                        category=FailureCategory.RUNTIME_CRASH,
                        headline="Unhandled runtime exception or crash in process",
                        snippet=lines[-5:] if len(lines) >= 5 else lines,
                    )
                ],
            )

        return FailureReport(total_failures=0, category_counts=category_counts, failures=[])

    @classmethod
    def _find_recent_location(cls, lines: List[str], current_index: int) -> tuple[Optional[str], Optional[int]]:
        """Scans backwards up to 8 lines to find the nearest `File "...", line X`."""
        start = max(0, current_index - 8)
        for idx in range(current_index, start - 1, -1):
            m = PATTERNS["file_location"].search(lines[idx])
            if m:
                return m.group(1), int(m.group(2))
        return None, None

    @classmethod
    def _extract_snippet(cls, lines: List[str], current_index: int, window: int = 4) -> List[str]:
        """Extracts localized surrounding lines for targeted context."""
        start = max(0, current_index - window)
        end = min(len(lines), current_index + 2)
        return [l.strip() for l in lines[start:end] if l.strip()]
