"""Fetch repo README and file tree (max 2 levels) from GitHub API."""
import os
import requests
from typing import Optional, List, Dict, Any

BASE_URL = "https://api.github.com"


def _headers() -> Dict[str, str]:
    h = {"Accept": "application/vnd.github.v3+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        h["Authorization"] = f"token {token}"
    return h


def get_default_branch(repo: str) -> Optional[str]:
    """Return default branch (e.g. main) for repo 'owner/name'."""
    try:
        r = requests.get(
            f"{BASE_URL}/repos/{repo}",
            headers=_headers(),
            timeout=15,
        )
        r.raise_for_status()
        return r.json().get("default_branch") or "main"
    except Exception:
        return "main"


def fetch_readme(repo: str) -> str:
    """Fetch README content as raw text. Returns empty string on failure."""
    try:
        # Raw content to avoid base64 decoding
        r = requests.get(
            f"{BASE_URL}/repos/{repo}/readme",
            headers={**_headers(), "Accept": "application/vnd.github.raw"},
            timeout=15,
        )
        if r.status_code != 200:
            return ""
        return r.text
    except Exception:
        return ""


def fetch_file_tree(repo: str, max_depth: int = 2) -> List[Dict[str, Any]]:
    """
    Fetch file tree from default branch, filter to paths with at most max_depth segments.
    depth 2 => path has at most 2 slashes (e.g. a, a/b, a/b/c).
    Returns list of items: [{"path": "...", "type": "blob"|"tree"}, ...].
    """
    branch = get_default_branch(repo)
    try:
        r = requests.get(
            f"{BASE_URL}/repos/{repo}/git/trees/{branch}",
            headers=_headers(),
            params={"recursive": "1"},
            timeout=30,
        )
        r.raise_for_status()
        data = r.json()
        tree = data.get("tree") or []
    except Exception:
        return []

    out = []
    for node in tree:
        path = node.get("path") or ""
        if path.count("/") <= max_depth:
            out.append({
                "path": path,
                "type": node.get("type", "blob"),
            })
    return out


def format_tree_for_prompt(tree: List[Dict[str, Any]]) -> str:
    """Format tree as a simple list of paths (one per line) for the prompt."""
    lines = [n["path"] for n in sorted(tree, key=lambda x: x["path"])]
    return "\n".join(lines) if lines else "(empty)"
