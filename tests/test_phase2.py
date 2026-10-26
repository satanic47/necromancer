"""
tests/test_phase2.py
Comprehensive Verification Suite for Phase 2:
- Era Detection (10 tests)
- Failure Taxonomy Classification & LLM Digest (12 tests)
- Repo Map AST Extraction & Blueprints (8 tests)
Total: 30 Unit Tests
"""

from datetime import datetime
from pathlib import Path
import pytest

from core.era_detect import EraDetector, EraProfile
from core.taxonomy import (
    FailureCategory,
    FailureItem,
    FailureReport,
    FailureTaxonomyEngine,
)
from core.repo_map import (
    ClassSignature,
    FunctionSignature,
    ModuleBlueprint,
    RepoMap,
    RepoMapper,
)


# ============================================================================
# 1. Era Detection Tests (10 tests)
# ============================================================================

def test_era_detect_py2_commit_year(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2013, 5, 20),
        language="python",
    )
    assert profile.recommended_runtime_version == "2.7"
    assert profile.docker_base_image == "python:2.7-slim"
    assert "--no-build-isolation" in profile.compatibility_flags


def test_era_detect_py2_print_syntax(tmp_path: Path):
    file = tmp_path / "legacy.py"
    file.write_text('print "Hello legacy world"\n')
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2020, 1, 1),
        language="python",
    )
    assert profile.recommended_runtime_version == "2.7"
    assert any("Python 2 print statement" in ind for ind in profile.indicators)


def test_era_detect_py2_except_syntax(tmp_path: Path):
    file = tmp_path / "exceptions.py"
    file.write_text("try:\n    pass\nexcept ValueError, err:\n    pass\n")
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2022, 1, 1),
        language="python",
    )
    assert profile.recommended_runtime_version == "2.7"
    assert any("Python 2 comma-except" in ind for ind in profile.indicators)


def test_era_detect_py35_transition(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2017, 8, 14),
        language="python",
    )
    assert profile.recommended_runtime_version == "3.6"
    assert "Early Python 3 Transition" in profile.era_name


def test_era_detect_py38_mature(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2020, 3, 10),
        language="python",
    )
    assert profile.recommended_runtime_version == "3.8"
    assert "Mature Python 3" in profile.era_name


def test_era_detect_py311_modern(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2024, 6, 1),
        language="python",
    )
    assert profile.recommended_runtime_version == "3.11"
    assert "Modern Python" in profile.era_name


def test_era_detect_node_legacy_012(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2013, 2, 1),
        language="node",
    )
    assert profile.recommended_runtime_version == "0.12"
    assert profile.docker_base_image == "node:0.12-slim"


def test_era_detect_node_lts_8_10(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2017, 10, 1),
        language="node",
    )
    assert profile.recommended_runtime_version == "10"
    assert profile.docker_base_image == "node:10-slim"


def test_era_detect_node_modern(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2025, 1, 1),
        language="node",
    )
    assert profile.recommended_runtime_version == "20"


def test_era_detect_unknown_language(tmp_path: Path):
    profile = EraDetector.detect_era(
        repo_path=tmp_path,
        last_commit_date=datetime(2015, 1, 1),
        language="haskell",
    )
    assert profile.language == "haskell"
    assert profile.docker_base_image == "alpine:3.18"


# ============================================================================
# 2. Failure Taxonomy Tests (12 tests)
# ============================================================================

def test_taxonomy_empty_logs():
    report = FailureTaxonomyEngine.classify("")
    assert report.total_failures == 0
    assert len(report.failures) == 0


def test_taxonomy_py2_print_error():
    log = """
  File "legacy/cli.py", line 42
    print "Starting worker..."
          ^
SyntaxError: Missing parentheses in call to 'print'. Did you mean print(...)?
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 1
    item = report.failures[0]
    assert item.category == FailureCategory.SYNTAX_OBSOLETE
    assert item.file_path == "legacy/cli.py"
    assert item.line_number == 42
    assert "print()" in item.suggested_action


def test_taxonomy_deprecated_collections_mapping():
    log = """
Traceback (most recent call last):
  File "app/server.py", line 12, in <module>
    from collections import Mapping
ImportError: cannot import name 'Mapping' from 'collections' (/usr/lib/python3.10/collections/__init__.py)
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 1
    item = report.failures[0]
    assert item.category == FailureCategory.DEPRECATED_STDLIB_IMPORT
    assert item.suspect_target == "collections.Mapping"
    assert item.file_path == "app/server.py"
    assert item.line_number == 12
    assert "collections.abc" in item.suggested_action


