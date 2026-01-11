#!/usr/bin/env python3
"""
Main script: Orchestrates the test case generation and verification workflow
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional


def expand_issue_json(issue_json_path: Path, expanded_json_path: Path):
    """Expand issue JSON to fetch PR patch information"""
    print(f"\n{'='*80}")
    print("Step 1: Expand issue JSON, fetch PR patch information")
    print(f"{'='*80}")
    
    script_dir = Path(__file__).parent
    expand_script = script_dir / "expand_issue_json.py"
    
    cmd = [
        sys.executable,
        str(expand_script),
        str(issue_json_path),
        str(expanded_json_path)
    ]
    
    result = subprocess.run(cmd, check=True)
    print("✓ Issue JSON expansion completed")


def generate_test_case(repo_path: Path, expanded_json_path: Path):
    """Generate test case using AI"""
    print(f"\n{'='*80}")
    print("Step 2: Generate test case using AI")
    print(f"{'='*80}")
    
    # Read issue number to determine expected test file name
    with open(expanded_json_path, 'r', encoding='utf-8') as f:
        import json
        issue_data = json.load(f)
    issue_number = issue_data.get('number')
    
    if not issue_number:
        print("Error: Cannot determine issue number from JSON")
        return False
    
    is_file_exist = False
    is_file2_exist = False
    expected_test_file = repo_path / f"test{issue_number}.py"
    if expected_test_file.exists():
        print(f"Expected test file: {expected_test_file}")
        print(f"  File size: {expected_test_file.stat().st_size} bytes")
        is_file_exist = True
    else:
        print(f"Expected test file does not exist: {expected_test_file}")

    expected_test_file2 = repo_path / f"tests/test{issue_number}.py"
    if expected_test_file2.exists():
        print(f"Expected test file 2: {expected_test_file2}")
        print(f"  File size: {expected_test_file2.stat().st_size} bytes")
        is_file2_exist = True
    else:
        print(f"Expected test file 2 does not exist: {expected_test_file2}")
    
    script_dir = Path(__file__).parent
    claude_script = script_dir / "claude" / "run_claude.py"
    
    cmd = [
        sys.executable,
        str(claude_script),
        str(repo_path),
        str(expanded_json_path)
    ]
    
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print("Warning: There may be issues with AI test case generation, please check")
        return False
    
    # Verify test file was created
    print(f"\nVerifying test file was created...")
    if is_file_exist or is_file2_exist:
        print(f"✓ Test file created successfully: {expected_test_file}")
        return True
    else:
        print(f"✗ Error: Test file was not created at expected location: {expected_test_file}")
        print(f"  Please check if the file was created with a different name.")
        
        # Try to find similar test files
        possible_files = list(repo_path.glob(f"test*{issue_number}*.py"))
        if possible_files:
            print(f"  Found similar files:")
            for f in possible_files:
                print(f"    - {f}")
        
        return False


def run_docker_tests(repo_path: Path, dockerfile_path: Path, issue_json_path: Path):
    """Run Docker tests"""
    print(f"\n{'='*80}")
    print("Step 3: Run Docker tests")
    print(f"{'='*80}")
    
    script_dir = Path(__file__).parent
    docker_script = script_dir / "run_docker_tests.py"
    
    cmd = [
        sys.executable,
        str(docker_script),
        str(repo_path),
        str(dockerfile_path),
        str(issue_json_path)
    ]
    
    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    """Main function"""
    if len(sys.argv) < 4:
        print("Usage: python main.py <repo_path> <dockerfile_path> <issue_json_path>")
        print("\nExamples:")
        print("  # Run from any directory (using absolute paths):")
        print("  python /home/cc/SWEGENT-BENCH/src/test-gen/main.py \\")
        print("         /home/cc/SWEGENT-BENCH/codex \\")
        print("         /home/cc/SWEGENT-BENCH/codex/claude.dockerfile \\")
        print("         /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json")
        print("\n  # Run from repo directory (using relative paths):")
        print("  python /home/cc/SWEGENT-BENCH/src/test-gen/main.py . ./claude.dockerfile ../data/issue-filtered/issue_128.json")
        sys.exit(1)
    
    # Parse paths, support both relative and absolute paths
    # repo_path can be relative (relative to current working directory)
    repo_path = Path(sys.argv[1])
    if not repo_path.is_absolute():
        repo_path = Path.cwd() / repo_path
    repo_path = repo_path.resolve()
    
    # dockerfile_path can be relative (relative to repo_path or current working directory)
    dockerfile_path = Path(sys.argv[2])
    if not dockerfile_path.is_absolute():
        # Try relative to repo_path first
        candidate = repo_path / dockerfile_path
        if candidate.exists():
            dockerfile_path = candidate
        else:
            # Otherwise relative to current working directory
            dockerfile_path = Path.cwd() / dockerfile_path
    dockerfile_path = dockerfile_path.resolve()
    
    # issue_json_path can be relative (relative to current working directory)
    issue_json_path = Path(sys.argv[3])
    if not issue_json_path.is_absolute():
        issue_json_path = Path.cwd() / issue_json_path
    issue_json_path = issue_json_path.resolve()
    
    # Validate paths
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    if not dockerfile_path.exists():
        print(f"Error: Dockerfile does not exist: {dockerfile_path}")
        sys.exit(1)
    
    if not issue_json_path.exists():
        print(f"Error: Issue JSON file does not exist: {issue_json_path}")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print("Test Case Generation and Verification Tool")
    print(f"{'='*80}")
    print(f"Repository path: {repo_path}")
    print(f"Dockerfile: {dockerfile_path}")
    print(f"Issue JSON: {issue_json_path}")
    
    # Create temp directory for expanded JSON
    script_dir = Path(__file__).parent
    temp_dir = script_dir / "temp"
    temp_dir.mkdir(exist_ok=True)
    
    # Generate expanded JSON filename
    issue_number = json.loads(issue_json_path.read_text()).get('number', 'unknown')
    expanded_json_path = temp_dir / f"issue_{issue_number}_expanded.json"
    
    try:
        # Step 1: Expand issue JSON
        expand_issue_json(issue_json_path, expanded_json_path)
        
        # Step 2: Generate test case
        test_generated = generate_test_case(repo_path, expanded_json_path)
        
        if not test_generated:
            print("\n" + "=" * 80)
            print("ERROR: Test case file was not generated successfully!")
            print("=" * 80)
            print("Please check the AI output above and ensure the test file was created.")
            if issue_number != 'unknown':
                print(f"The expected filename is: test{issue_number}.py")
            sys.exit(1)
        
        print(f"\n✓ Test file verification passed. Proceeding to Docker tests...")
        
        # Step 3: Run Docker tests
        # Use expanded_json_path instead of issue_json_path to include patch information
        tests_passed = run_docker_tests(repo_path, dockerfile_path, expanded_json_path)
        
        if tests_passed:
            print(f"\n{'='*80}")
            print("✓ All steps completed!")
            print(f"{'='*80}")
        else:
            print(f"\n{'='*80}")
            print("⚠ Tests may have failed, please check output")
            print(f"{'='*80}")
            sys.exit(1)
        
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

