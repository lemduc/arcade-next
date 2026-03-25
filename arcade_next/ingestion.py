"""Git repository ingestion: clone, detect versions, checkout."""

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from git import Repo, GitCommandError


@dataclass
class IngestedRepo:
    """Result of ingesting a repository."""
    path: Path
    name: str
    version: str
    is_temp: bool = False
    java_files: list[Path] = field(default_factory=list)

    def cleanup(self):
        if self.is_temp and self.path.exists():
            shutil.rmtree(self.path)


def ingest(source: str, work_dir: Path | None = None) -> IngestedRepo:
    """Ingest a repository from a URL or local path.

    Args:
        source: Git repo URL or local directory path.
        work_dir: Directory to clone into. Uses temp dir if None.

    Returns:
        IngestedRepo with path, name, version, and java file list.
    """
    source_path = Path(source)
    if source_path.is_dir():
        return _ingest_local(source_path)
    return _clone_and_ingest(source, work_dir)


def _ingest_local(path: Path) -> IngestedRepo:
    """Ingest a local directory (may or may not be a git repo)."""
    name = path.name
    version = "local"

    try:
        repo = Repo(path)
        version = _detect_version(repo)
    except Exception:
        pass

    java_files = sorted(path.rglob("*.java"))
    return IngestedRepo(
        path=path, name=name, version=version,
        is_temp=False, java_files=java_files,
    )


def _clone_and_ingest(url: str, work_dir: Path | None) -> IngestedRepo:
    """Clone a remote repo and ingest it."""
    name = _repo_name_from_url(url)

    if work_dir is None:
        work_dir = Path(tempfile.mkdtemp(prefix="arcade_next_"))
    clone_path = work_dir / name

    print(f"  Cloning {url}...")
    repo = Repo.clone_from(url, clone_path, depth=1)

    version = _detect_version(repo)
    if version != "HEAD":
        try:
            repo.git.checkout(version)
        except GitCommandError:
            pass

    java_files = sorted(clone_path.rglob("*.java"))
    return IngestedRepo(
        path=clone_path, name=name, version=version,
        is_temp=True, java_files=java_files,
    )


def _detect_version(repo: Repo) -> str:
    """Detect the latest version tag from a repo."""
    try:
        tags = sorted(repo.tags, key=lambda t: t.commit.committed_datetime)
        if tags:
            return str(tags[-1])
    except Exception:
        pass
    return "HEAD"


def _repo_name_from_url(url: str) -> str:
    """Extract repository name from a URL."""
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name
