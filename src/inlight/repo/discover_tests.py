#!/usr/bin/env python3
"""
Step 1–2: Fetch README + file tree for each agent repo, call LLM to get test paths, save per-repo JSON.
Repo list: from data/hooked_repo/agent_repo.json (repositories[].name) or from repos.json in this dir.
"""
import json
import re
import sys
import time
from pathlib import Path

# Forge is under src/; this package is src/inlight/repo
_REPO_DIR = Path(__file__).resolve().parent
_SRC_DIR = _REPO_DIR.parent.parent  # src/
sys.path.insert(0, str(_SRC_DIR))

from forge.api import LLMClient

from . import config
from . import prompts
from .github_fetch import fetch_readme, fetch_file_tree, format_tree_for_prompt


def load_repo_list(use_small_list: bool = False) -> list[str]:
    """Load list of 'owner/repo'. By default use agent_repo.json (many repos from existing crawler).
    If use_small_list=True or repos.json exists and you want a small test list, pass use_small_list
    or we read repos.json only when agent_repo.json is missing."""
    # Prefer the hooked list (many agent repos from repo-hook pipeline)
    if config.HOOKED_REPO_JSON.exists() and not use_small_list:
        with open(config.HOOKED_REPO_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        repos = data.get("repositories") or []
        out = [r["name"] for r in repos if r.get("name")]
        if out:
            return out

    if config.REPOS_JSON.exists():
        with open(config.REPOS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return [r if isinstance(r, str) else r.get("name") or r.get("repo") for r in data]
        if isinstance(data, dict) and "repositories" in data:
            return [r.get("name") for r in data["repositories"] if r.get("name")]
        return []

    return []


def extract_json_only(text: str) -> dict:
    """Extract a single JSON object from model output (may be wrapped in markdown)."""
    text = (text or "").strip()
    # Strip markdown code block if present
    m = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
    if m:
        text = m.group(1)
    else:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            text = m.group(0)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"test_paths": []}


def run_one(repo: str, llm: LLMClient) -> dict:
    """Fetch readme + tree, call LLM, return {"repo": repo, "test_paths": [...]}."""
    readme = fetch_readme(repo)
    tree = fetch_file_tree(repo, max_depth=2)
    tree_text = format_tree_for_prompt(tree)

    user_msg = prompts.build_user_message(readme, tree_text, repo)
    response = llm.simple_chat(
        user_message=user_msg,
        system_prompt=prompts.SYSTEM_PROMPT,
        temperature=0.2,
    )
    out = extract_json_only(response)
    paths = out.get("test_paths")
    if not isinstance(paths, list):
        paths = []
    return {"repo": repo, "test_paths": paths}


def main():
    import os
    # forge.api loads .env on import; ensure key is set before calling LLM
    key = (os.getenv("FORGE_API_KEY") or "").strip()
    if not key or key == "your-forge-api-key-here":
        print("Error: FORGE_API_KEY is not set or still the placeholder.")
        print("Copy .env.example to .env in the project root and set FORGE_API_KEY to your API key.")
        return 1

    import argparse
    parser = argparse.ArgumentParser(description="Discover test paths per repo via README + tree + LLM")
    parser.add_argument("--small", action="store_true", help="Use repos.json only (small list), not agent_repo.json")
    parser.add_argument("--limit", type=int, default=None, metavar="N", help="Only run on the first N repos (e.g. --limit 100)")
    args = parser.parse_args()

    config.ensure_dirs()
    repos = load_repo_list(use_small_list=args.small)
    if args.limit is not None and args.limit > 0:
        repos = repos[: args.limit]
        print(f"Limited to first {args.limit} repos.")
    if not repos:
        print("No repos found. Put repos in data/hooked_repo/agent_repo.json or src/inlight/repo/repos.json")
        return 1

    print(f"Loaded {len(repos)} repos. Running discover_tests (README + tree -> LLM -> JSON)...")
    llm = LLMClient()

    for i, repo in enumerate(repos, 1):
        safe = repo.replace("/", "-")
        out_path = config.REPO_RESULTS_DIR / f"{safe}.json"
        if out_path.exists():
            print(f"[{i}/{len(repos)}] Skip (exists): {repo}")
            continue
        print(f"[{i}/{len(repos)}] {repo} ...")
        try:
            result = run_one(repo, llm)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"  -> {len(result.get('test_paths', []))} test paths")
        except Exception as e:
            print(f"  Error: {e}")
        time.sleep(0.5)

    print(f"Done. Results under {config.REPO_RESULTS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
