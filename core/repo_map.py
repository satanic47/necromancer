"""
core/repo_map.py
Repository Skeleton & AST Mapper for Necromancer.

Extracts top-level declarations, class hierarchies, method signatures,
docstrings, and dependencies from dormant repositories using Python's stdlib AST.
Produces a compressed repository blueprint suitable for LLM system prompts.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set


@dataclass
class FunctionSignature:
    name: str
    args: List[str]
    is_async: bool = False
    docstring: Optional[str] = None
    line_number: int = 1


@dataclass
class ClassSignature:
    name: str
    bases: List[str]
    methods: List[FunctionSignature] = field(default_factory=list)
    docstring: Optional[str] = None
    line_number: int = 1


@dataclass
class ModuleBlueprint:
    rel_path: str
    imports: List[str] = field(default_factory=list)
    classes: List[ClassSignature] = field(default_factory=list)
    functions: List[FunctionSignature] = field(default_factory=list)
    is_test_file: bool = False


@dataclass
class RepoMap:
    root_path: str
    total_files: int
    modules: List[ModuleBlueprint] = field(default_factory=list)

    def to_condensed_prompt_outline(self, max_chars: int = 6000) -> str:
        """Generates a compressed structural representation for LLM context."""
        lines = [
            f"=== REPOSITORY SKELETON MAP ({self.total_files} modules) ===",
        ]

        # Put test files at the bottom or mark them
        for mod in self.modules:
            prefix = "[TEST] " if mod.is_test_file else ""
            lines.append(f"\n* {prefix}{mod.rel_path}:")
            if mod.imports:
                condensed_imports = ", ".join(mod.imports[:6])
                if len(mod.imports) > 6:
                    condensed_imports += f" (+{len(mod.imports) - 6} more)"
                lines.append(f"  Imports: {condensed_imports}")

            for cls in mod.classes:
                base_str = f"({', '.join(cls.bases)})" if cls.bases else ""
                lines.append(f"  class {cls.name}{base_str}:")
                for method in cls.methods[:8]:
                    args_str = ", ".join(method.args)
                    async_prefix = "async " if method.is_async else ""
                    lines.append(f"    {async_prefix}def {method.name}({args_str})")
                if len(cls.methods) > 8:
                    lines.append(f"    ... (+{len(cls.methods) - 8} methods)")

            for fn in mod.functions[:10]:
                args_str = ", ".join(fn.args)
                async_prefix = "async " if fn.is_async else ""
                lines.append(f"  {async_prefix}def {fn.name}({args_str})")
            if (fn_count := len(mod.functions)) > 10:
                lines.append(f"  ... (+{fn_count - 10} functions)")

        full_text = "\n".join(lines)
        if len(full_text) > max_chars:
            return full_text[:max_chars] + f"\n\n[... Remaining repo map truncated to stay within {max_chars} chars ...]"
        return full_text


IGNORE_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".tox",
    "venv",
    ".venv",
    "env",
    ".env",
    "node_modules",
    "build",
    "dist",
    ".eggs",
}


class RepoMapper:
    """Walks the repository and parses syntax trees to extract public interfaces."""

    @classmethod
    def generate_map(cls, repo_path: Path, max_files: int = 50) -> RepoMap:
        repo_path = repo_path.resolve()
        modules: List[ModuleBlueprint] = []

        all_py_files = []
        for p in repo_path.rglob("*.py"):
            parts = set(p.relative_to(repo_path).parts)
            if not parts.intersection(IGNORE_DIRS):
                all_py_files.append(p)

        # Prioritize root and top modules, limit to max_files
        all_py_files = sorted(all_py_files, key=lambda x: (len(x.parts), x.name))[:max_files]

        for py_file in all_py_files:
            rel_path = str(py_file.relative_to(repo_path)).replace("\\", "/")
            blueprint = cls._parse_python_module(py_file, rel_path)
            if blueprint:
                modules.append(blueprint)

        return RepoMap(
            root_path=str(repo_path),
            total_files=len(modules),
            modules=modules,
        )

    @classmethod
    def _parse_python_module(cls, file_path: Path, rel_path: str) -> Optional[ModuleBlueprint]:
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source, filename=str(file_path))
        except SyntaxError:
            # If modern ast fails due to Python 2 syntax, return stub
            return ModuleBlueprint(
                rel_path=rel_path,
                imports=["<Legacy Python 2 Syntax - AST unparseable in modern Python>"],
                is_test_file="test" in rel_path.lower(),
            )
        except Exception:
            return None

        imports: List[str] = []
        classes: List[ClassSignature] = []
        functions: List[FunctionSignature] = []
        is_test = "test" in rel_path.lower() or file_path.name.startswith("test_")

        for node in tree.body:
            # Imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                for alias in node.names:
                    imports.append(f"{mod}.{alias.name}")

            # Classes
            elif isinstance(node, ast.ClassDef):
                bases = []
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        bases.append(base.id)
                    elif isinstance(base, ast.Attribute):
                        bases.append(f"{cls._get_attribute_name(base)}")

                methods: List[FunctionSignature] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        methods.append(cls._extract_function_signature(item))

                doc = ast.get_docstring(node)
                classes.append(
                    ClassSignature(
                        name=node.name,
                        bases=bases,
                        methods=methods,
                        docstring=doc.splitlines()[0] if doc else None,
                        line_number=node.lineno,
                    )
                )

            # Top-level Functions
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                functions.append(cls._extract_function_signature(node))

        return ModuleBlueprint(
            rel_path=rel_path,
            imports=imports,
            classes=classes,
            functions=functions,
            is_test_file=is_test,
        )

    @classmethod
    def _extract_function_signature(cls, node: ast.FunctionDef | ast.AsyncFunctionDef) -> FunctionSignature:
        args = [arg.arg for arg in node.args.args]
        doc = ast.get_docstring(node)
        return FunctionSignature(
            name=node.name,
            args=args,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=doc.splitlines()[0] if doc else None,
            line_number=node.lineno,
        )

    @classmethod
    def _get_attribute_name(cls, node: ast.Attribute) -> str:
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        return node.attr
