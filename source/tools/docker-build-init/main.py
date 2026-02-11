#!/usr/bin/env python3
"""
Scans key repository files, generates a detailed prompt, and calls the LLM to 
write a Dockerfile (env.dockerfile) that explicitly includes stages for both 
runtime and unit testing environments, ensuring multi-language (Node.js + Python) 
support in the test stage if required.
"""

import json
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

# 确保 that the necessary module (tools.api.main.chat) can be imported
PROJECT_ROOT = Path(__file__).resolve().parents[2]  # e.g., /home/cc/SWEGENT-BENCH/source
sys.path.insert(0, str(PROJECT_ROOT))

# Assuming this import path is correct for the user's environment
from tools.api.main import chat  # noqa: E402


# --- Configuration: Key Files to Scan ---

TARGET_FILES = [
    # Core Documentation & Deployment
    "README.md", "Dockerfile", "docker-compose.yml", 
    "Procfile", ".gitignore", "LICENSE", "CHANGELOG.md", "Makefile",
    
    # Dependency Management (Node.js/JavaScript)
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", 
    
    # Dependency Management (Python)
    "requirements.txt", "setup.py", "pyproject.toml",
    
    # Dependency Management (Java)
    "pom.xml", "build.gradle",
    
    # Dependency Management (PHP, Ruby, Go)
    "composer.json", "composer.lock", "Gemfile", "Gemfile.lock", 
    "go.mod", "go.sum",
    
    # Configuration & Build Tools
    "tsconfig.json", "babel.config.js", "jest.config.js",
]

TARGET_GLOBS = [
    # CI/CD Workflows
    ".github/workflows/*.yml",
    ".github/workflows/*.yaml",
    "gitlab-ci.yml",
    
    # Dockerfile Variants
    "*.Dockerfile",
    # Frontend Bundler/Configuration
    "*.config.*",  # e.g., webpack.config.js, vite.config.ts
    "docker-compose.*.yml",
]


# --- Core Logic Functions ---

def find_target_files(repo_root: Path) -> List[Path]:
    """Locate the target configuration and source files within the repository."""
    found: List[Path] = []

    for name in TARGET_FILES:
        path = repo_root / name
        if path.exists():
            found.append(path)

    for pattern in TARGET_GLOBS:
        found.extend(repo_root.glob(pattern))

    # Deduplicate paths (important for glob matching)
    unique: List[Path] = []
    seen = set()
    for p in found:
        if p.exists():
            key = p.resolve()
            if key not in seen:
                seen.add(key)
                unique.append(p)
    return unique


def read_files(files: List[Path]) -> List[Dict[str, str]]:
    """Read the content of the files, logging an error if reading fails."""
    results = []
    for file in files:
        # Use relative path for cleaner output in the prompt
        relative_path = Path(file).relative_to(Path.cwd()) if file.is_absolute() and file.is_relative_to(Path.cwd()) else file
        try:
            content = file.read_text(encoding="utf-8", errors="replace")
            results.append({"path": str(relative_path), "content": content})
        except Exception as e:  # pragma: no cover
            results.append({"path": str(relative_path), "content": f"<<READ ERROR: {e}>>"})
    return results


