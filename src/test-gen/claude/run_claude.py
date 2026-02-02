#!/usr/bin/env python3
"""
Script that loads environment variables from .env file, prepares context files,
and runs the claude command to generate test cases for agent-related issues.
"""

import os
import json
import subprocess
import sys
from pathlib import Path


def load_file_content(file_path):
    """Load and return file content, or return error message if file doesn't exist."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return f"[File not found: {file_path}]"
    except Exception as e:
        return f"[Error reading {file_path}: {e}]"


def get_repo_code_summary(repo_path: Path, max_files: int = 50) -> str:
    """
    Get repository code summary
    
    Args:
        repo_path: Repository path
        max_files: Maximum number of files
        
    Returns:
        Code summary string
    """
    summary_parts = []
    summary_parts.append("=" * 80)
    summary_parts.append("REPOSITORY CODE STRUCTURE")
    summary_parts.append("=" * 80)
    
    # Get main source code files
    code_files = []
    for ext in ['*.py', '*.js', '*.ts', '*.rs', '*.go', '*.java']:
        code_files.extend(list(repo_path.rglob(ext)))
    
    # Limit number of files
    code_files = code_files[:max_files]
    
    summary_parts.append(f"\nFound {len(code_files)} code files (showing up to {max_files}):\n")
    
    for file_path in code_files[:20]:  # Show first 20
        rel_path = file_path.relative_to(repo_path)
        summary_parts.append(f"- {rel_path}")
    
    # Read some key files' content
    key_files = []
    for pattern in ['README.md', 'setup.py', 'package.json', 'Cargo.toml', 'requirements.txt']:
        matches = list(repo_path.glob(pattern))
        if matches:
            key_files.extend(matches[:1])
    
    if key_files:
        summary_parts.append("\nKey configuration files:")
        for file_path in key_files[:5]:
            rel_path = file_path.relative_to(repo_path)
            try:
                content = load_file_content(file_path)
                summary_parts.append(f"\n--- {rel_path} ---")
                summary_parts.append(content[:1000])  # Limit length
            except:
                pass
    
    return "\n".join(summary_parts)


def build_prompt(repo_path: Path, issue_json_path: Path, repo_build_dir: Path):
    """
    Build prompt for generating standalone reproduction scripts
    
    Args:
        repo_path: Repository path
        issue_json_path: Issue JSON file path
        repo_build_dir: repo-build directory path
    """
    prompt_parts = []
    
    # Load issue JSON
    with open(issue_json_path, 'r', encoding='utf-8') as f:
        issue_data = json.load(f)
    
    # Load reference files
    env_pool_file = repo_build_dir / "env_pool.json"
    env_pool = load_file_content(env_pool_file)
    
    mock_interface_file = repo_build_dir / "mock_interface.md"
    mock_interface = load_file_content(mock_interface_file)
    
    # Get repository code summary
    repo_summary = get_repo_code_summary(repo_path)
    
    # Build prompt
    prompt_parts.append("=" * 80)
    prompt_parts.append("TASK: GENERATE STANDALONE REPRODUCTION SCRIPT")
    prompt_parts.append("=" * 80)
    prompt_parts.append("""
You are tasked with creating a standalone Python reproduction script for an agent-related issue.

CRITICAL REQUIREMENTS:
1. Write a standalone script based on the issue description and the provided patch
2. The script must NOT use the 'unittest' framework (no unittest.TestCase)
3. Use standard 'assert' statements to verify the bug described
4. Mock any remote API calls (LLM providers, external services) - DO NOT make real API calls
5. The script should raise an AssertionError (or exit with non-zero code) on the buggy version
6. The script should run successfully (exit with code 0) on the fixed version (after patch)

SCRIPT STRUCTURE:
- Use standard Python functions or top-level code
- Use 'unittest.mock' (or similar) strictly for mocking functionality, NOT for test runners
- Include a 'if __name__ == "__main__":' block
- Do NOT define a class inheriting from unittest.TestCase

OUTPUT FORMAT:
You MUST save the script as a Python file. Prefer saving in tests/ directory if it exists,
otherwise save in repository root directory.
The filename MUST be exactly: test{issue_number}.py
For example, if issue number is 128, the file must be named: test128.py
DO NOT use any other naming format like test_issue_128.py or test_128.py - use test128.py

IMPORTANT: If tests/ directory exists, save the file there to avoid setuptools conflicts.
If tests/ directory doesn't exist, save in repository root directory.
CRITICAL: The file must be created before you finish.
""")
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("ISSUE INFORMATION")
    prompt_parts.append("=" * 80)
    prompt_parts.append(f"""
Issue #{issue_data.get('number')}: {issue_data.get('title')}
URL: {issue_data.get('url')}
State: {issue_data.get('state')}
Created: {issue_data.get('created_at')}
Closed: {issue_data.get('closed_at')}

