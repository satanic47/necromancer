"""
core/serp_crawler.py
SerpApi Historical Archive & Dependency Migration Grounding Engine.

Discovers historical PyPI package mirrors, deprecated module replacements,
and PEP syntax migration guides to ground the LLM agent during test repair.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class MigrationGuidance:
    package_or_module: str
    issue_type: str  # "DEPRECATED_MODULE" | "MISSING_WHEEL" | "SYNTAX_CHANGE"
    recommended_fix: str
    suggested_import: str
    code_snippet: str
    source_url: str
    confidence: float


class SerpApiMigrationCrawler:
    """
    Queries SerpApi to discover legacy package mirrors and syntax modernization paths.
    """

    # Curated Fast-Grounding Cache for Common Legacy Bitrot Archetypes
    CURATED_MIGRATIONS: Dict[str, Dict[str, str]] = {
        "imp": {
            "issue_type": "DEPRECATED_MODULE",
            "recommended_fix": "Replace legacy 'imp' with modern 'importlib' or 'importlib.util'.",
            "suggested_import": "import importlib.util",
            "code_snippet": "spec = importlib.util.spec_from_file_location(name, path)\nmod = importlib.util.module_from_spec(spec)\nspec.loader.exec_module(mod)",
            "source_url": "https://docs.python.org/3/whatsnew/3.12.html#removed",
        },
        "collections.Mapping": {
            "issue_type": "SYNTAX_CHANGE",
            "recommended_fix": "Import abstract collections from 'collections.abc' instead of 'collections'.",
            "suggested_import": "from collections.abc import Mapping, MutableMapping, Sequence",
            "code_snippet": "try:\n    from collections.abc import Mapping\nexcept ImportError:\n    from collections import Mapping",
            "source_url": "https://docs.python.org/3/library/collections.abc.html",
        },
        "urllib2": {
            "issue_type": "DEPRECATED_MODULE",
            "recommended_fix": "Split Python 2 urllib2 into urllib.request and urllib.error.",
            "suggested_import": "import urllib.request\nimport urllib.error",
            "code_snippet": "try:\n    import urllib.request as urllib2\nexcept ImportError:\n    import urllib2",
            "source_url": "https://docs.python.org/3/library/urllib.request.html",
        },
        "nose": {
            "issue_type": "DEPRECATED_RUNNER",
            "recommended_fix": "Migrate dead 'nose' test runner to modern 'pytest'.",
            "suggested_import": "import pytest",
            "code_snippet": "# Replace nose.tools assert_equals with standard assert or pytest.raises",
            "source_url": "https://docs.pytest.org/en/stable/how-to/nose.html",
        },
        "six": {
            "issue_type": "TRANSITIONAL_SHIM",
            "recommended_fix": "Retain 'six' for Python 2/3 cross-compatibility or modernize to native builtins.",
            "suggested_import": "import six",
            "code_snippet": "isinstance(val, six.string_types) -> isinstance(val, str)",
            "source_url": "https://pypi.org/project/six/",
        },
        "cgi.escape": {
            "issue_type": "DEPRECATED_MODULE",
            "recommended_fix": "Replace removed 'cgi.escape' with 'html.escape'.",
            "suggested_import": "import html",
            "code_snippet": "html.escape(user_input)",
            "source_url": "https://docs.python.org/3/library/html.html#html.escape",
        },
    }

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("SERPAPI_API_KEY", "")

    def search_migration(
        self,
        module_or_package: str,
        error_context: str = "",
    ) -> MigrationGuidance:
        """
        Searches SerpApi for migration guides or historical mirror archives.
        Falls back to the curated knowledge cache when API key is unconfigured or offline.
        """
        clean_key = module_or_package.strip()

        # Check curated cache first for instant deterministic grounding
        for k, data in self.CURATED_MIGRATIONS.items():
            if k.lower() in clean_key.lower() or clean_key.lower() in k.lower():
                return MigrationGuidance(
                    package_or_module=k,
                    issue_type=data["issue_type"],
                    recommended_fix=data["recommended_fix"],
                    suggested_import=data["suggested_import"],
                    code_snippet=data["code_snippet"],
                    source_url=data["source_url"],
                    confidence=0.98,
                )

        # If live SerpApi key is available, query Google via SerpApi
        if self.api_key:
            try:
                query = f"Python 3 migration {clean_key} replaced deprecated how to fix"
                params = urllib.parse.urlencode({
                    "q": query,
                    "api_key": self.api_key,
                    "engine": "google",
                    "num": 3,
                })
                url = f"https://serpapi.com/search?{params}"
                req = urllib.request.Request(url, headers={"User-Agent": "Necromancer-Agent/1.0"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    organic = data.get("organic_results", [])
                    if organic:
                        first = organic[0]
                        title = first.get("title", "")
                        snippet = first.get("snippet", "")
                        link = first.get("link", "https://docs.python.org")

                        return MigrationGuidance(
                            package_or_module=clean_key,
                            issue_type="WEB_SEARCH_GROUNDED",
                            recommended_fix=f"Discovered via SerpApi: {title}. {snippet[:150]}...",
                            suggested_import=f"# Consult {link}",
                            code_snippet=f"# SerpApi Grounding for {clean_key}\n# Reference: {link}",
                            source_url=link,
                            confidence=0.85,
                        )
            except Exception:
                pass

        # Fallback guidance
        return MigrationGuidance(
            package_or_module=clean_key,
            issue_type="AUTOMATED_HEURISTIC",
            recommended_fix=f"Check Python 3 deprecation migration path for '{clean_key}'. Verify pyproject.toml pin.",
            suggested_import=f"import {clean_key}",
            code_snippet=f"# Modernize import or pin legacy version in requirements.txt",
            source_url="https://docs.python.org/3/whatsnew/",
            confidence=0.70,
        )
