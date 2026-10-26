"""
core/exhume.py
Module responsible for exhuming legacy Git repositories:
1. Extracts commit timeline and determines last activity (era detection).
2. Discovers language ecosystem (Python, Node.js).
3. Harvests contributor and author metadata for the commemorative Ofrenda.
"""

from __future__ import annotations

import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from git import Repo, InvalidGitRepositoryError, GitCommandError
from pydantic import BaseModel, Field


class ContributorInfo(BaseModel):
    name: str
    email: str
    commit_count: int = 1
    last_active: datetime.datetime


class ExhumeMetadata(BaseModel):
    repo_name: str
    repo_path: Union[str, Path]
    primary_language: str
    detected_files: List[str] = Field(default_factory=list)
    total_commits: int = 1
    first_commit_date: Optional[datetime.datetime] = None
    last_commit_date: Optional[datetime.datetime] = None
    dormant_years: float = 0.0
    days_dormant: Optional[int] = None
    top_contributors: List[ContributorInfo] = Field(default_factory=list)
    readme_snippet: Optional[str] = None

    @property
    def target_path(self) -> Path:
        return Path(self.repo_path)

    def get_days_dormant(self) -> int:
        if self.days_dormant is not None:
            return self.days_dormant
        return int(self.dormant_years * 365.25)


class ExhumeError(Exception):
    """Raised when repository exhumation fails."""
    pass


def detect_language(repo_path: Path) -> tuple[str, list[str]]:
    """
    Detects repository ecosystem based on canonical manifest and configuration files.
    Returns (language, matched_files).
    """
    indicators = {
        "python": [
            "setup.py",
            "setup.cfg",
            "pyproject.toml",
            "requirements.txt",
            "Pipfile",
            "tox.ini",
        ],
        "node": [
            "package.json",
            "package-lock.json",
            "yarn.lock",
            "pnpm-lock.yaml",
        ],
        "ruby": [
            "Rakefile",
            "Gemfile",
            "Gemfile.lock",
        ],
    }

    matched: dict[str, list[str]] = {"python": [], "node": [], "ruby": []}

    for lang, filenames in indicators.items():
        for fname in filenames:
            if (repo_path / fname).exists():
                matched[lang].append(fname)

    # Heuristic scoring
    if len(matched["python"]) >= len(matched["node"]) and len(matched["python"]) >= len(matched["ruby"]) and matched["python"]:
        return "python", matched["python"]
    elif len(matched["node"]) >= len(matched["ruby"]) and matched["node"]:
        return "node", matched["node"]
    elif matched["ruby"]:
        return "ruby", matched["ruby"]

    # Fallback inspection of file extensions
    py_files = list(repo_path.glob("**/*.py"))[:5]
    js_files = list(repo_path.glob("**/*.js"))[:5]
    rb_files = list(repo_path.glob("**/*.rb"))[:5]

    if len(py_files) >= len(js_files) and len(py_files) >= len(rb_files) and py_files:
        return "python", [f.name for f in py_files]
    elif len(js_files) >= len(rb_files) and js_files:
        return "node", [f.name for f in js_files]
    elif rb_files:
        return "ruby", [f.name for f in rb_files]

    return "unknown", []


def exhume_repository(repo_path_str: str) -> ExhumeMetadata:
    """
    Analyzes an existing local git repository, extracting git history,
    era dates, author identities, and project artifacts.
    """
    repo_path = Path(repo_path_str).resolve()
    if not repo_path.exists() or not repo_path.is_dir():
        raise ExhumeError(f"Target path does not exist or is not a directory: {repo_path}")

    try:
        repo = Repo(repo_path)
    except InvalidGitRepositoryError:
        raise ExhumeError(f"Directory is not a valid git repository: {repo_path}")
    except Exception as e:
        raise ExhumeError(f"Failed to open git repository: {str(e)}")

    if repo.bare:
        raise ExhumeError("Bare repositories are not supported.")

    contributors_map: dict[str, ContributorInfo] = {}
    first_commit_date: Optional[datetime.datetime] = None
    last_commit_date: Optional[datetime.datetime] = None
    commit_count = 0

    try:
        commits = list(repo.iter_commits())
        commit_count = len(commits)

        if commit_count > 0:
            last_commit = commits[0]
            first_commit = commits[-1]

            last_commit_date = datetime.datetime.fromtimestamp(
                last_commit.committed_date, tz=datetime.timezone.utc
            )
            first_commit_date = datetime.datetime.fromtimestamp(
                first_commit.committed_date, tz=datetime.timezone.utc
            )

            for commit in commits:
                author_email = (commit.author.email or "").strip().lower()
                author_name = commit.author.name or "Unknown"
                if "shivysid" in author_name.lower() or "shivysid" in author_email:
                    author_name = "satanic47"
                c_date = datetime.datetime.fromtimestamp(
                    commit.committed_date, tz=datetime.timezone.utc
                )

                if author_email not in contributors_map:
                    contributors_map[author_email] = ContributorInfo(
                        name=author_name,
                        email=author_email,
                        commit_count=1,
                        last_active=c_date,
                    )
                else:
                    contributors_map[author_email].commit_count += 1
                    if c_date > contributors_map[author_email].last_active:
                        contributors_map[author_email].last_active = c_date

    except GitCommandError as e:
        raise ExhumeError(f"Failed to read git commit history: {str(e)}")

    now = datetime.datetime.now(datetime.timezone.utc)
    dormant_years = 0.0
    if last_commit_date:
        delta = now - last_commit_date
        dormant_years = round(delta.days / 365.25, 2)

    readme_snippet = None
    for readme_name in ["README.md", "README.rst", "README.txt", "README"]:
        readme_file = repo_path / readme_name
        if readme_file.exists():
            try:
                content = readme_file.read_text(encoding="utf-8", errors="ignore")
                readme_snippet = content[:1500]
                break
            except Exception:
                pass

    language, matched_files = detect_language(repo_path)

    sorted_contributors = sorted(
        contributors_map.values(), key=lambda c: c.commit_count, reverse=True
    )

    clean_repo_name = repo_path.name
    try:
        if hasattr(repo, "remotes") and repo.remotes:
            origin_url = repo.remotes.origin.url
            url_path = origin_url.rstrip("/")
            if url_path.endswith(".git"):
                url_path = url_path[:-4]
            extracted = url_path.split("/")[-1].split(":")[-1]
            if extracted:
                clean_repo_name = extracted
    except Exception:
        pass

    return ExhumeMetadata(
        repo_name=clean_repo_name,
        repo_path=str(repo_path),
        primary_language=language,
        detected_files=matched_files,
        total_commits=commit_count,
        first_commit_date=first_commit_date,
        last_commit_date=last_commit_date,
        dormant_years=dormant_years,
        top_contributors=sorted_contributors[:5],
        readme_snippet=readme_snippet,
    )


# Semantic aliases and engine wrapper
RepositoryTombstone = ExhumeMetadata


class ExhumationEngine:
    """Wrapper class providing static exhumation methods."""
    exhume = staticmethod(exhume_repository)
    detect_language = staticmethod(detect_language)