Description:
{issue_data.get('body', 'N/A')}

Labels: {', '.join(issue_data.get('labels', []))}

IMPORTANT: You must create a reproduction script named: test{issue_data.get('number')}.py
""")
    
    # Add PR and patch information
    linked_prs = issue_data.get('linked_prs', [])
    if linked_prs:
        prompt_parts.append("\n" + "=" * 80)
        prompt_parts.append("LINKED PULL REQUEST(S)")
        prompt_parts.append("=" * 80)
        
        for pr in linked_prs:
            patch = pr.get('patch')
            patch_str = patch[:5000] if patch else 'N/A'
            prompt_parts.append(f"""
PR #{pr.get('number')}: {pr.get('title')}
URL: {pr.get('url')}
State: {pr.get('state')}
Merged: {pr.get('merged', False)}
Base Branch: {pr.get('base_branch', 'N/A')}

PR Description:
{pr.get('body', 'N/A')}

Patch/Diff:
{patch_str}
""")
    
    prompt_parts.append("")
    prompt_parts.append(repo_summary)
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("MOCK INTERFACE GUIDELINES")
    prompt_parts.append("=" * 80)
    prompt_parts.append("""
When writing tests, you MUST mock remote API interactions. Use the following guidelines:
""")
    prompt_parts.append(mock_interface)
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("ENVIRONMENT VARIABLES REFERENCE")
    prompt_parts.append("=" * 80)
    prompt_parts.append("These environment variables may be relevant for mocking:")
    prompt_parts.append(env_pool)
    prompt_parts.append("")
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("INSTRUCTIONS")
    prompt_parts.append("=" * 80)
    prompt_parts.append("""
1. Analyze the issue description and the patch to understand what bug was fixed
2. Examine the repository structure to understand the codebase
3. Write a standalone reproduction script that:
   - Reproduces the bug condition (script should FAIL/Raise Error with buggy code)
   - Verifies the fix works (script should PASS/Exit 0 with fixed code)
   - Uses mocks for all external API calls
   - Is self-contained and can run independently

4. Save the script with the exact filename: test{issue_number}.py
   - If tests/ directory exists, save there: tests/test{issue_number}.py
   - Otherwise, save in repository root: test{issue_number}.py
   - IMPORTANT: The filename must be exactly "test{issue_number}.py"
   - DO NOT use the unittest framework (no class inheriting from unittest.TestCase)

5. Make sure the script:
   - Uses standard `assert` statements
   - Contains a `if __name__ == "__main__":` block
   - Exits with status code 0 if the test passes (reproduction successful/fix verified)
   - Raises an exception or exits with non-zero status if the test fails
   - Includes comments explaining the reproduction steps
""")
    
    return "\n".join(prompt_parts)


def main():
    # Get directories relative to script location
    script_dir = Path(__file__).resolve().parent  # claude/
    test_gen_dir = script_dir.parent  # test-gen/
    repo_build_dir = test_gen_dir.parent / "repo-build"  # repo-build/
    project_root = test_gen_dir.parent.parent  # project root
    env_path = project_root / ".env"
    
    # Parse command line arguments
    if len(sys.argv) < 3:
        print("Usage: python run_claude.py <repo_path> <issue_json_path>")
        print("Example: python run_claude.py /home/cc/SWEGENT-BENCH/codex /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json")
        sys.exit(1)
    
    repo_path = Path(sys.argv[1]).resolve()
    issue_json_path = Path(sys.argv[2]).resolve()
    
    # Validate paths
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    if not issue_json_path.exists():
        print(f"Error: Issue JSON file does not exist: {issue_json_path}")
        sys.exit(1)
    
    print(f"Repository path: {repo_path}")
    print(f"Issue JSON: {issue_json_path}")
    print(f"Repo-build directory: {repo_build_dir}")
    print(f"Project root: {project_root}")
    print(f"Current working directory: {Path.cwd()}")
    
    # Check if .env exists
    if not env_path.exists():
        print(f"Warning: {env_path} file does not exist, will use environment variables")
    else:
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
    
    # Switch to repository directory
    original_cwd = Path.cwd()
    os.chdir(repo_path)
    
    try:
        # Build comprehensive prompt
        print("\nBuilding prompt...")
        full_prompt = build_prompt(repo_path, issue_json_path, repo_build_dir)
        print(f"Prompt built successfully ({len(full_prompt)} characters)")
        
        # Run claude command
        print("\nRunning claude command...")
        print("-" * 80)
        
        # Run claude command with the built prompt, in the repository directory
        cmd = ['claude', full_prompt]
        result = subprocess.run(cmd, env=os.environ, cwd=repo_path)
        
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        os.chdir(original_cwd)


if __name__ == "__main__":
    main()

