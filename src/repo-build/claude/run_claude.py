#!/usr/bin/env python3
"""
Script that loads environment variables from .env file, prepares context files,
and runs the claude command with a comprehensive prompt.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


def load_file_content(file_path):
    """Load and return file content, or return error message if file doesn't exist."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"[File not found: {file_path}]"
    except Exception as e:
        return f"[Error reading {file_path}: {e}]"


def build_prompt(repo_build_dir, feedback: Optional[str] = None):
    """Build the comprehensive prompt with all context files."""
    prompt_parts = []
    
    # Check for repository structure info from environment
    repo_structure_json = os.getenv("REPO_STRUCTURE")
    repo_structure = None
    if repo_structure_json:
        try:
            import json
            repo_structure = json.loads(repo_structure_json)
        except Exception:
            pass
    
    # Load base prompt
    prompt_file = repo_build_dir / "prompt.txt"
    base_prompt = load_file_content(prompt_file).strip()
    
    # Load model list
    model_list_file = repo_build_dir / "model-list.json"
    model_list = load_file_content(model_list_file)
    
    # Load environment pool
    env_pool_file = repo_build_dir / "env_pool.json"
    env_pool = load_file_content(env_pool_file)
    
    # Load mock interface
    mock_interface_file = repo_build_dir / "mock_interface.md"
    mock_interface = load_file_content(mock_interface_file)
    
    # Check for existing claude.dockerfile in current directory
    existing_dockerfile_path = Path.cwd() / "claude.dockerfile"
    existing_dockerfile_content = None
    if existing_dockerfile_path.exists():
        existing_dockerfile_content = load_file_content(existing_dockerfile_path)
    
    # Build the comprehensive prompt with clear instructions
    prompt_parts.append("=" * 80)
    prompt_parts.append("IMPORTANT INSTRUCTIONS")
    prompt_parts.append("=" * 80)
    prompt_parts.append("""
This repository is an AI project that needs to be configured to use Forge API instead of OpenAI API.

CRITICAL CONSTRAINTS:
- DO NOT modify any source code files
- ONLY configure environment variables in the Dockerfile
- DO NOT change any Python/JavaScript/other source files

BASE IMAGE SELECTION (VERY IMPORTANT):
- For Python projects: Use 'python:3.12-slim' or 'python:3.11-slim' (STRONGLY RECOMMENDED)
- For Node.js projects: Use 'node:20-slim' or 'node:18-slim'
- For Python+Node.js: Start from 'python:3.12-slim' and install Node.js on top
- For Rust projects: Use 'rust:1.75-slim' or 'rust:latest'
- AVOID debian:bullseye-slim or ubuntu (causes dependency issues like gnupg problems)
- Official language images are pre-configured and more reliable

PROJECT TYPE DETECTION:
- Check for Cargo.toml: This is a Rust project, use cargo build, NOT pip install
- Check for package.json: This is a Node.js/TypeScript project
- Check for requirements.txt or setup.py: This is a Python project
- Check for pyproject.toml: This is a Python project (may use poetry)

YOUR TASK:
When creating/configuring the Dockerfile, you need to:
1. Choose the appropriate base image (see BASE IMAGE SELECTION above)
2. Set the appropriate environment variables to make the repository use Forge API instead of OpenAI API
3. Install any dependencies required for the standalone reproduction script (standard pip requirements)
4. Ensure the system can run the standalone Python script directly (e.g., via 'python test_script.py')

ENVIRONMENT VARIABLES TO SET IN DOCKERFILE:
The Forge API is OpenAI-compatible, so the application can work with it by setting these 
environment variables in the Dockerfile:

For OpenAI SDK compatibility:
- OPENAI_BASE_URL=https://api.forge.tensorblock.co/v1
- OPENAI_API_KEY=${FORGE_API_KEY}

For Anthropic SDK compatibility:
- ANTHROPIC_BASE_URL=https://api.forge.tensorblock.co
- ANTHROPIC_AUTH_TOKEN=${FORGE_API_KEY}

Additional configuration variables are available in the "ENVIRONMENT VARIABLES REFERENCE" section.

STANDALONE SCRIPT ENVIRONMENT CONFIGURATION:
The Dockerfile MUST configure the environment to run standalone Python scripts:
- Ensure Python 3 is installed and available as `python` or `python3`
- Install standard system dependencies needed for Python execution
- If the repository has requirements (requirements.txt, etc.), install them so the script can import project modules
- The script will be run directly (e.g., `python test128.py`), NOT via a test runner (pytest/unittest)
- Ensure the environment allows standard import of 'sys', 'os', 'json', and 'requests' (if needed)

CRITICAL DOCKERFILE BEST PRACTICES:

1. FILE EXISTENCE CHECKS:
    - ALWAYS check if files exist before COPY: `RUN if [ -f "file.txt" ]; then cp file.txt /app/; fi`
    - ALWAYS check if directories exist before COPY: `RUN if [ -d "tests" ]; then cp -r tests/ /app/tests/; fi`
    - NEVER assume files exist - use conditional commands

2. PNPM GLOBAL CONFIGURATION:
    - If using `pnpm link --global`, set: `ENV PNPM_HOME=/root/.local/share/pnpm`
    - Add to PATH: `ENV PATH="$PNPM_HOME:$PATH"`
    - Or avoid --global flag if not needed

3. PYTHON PACKAGE INSTALLATION (PEP 668):
    - For Python 3.11+, use virtual environment: `RUN python3 -m venv /venv && /venv/bin/pip install ...`
    - Or use: `RUN pip install --break-system-packages ...`
    - Or use: `RUN pip install --user ...`

4. COMPILATION DEPENDENCIES:
    - For packages like lxml, install system libraries first:
      `RUN apt-get update && apt-get install -y libxml2-dev libxslt1-dev python3-dev gcc`
    - Then install Python packages: `RUN pip install lxml`

5. POETRY INSTALLATION:
    - Install via pipx: `RUN pipx install poetry`
    - Add to PATH: `ENV PATH="/root/.local/bin:$PATH"`
    - Or use pip: `RUN pip install poetry`

6. RUST PROJECTS:
    - If Cargo.toml exists, this is a Rust project
    - Use `cargo build` NOT `pip install`
    - Install Rust toolchain if needed: `RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y`

7. PATH HANDLING:
    - Always use forward slashes in paths: `/workspace/tests/test.py`
    - Never use Windows-style backslashes: `\\workspace\\tests\\test.py`
    - Normalize paths in RUN commands

8. NETWORK ERRORS:
    - Add retry logic for network operations
    - Use mirrors for package managers if needed
    - Consider using --network=host for Docker builds if network issues persist

APPROACH:
1. Set environment variables in the Dockerfile using ENV directives
2. Install Python and any project dependencies required by the reproduction script using RUN commands
3. Install any system packages needed by the repository
4. These environment variables will override the default API endpoints
5. The existing code will automatically use Forge API through these environment variables
6. No code changes needed - only Dockerfile configuration
""")
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("AVAILABLE MODELS")
    prompt_parts.append("=" * 80)
    prompt_parts.append("These models are available through Forge API:")
    prompt_parts.append(model_list)
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("ENVIRONMENT VARIABLES REFERENCE")
    prompt_parts.append("=" * 80)
    prompt_parts.append("Set these environment variables in the Dockerfile (use ENV directive):")
    prompt_parts.append(env_pool)
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("API USAGE EXAMPLE (For Reference Only)")
    prompt_parts.append("=" * 80)
    prompt_parts.append("This shows how the Forge API works - DO NOT modify code, just set ENV vars:")
    prompt_parts.append(mock_interface)
    prompt_parts.append("")
    
    # Add existing Dockerfile section if available (from agentless init or previous iteration)
    if existing_dockerfile_content and not existing_dockerfile_content.startswith("["):
        prompt_parts.append("=" * 80)
        prompt_parts.append("EXISTING DOCKERFILE (Current Version)")
        prompt_parts.append("=" * 80)
        if feedback:
            prompt_parts.append("This is the current Dockerfile that failed to build:")
        else:
            prompt_parts.append("An initial Dockerfile has been generated (possibly by agentless initialization).")
            prompt_parts.append("Please review and optimize it based on the requirements:")
        prompt_parts.append("")
        prompt_parts.append(existing_dockerfile_content)
        prompt_parts.append("")
        if not feedback:
            prompt_parts.append("TASK: Review the above Dockerfile and improve it if needed.")
            prompt_parts.append("If it looks good, you can keep it. If there are issues, fix them.")
    prompt_parts.append("")
    
    # Add feedback section if available
    if feedback:
        prompt_parts.append("=" * 80)
        prompt_parts.append("PREVIOUS BUILD FEEDBACK")
        prompt_parts.append("=" * 80)
        prompt_parts.append("The previous Docker build attempt failed. Here is the error information:")
        prompt_parts.append("")
        prompt_parts.append(feedback)
        prompt_parts.append("")
        prompt_parts.append("Please analyze the errors above and generate an improved Dockerfile that fixes these issues.")
        prompt_parts.append("Focus on the specific errors shown in the feedback.")
        prompt_parts.append("")
    
    # Add repository structure information if available
    if repo_structure:
        prompt_parts.append("=" * 80)
        prompt_parts.append("REPOSITORY STRUCTURE INFORMATION")
        prompt_parts.append("=" * 80)
        prompt_parts.append("The following files/directories exist (or don't exist) in this repository:")
        prompt_parts.append("")
        for key, exists in repo_structure.items():
            status = "✓ EXISTS" if exists else "✗ DOES NOT EXIST"
            prompt_parts.append(f"  {status}: {key}")
        prompt_parts.append("")
        prompt_parts.append("IMPORTANT: Only COPY files/directories that EXIST. Use conditional COPY or check existence first.")
        prompt_parts.append("Example: RUN if [ -f \"requirements.txt\" ]; then pip install -r requirements.txt; fi")
        prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("SPECIFIC TASK")
    prompt_parts.append("=" * 80)
    prompt_parts.append(base_prompt)
    prompt_parts.append("")
    prompt_parts.append("REMINDER: Only configure environment variables and install dependencies in Dockerfile. Do NOT modify any source code.")
    prompt_parts.append("")
    prompt_parts.append("STANDALONE SCRIPT REQUIREMENT: The Dockerfile must ensure the environment supports running standalone Python scripts directly.")
    
    return "\n".join(prompt_parts)