# NOTE: This build_prompt is now designed for the FINAL, most complex iteration 
# (Step 3: Force multi-language, force unit test, fix entry path).
def build_prompt(
    file_entries: List[Dict[str, str]],
    test_paths_list: Optional[List[str]] = None,
) -> str:
    """
    Assemble the final prompt with all constraints: multi-language setup, 
    standalone script execution, and fixing the application entry path inference.
    test_paths_list: known test paths/dirs from agent_repo (included in prompt so LLM supports them).
    """
    
    # --- Language Detection Logic ---
    has_node = any("package.json" in item['path'] for item in file_entries)

    # --------------------------------------------------------------------------
    # --- CRITICAL INSTRUCTIONS ---
    # --------------------------------------------------------------------------
    
    # Base image selection strategy
    base_image_note = (
        "**CRITICAL BASE IMAGE SELECTION:**\n"
        "- For Python projects: Use 'python:3.12-slim' or 'python:3.11-slim' (RECOMMENDED)\n"
        "- For Node.js projects: Use 'node:20-slim' or 'node:18-slim'\n"
        "- For Python+Node.js: Use 'python:3.12-slim' as base and install Node.js on top\n"
        "- AVOID using debian:bullseye-slim or ubuntu directly (complex dependency management)\n"
        "- Official language images are pre-configured, more reliable, and easier to build"
    )
    
    # Python is mandatory, so we enforce a versatile base image if Node is also present.
    multi_language_setup_note = (
        "**MULTI-LANGUAGE SETUP (if needed):** If both Python and Node.js are required:\n"
        "- Start from python:3.12-slim\n"
        "- Then install Node.js: apt-get install nodejs npm\n"
        "- This approach is simpler than starting from debian/ubuntu"
    )
    
    # This addresses the previous 'dist/main.js' error
    entrypoint_fix_note = (
        "**CRITICAL ENTRYPOINT FIX:** The final `CMD` or `ENTRYPOINT` **MUST be inferred directly from package.json (e.g., 'start' script) or other key files**, "
        "and the corresponding main application file (e.g., 'index.js', 'server.js', 'main.py') MUST be copied correctly, **without relying on a generic '/dist' path unless explicitly defined in the source files.**"
    )

    parts = [
        "--- LLM INSTRUCTION: READ CAREFULLY ---",
        "",
        "**STRICT OUTPUT RULE:** Your entire response MUST be the raw, complete, final Dockerfile text. "
        "DO NOT use code fences (```dockerfile), DO NOT provide explanations, and DO NOT add any surrounding prose.",
        "",
        "--- REQUIREMENTS ---",
        "",
        base_image_note,
        "",
        multi_language_setup_note,
        "",
        entrypoint_fix_note,
        "",
        # UPDATED SECTION BELOW
        "1. **Test/Build Stage (AS test_builder):** This stage MUST install ALL dependencies (development included) and explicitly configure the environment to run the project build (inferred) AND **execute the standalone Python test script** found in the file list (e.g., `reproduce_issue.py` or similar).",
        "   - **DO NOT** use `python -m unittest discover`.", 
        "   - Instead, command the Dockerfile to run the specific python script directly (e.g., `RUN python reproduce_issue.py`).",
        "   If the file list below includes **known test file paths**, read their content and ensure your Dockerfile installs any required test dependencies and configures the environment so these scripts can be executed.",
        *(
            [f"   **Known test paths for this repo** (ensure Dockerfile supports running them): {', '.join(p.strip() for p in test_paths_list if p and isinstance(p, str))}"]
            if test_paths_list else []
        ),
        "2. **Minimal Runtime Image:** Use multi-stage build. The final image MUST be minimal, containing only production dependencies (no test tools).",
        "3. **Inference:** Infer package managers, required ports (EXPOSE), and installation steps from the provided file contents.",
        "",
        "--- START FILE CONTENTS ---",
    ]
    
    # Insert file contents
    for item in file_entries:
        path_str = item['path'].replace('\\', '/')
        parts.append(f"### {path_str}")
        parts.append(item["content"])
        parts.append("")
        
    parts.append("--- END FILE CONTENTS ---")
    
    # Final instruction block for the LLM
    parts.append("\nNow, output ONLY the Dockerfile content:")
    
    return "\n".join(parts)


def ask_ai(prompt: str, model: str = "OpenAI/gpt-4o") -> str:
    """Call the LLM to get the Docker build solution."""
    messages = [
        # System instruction is now much stronger and clearer on the role and output constraint
        {"role": "system", "content": "You are a Senior DevOps Engineer specialized in creating highly constrained, multi-purpose Dockerfiles. Your output must strictly be a raw Dockerfile. **Do NOT generate any text other than the Dockerfile content.**"},
        
        {"role": "user", "content": prompt},
    ]
    return chat(messages=messages, model=model)


def write_env_dockerfile(repo_root: Path, content: str) -> Path:
    """Write the AI output to env.dockerfile in the repository root."""
    target = repo_root / "env.dockerfile"
    target.write_text(content, encoding="utf-8")
    return target


def run_docker_build_flow(repo_root: Path, test_paths: Optional[List[str]] = None) -> Path:
    """Scan -> Assemble Prompt -> Call AI -> Write env.dockerfile.
    If test_paths is provided (e.g. from REPO_TEST_PATHS env or agent_repo test_paths),
    those paths are included in the context so the AI can ensure the Dockerfile supports running them.
    """
    print("--- Dockerfile Generation Flow Started ---")
    
    files = find_target_files(repo_root)
    print(f"1. Found {len(files)} key files for context.")
    
    file_entries = read_files(files)
    if not test_paths:
        test_paths = []
        try:
            raw = os.environ.get("REPO_TEST_PATHS")
            if raw:
                test_paths = json.loads(raw)
        except Exception:
            pass
    for p in test_paths:
        if not isinstance(p, str) or not p.strip():
            continue
        p = p.strip().replace("\\", "/")
        full = repo_root / p
        if full.is_file() and full.exists():
            if not any(e.get("path") == p for e in file_entries):
                try:
                    content = full.read_text(encoding="utf-8", errors="replace")
                    file_entries.append({"path": p, "content": content})
                    print(f"   Added known test file: {p}")
                except Exception:
                    pass
    
    # NOTE: This step assumes the FINAL prompt (Step 3) is being built.
    prompt = build_prompt(file_entries, test_paths_list=test_paths or None)
    
    print("2. Calling LLM to generate Dockerfile... (Wait time depends on API)")
    ai_result = ask_ai(prompt)
    
    # The output might still contain unwanted text if the LLM breaks the instruction.
    
    result_path = write_env_dockerfile(repo_root, ai_result)
    return result_path


def main():
    """Main execution entry point."""
    repo_root = Path.cwd()
    try:
        result_path = run_docker_build_flow(repo_root)
        print(f"\n--- SUCCESS ---")
        print(f"env.dockerfile successfully generated at: {result_path}")
    except Exception as e:
        print(f"\n--- ERROR ---")
        print(f"An error occurred during the process: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()