def test_taxonomy_deprecated_imp_module():
    log = """
Traceback (most recent call last):
  File "engine.py", line 4, in <module>
    import imp
ModuleNotFoundError: No module named 'imp'
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures >= 1
    # Check that either DEPRECATED_STDLIB_IMPORT or MISSING_DEPENDENCY is flagged
    categories = [f.category for f in report.failures]
    assert (
        FailureCategory.DEPRECATED_STDLIB_IMPORT in categories
        or FailureCategory.MISSING_DEPENDENCY in categories
    )


def test_taxonomy_missing_dependency():
    log = """
Traceback (most recent call last):
  File "tests/test_api.py", line 5, in <module>
    import requests
ModuleNotFoundError: No module named 'requests'
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 1
    item = report.failures[0]
    assert item.category == FailureCategory.MISSING_DEPENDENCY
    assert item.suspect_target == "requests"
    assert item.file_path == "tests/test_api.py"
    assert item.line_number == 5


def test_taxonomy_gcc_compilation_failure():
    log = """
building 'legacy_c_ext' extension
x86_64-linux-gnu-gcc -pthread -Wno-unused-result -c ext.c -o build/ext.o
ext.c:10:20: fatal error: Python.h: No such file or directory
error: command 'gcc' failed with exit status 1
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 1
    item = report.failures[0]
    assert item.category == FailureCategory.BUILD_SYSTEM_MISMATCH
    assert "PEP 517 / GCC" in item.headline


def test_taxonomy_pep517_build_wheel_error():
    log = """
Building wheels for collected packages: old-crypto
  Building wheel for old-crypto (pyproject.toml) ... error
ERROR: Failed to build installable wheels for one or more PEP 517 projects
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 1
    assert report.failures[0].category == FailureCategory.BUILD_SYSTEM_MISMATCH


def test_taxonomy_assertion_failure():
    log = """
Traceback (most recent call last):
  File "tests/test_calc.py", line 18, in test_add
    assert add(2, 2) == 5
AssertionError: assert 4 == 5
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 1
    item = report.failures[0]
    assert item.category == FailureCategory.TEST_ASSERTION_FAILURE
    assert item.file_path == "tests/test_calc.py"
    assert item.line_number == 18
    assert "assert 4 == 5" in item.headline


def test_taxonomy_generic_runtime_crash():
    log = """
Traceback (most recent call last):
  File "main.py", line 99, in execute
    raise RuntimeError("Corrupted memory buffer state")
RuntimeError: Corrupted memory buffer state
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures >= 1
    assert report.failures[0].category == FailureCategory.RUNTIME_CRASH


def test_taxonomy_multiple_errors_in_one_run():
    log = """
  File "a.py", line 10
    print "hello"
SyntaxError: Missing parentheses in call to 'print'.
  File "b.py", line 2
ModuleNotFoundError: No module named 'flask'
"""
    report = FailureTaxonomyEngine.classify(log)
    assert report.total_failures == 2
    assert report.category_counts[FailureCategory.SYNTAX_OBSOLETE.value] == 1
    assert report.category_counts[FailureCategory.MISSING_DEPENDENCY.value] == 1


def test_taxonomy_llm_prompt_summary_formatting():
    item = FailureItem(
        category=FailureCategory.SYNTAX_OBSOLETE,
        headline="Missing parentheses in call to 'print'",
        file_path="src/cli.py",
        line_number=33,
        suggested_action="Convert to print()",
        snippet=['print "deprecated"'],
    )
    report = FailureReport(
        total_failures=1,
        category_counts={FailureCategory.SYNTAX_OBSOLETE.value: 1},
        failures=[item],
    )
    prompt_str = report.to_llm_prompt_summary()
    assert "FAILURE TAXONOMY SUMMARY" in prompt_str
    assert "src/cli.py:33" in prompt_str
    assert "Convert to print()" in prompt_str


def test_taxonomy_llm_prompt_summary_truncation():
    items = [
        FailureItem(category=FailureCategory.MISSING_DEPENDENCY, headline=f"Missing module {i}")
        for i in range(10)
    ]
    report = FailureReport(
        total_failures=10,
        category_counts={FailureCategory.MISSING_DEPENDENCY.value: 10},
        failures=items,
    )
    prompt_str = report.to_llm_prompt_summary(max_items=3)
    assert "more errors truncated" in prompt_str


