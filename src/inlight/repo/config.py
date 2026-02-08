"""Paths and defaults for inlight.repo."""
import os
from pathlib import Path

# This package: src/inlight/repo/
_REPO_DIR = Path(__file__).resolve().parent
_SRC_DIR = _REPO_DIR.parent
_PROJECT_ROOT = _SRC_DIR.parent.parent

# Data dirs (under project root)
DATA_DIR = _PROJECT_ROOT / "data"
HOOKED_REPO_JSON = DATA_DIR / "hooked_repo" / "agent_repo.json"
REPO_RESULTS_DIR = DATA_DIR / "inlight" / "repo_results"
TOP_K_PATTERNS_JSON = DATA_DIR / "inlight" / "test_path_patterns_topk.json"

# Optional: override repo list with a local JSON array of "owner/repo"
REPOS_JSON = _REPO_DIR / "repos.json"

# Default top-k for aggregated patterns
DEFAULT_TOP_K = 50


def ensure_dirs():
    REPO_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    TOP_K_PATTERNS_JSON.parent.mkdir(parents=True, exist_ok=True)