def main():
    # Get directories relative to script location
    script_dir = Path(__file__).resolve().parent  # claude/
    repo_build_dir = script_dir.parent  # repo-build/
    project_root = repo_build_dir.parent.parent  # project root
    env_path = project_root / ".env"
    
    print(f"Script directory: {script_dir}")
    print(f"Repo-build directory: {repo_build_dir}")
    print(f"Project root: {project_root}")
    print(f".env path: {env_path}")
    print(f"Current working directory: {Path.cwd()}")
    
    # Check if .env exists
    if not env_path.exists():
        print(f"Error: {env_path} file does not exist!")
        sys.exit(1)
    
    # Load and set environment variables
    print("\nLoading environment variables...")
    with open(env_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue
            
            # Parse environment variable
            if '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip()
                
                # Remove quotes
                if (value.startswith('"') and value.endswith('"')) or \
                   (value.startswith("'") and value.endswith("'")):
                    value = value[1:-1]
                
                # Set environment variable for current process
                os.environ[key] = value
                print(f"  Set: {key} = {value}")
    
    print("\nEnvironment variables loaded successfully!")
    
    # Build comprehensive prompt
    print("\nBuilding prompt with context files...")
    # Check for feedback from environment
    feedback = os.getenv("DOCKERFILE_FEEDBACK")
    if feedback:
        print("Found feedback from previous build attempt, including in prompt...")
    full_prompt = build_prompt(repo_build_dir, feedback)
    print(f"Prompt built successfully ({len(full_prompt)} characters)")
    
    # Run claude command
    print("\nRunning claude command...")
    print("-" * 80)
    
    try:
        # Get additional arguments passed to the script
        extra_args = sys.argv[1:]
        
        # Run claude command with the built prompt, in the current working directory
        # This ensures claude runs from where the user invoked the script, not from script location
        cmd = ['claude', full_prompt] + extra_args
        result = subprocess.run(cmd, env=os.environ, cwd=Path.cwd())
        
        sys.exit(result.returncode)
        
    except FileNotFoundError:
        print("Error: 'claude' command not found!")
        print("Please ensure claude is installed and in PATH.")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
