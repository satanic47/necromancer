"""
Necromancer Core Engine
Resurrecting dormant open-source repositories and honoring their creators.
"""

from core.exhume import ExhumationEngine, RepositoryTombstone, detect_language
from core.sandbox import DockerSandbox, SandboxResult, SandboxSecurityConfig
from core.test_integrity import IntegrityAssessment, ParsedSummary, TestIntegrityParser
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

__version__ = "0.2.0"

__all__ = [
    "ExhumationEngine",
    "RepositoryTombstone",
    "detect_language",
    "DockerSandbox",
    "SandboxResult",
    "SandboxSecurityConfig",
    "IntegrityAssessment",
    "ParsedSummary",
    "TestIntegrityParser",
    "EraDetector",
    "EraProfile",
    "FailureCategory",
    "FailureItem",
    "FailureReport",
    "FailureTaxonomyEngine",
    "ClassSignature",
    "FunctionSignature",
    "ModuleBlueprint",
    "RepoMap",
    "RepoMapper",
]