# ============================================================================
# 3. Repo Map Tests (8 tests)
# ============================================================================

def test_repo_map_parse_classes_and_methods(tmp_path: Path):
    code = '''
class Worker(object):
    """Worker daemon process."""
    def __init__(self, name, port=8080):
        self.name = name

    def execute(self, payload):
        return True
'''
    (tmp_path / "worker.py").write_text(code)
    rmap = RepoMapper.generate_map(tmp_path)
    assert rmap.total_files == 1
    mod = rmap.modules[0]
    assert mod.rel_path == "worker.py"
    assert len(mod.classes) == 1
    cls = mod.classes[0]
    assert cls.name == "Worker"
    assert cls.bases == ["object"]
    assert cls.docstring == "Worker daemon process."
    method_names = [m.name for m in cls.methods]
    assert "execute" in method_names
    assert "__init__" in method_names


def test_repo_map_parse_functions_and_async(tmp_path: Path):
    code = """
def sync_handler(a, b):
    return a + b

async def async_handler(request, timeout):
    return await request.json()
"""
    (tmp_path / "handlers.py").write_text(code)
    rmap = RepoMapper.generate_map(tmp_path)
    mod = rmap.modules[0]
    assert len(mod.functions) == 2
    f_sync = next(f for f in mod.functions if f.name == "sync_handler")
    f_async = next(f for f in mod.functions if f.name == "async_handler")
    assert f_sync.is_async is False
    assert f_sync.args == ["a", "b"]
    assert f_async.is_async is True
    assert f_async.args == ["request", "timeout"]


def test_repo_map_parse_imports(tmp_path: Path):
    code = """
import os
import sys
from datetime import datetime
from collections import OrderedDict
"""
    (tmp_path / "main.py").write_text(code)
    rmap = RepoMapper.generate_map(tmp_path)
    mod = rmap.modules[0]
    assert "os" in mod.imports
    assert "sys" in mod.imports
    assert "datetime.datetime" in mod.imports
    assert "collections.OrderedDict" in mod.imports


def test_repo_map_identifies_test_file(tmp_path: Path):
    (tmp_path / "test_api.py").write_text("def test_simple(): assert True")
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    (tests_dir / "suite.py").write_text("def run(): pass")

    rmap = RepoMapper.generate_map(tmp_path)
    test_mods = [m for m in rmap.modules if m.is_test_file]
    assert len(test_mods) == 2


def test_repo_map_ignores_hidden_and_virtualenv_dirs(tmp_path: Path):
    (tmp_path / "app.py").write_text("def run(): pass")
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    (git_dir / "hook.py").write_text("print(1)")
    venv_dir = tmp_path / ".venv"
    venv_dir.mkdir()
    (venv_dir / "lib.py").write_text("print(2)")

    rmap = RepoMapper.generate_map(tmp_path)
    assert rmap.total_files == 1
    assert rmap.modules[0].rel_path == "app.py"


def test_repo_map_handles_legacy_py2_syntax_gracefully(tmp_path: Path):
    # Python 2 print will raise SyntaxError in Python 3 ast.parse
    (tmp_path / "retro.py").write_text('print "no parens"')
    rmap = RepoMapper.generate_map(tmp_path)
    assert rmap.total_files == 1
    mod = rmap.modules[0]
    assert "<Legacy Python 2 Syntax" in mod.imports[0]


def test_repo_map_condensed_prompt_outline(tmp_path: Path):
    (tmp_path / "service.py").write_text("""
import math

class Calculator:
    def compute(self, x, y):
        return x * y
""")
    rmap = RepoMapper.generate_map(tmp_path)
    outline = rmap.to_condensed_prompt_outline(max_chars=2000)
    assert "REPOSITORY SKELETON MAP" in outline
    assert "service.py" in outline
    assert "class Calculator" in outline
    assert "compute(self, x, y)" in outline


def test_repo_map_outline_truncation(tmp_path: Path):
    (tmp_path / "big.py").write_text("\n".join(f"def func_{i}(): pass" for i in range(100)))
    rmap = RepoMapper.generate_map(tmp_path)
    outline = rmap.to_condensed_prompt_outline(max_chars=150)
    assert len(outline) <= 300
    assert "Remaining repo map truncated" in outline
