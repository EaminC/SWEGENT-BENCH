#!/usr/bin/env python3
"""
Run Docker tests: Run tests on buggy version and fixed version
"""

import os
import sys
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Tuple


def get_pr_info(issue_json_path: Path) -> Optional[dict]:
    """Get PR information from issue JSON"""
    with open(issue_json_path, 'r', encoding='utf-8') as f:
        issue_data = json.load(f)
    
    linked_prs = issue_data.get('linked_prs', [])
    if not linked_prs:
        print("Error: Issue has no linked PR")
        return None
    
    # Get first PR (should only have one)
    pr = linked_prs[0]
    return pr


def get_base_sha(pr_info: dict) -> Optional[str]:
    """Get PR base SHA (version before fix)"""
    return pr_info.get('base_sha')


def get_head_sha(pr_info: dict) -> Optional[str]:
    """Get PR head SHA (version after fix)"""
    return pr_info.get('head_sha')


def apply_patch(repo_path: Path, patch_content: str) -> bool:
    """Apply patch to repository"""
    try:
        # Create temporary patch file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        # Apply patch using git apply
        cmd = ['git', 'apply', patch_file]
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        # Clean up temporary file
        os.unlink(patch_file)
        
        if result.returncode != 0:
            print(f"Warning: git apply failed: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"Error: Failed to apply patch: {e}")
        return False


def checkout_commit(repo_path: Path, sha: str) -> bool:
    """Checkout specified commit"""
    try:
        cmd = ['git', 'checkout', sha]
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: Cannot checkout commit {sha}: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"Error: Failed to checkout commit: {e}")
        return False


def find_test_file(repo_path: Path, issue_number: int) -> Optional[Path]:
    """Find test file"""
    # Possible test file names (in order of preference)
    test_patterns = [
        f"test{issue_number}.py",  # Preferred format: test128.py
        f"test_issue_{issue_number}.py",
        f"test_issue_{issue_number}_test.py",
        f"test{issue_number}_test.py",
        f"test_issue_{issue_number}.js",
    ]
    
    # Search in repo root directory first
    for pattern in test_patterns:
        test_file = repo_path / pattern
        if test_file.exists():
            return test_file
    
    # Search in all directories
    for pattern in test_patterns:
        matches = list(repo_path.rglob(pattern))
        if matches:
            return matches[0]
    
    return None


def check_docker_available() -> Tuple[bool, Optional[str]]:
    """
    Check if Docker is available and accessible
    
    Returns:
        (is_available, error_message)
    """
    # First check if docker command exists
    try:
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False, "Docker command exists but --version failed"
    except FileNotFoundError:
        return False, "Docker command not found in PATH"
    except subprocess.TimeoutExpired:
        return False, "Docker command timed out"
    
    # Then check if we can actually use Docker (permission check)
    try:
        result = subprocess.run(
            ['docker', 'ps'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, None
        else:
            # Check if it's a permission error
            error_output = result.stderr.lower()
            if 'permission denied' in error_output or 'dial unix' in error_output:
                return False, "Permission denied: User not in docker group"
            else:
                return False, f"Docker ps failed: {result.stderr[:100]}"
    except subprocess.TimeoutExpired:
        return False, "Docker ps command timed out"
    except Exception as e:
        return False, f"Error checking Docker access: {str(e)}"


def run_test_in_docker(repo_path: Path, dockerfile_path: Path, test_file: Path, version_name: str) -> Tuple[bool, str]:
    """
    Run test in Docker
    
    Returns:
        (success, output)
    """
    # Check if Docker is available
    docker_available, docker_error = check_docker_available()
    if not docker_available:
        error_msg = f"Docker is not available: {docker_error}\n"
        if "permission denied" in docker_error.lower() or "docker group" in docker_error.lower():
            error_msg += (
                "\nTo fix this, add your user to the docker group:\n"
                "  sudo usermod -aG docker $USER\n"
                "  newgrp docker  # or log out and back in\n"
            )
        else:
            error_msg += "Please ensure Docker is installed and in your PATH.\n"
        error_msg += "You can check by running: docker --version"
        return False, error_msg
    
    print(f"\nRunning test in Docker ({version_name})...")
    
    # Build Docker image
    image_name = f"test-{version_name.lower().replace(' ', '-')}"
    print(f"Building Docker image: {image_name}")
    
    # Remove old image if it exists to force rebuild
    print(f"  Removing old image if exists...")
    subprocess.run(['docker', 'rmi', '-f', image_name], capture_output=True, text=True)
    
    # Check if Dockerfile needs platform specification
    dockerfile_content = dockerfile_path.read_text()
    needs_platform_fix = 'FROM --platform=' not in dockerfile_content and 'FROM' in dockerfile_content
    
    # Create a temporary Dockerfile with platform fix if needed
    temp_dockerfile = None
    if needs_platform_fix:
        print(f"  ⚠ Dockerfile missing platform specification, creating temporary fix...")
        import re
        # Replace FROM statements with platform specification
        fixed_content = re.sub(
            r'^FROM\s+(\S+)',
            r'FROM --platform=linux/amd64 \1',
            dockerfile_content,
            flags=re.MULTILINE
        )
        # Create temporary Dockerfile
        temp_dockerfile = repo_path / f".dockerfile.{version_name.replace(' ', '_')}.tmp"
        temp_dockerfile.write_text(fixed_content)
        dockerfile_to_use = temp_dockerfile
        print(f"  Created temporary Dockerfile: {temp_dockerfile}")
    else:
        dockerfile_to_use = dockerfile_path
    
    try:
        # Build with explicit platform to avoid architecture mismatches
        # Use --no-cache to ensure fresh build
        build_cmd = [
            'docker', 'build',
            '--platform', 'linux/amd64',  # Force amd64 platform
            '--no-cache',  # Force rebuild without cache
            '--build-arg', 'BUILDPLATFORM=linux/amd64',  # Additional build arg
            '-f', str(dockerfile_to_use),
            '-t', image_name,
            str(repo_path)
        ]
        
        print(f"  Build command: {' '.join(build_cmd)}")
        result = subprocess.run(build_cmd, capture_output=True, text=True)
        if result.returncode != 0:
            error_msg = f"Docker build failed: {result.stderr}"
            # Check if it's an architecture issue
            if 'cannot execute binary file' in error_msg.lower() or 'wrong architecture' in error_msg.lower():
                error_msg += "\n\nNote: Architecture mismatch detected. The Dockerfile may need to specify the target platform."
            return False, error_msg
        
        # Verify the image platform
        print(f"  Verifying image platform...")
        inspect_cmd = ['docker', 'inspect', '--format', '{{.Architecture}}', image_name]
        inspect_result = subprocess.run(inspect_cmd, capture_output=True, text=True)
        if inspect_result.returncode == 0:
            arch = inspect_result.stdout.strip()
            print(f"  Image architecture: {arch}")
            if arch not in ['amd64', 'x86_64']:
                print(f"  ⚠ Warning: Image is {arch}, but we need amd64/x86_64")
    finally:
        # Clean up temporary Dockerfile
        if temp_dockerfile and temp_dockerfile.exists():
            temp_dockerfile.unlink()
            print(f"  Cleaned up temporary Dockerfile")
    
    # Run test
    # Use absolute path since docker run executes in container
    test_relative_path = test_file.relative_to(repo_path)
    
    # Try different test run methods
    run_commands = [
        # Method 1: Run python file directly (most reliable)
        ['python3', str(test_relative_path)],
        # Method 2: Run as unittest module
        ['python3', '-m', 'unittest', str(test_relative_path).replace('.py', '').replace('/', '.')],
        # Method 3: Use python -m unittest discover
        ['python3', '-m', 'unittest', 'discover', '-s', str(test_relative_path.parent), '-p', test_file.name],
    ]
    
    for i, run_cmd in enumerate(run_commands, 1):
        # Build docker run command with platform specification
        # Use --platform flag and ensure we're using the correct architecture
        cmd = [
            'docker', 'run', '--rm',
            '--platform', 'linux/amd64',  # Force amd64 platform
            '--env', 'PYTHONUNBUFFERED=1',  # Ensure Python output is unbuffered
            '-v', f'{repo_path}:/workspace',
            '-w', '/workspace',
            image_name
        ] + run_cmd
        
        print(f"  Trying method {i}: {' '.join(run_cmd)}")
        print(f"    Full command: docker run --platform linux/amd64 ...")
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        # Check for architecture mismatch errors
        error_output = (result.stderr or "").lower()
        stdout_output = (result.stdout or "").lower()
        combined_output = error_output + stdout_output
        
        if 'cannot execute binary file' in combined_output or 'wrong architecture' in combined_output:
            print(f"    ⚠ Architecture mismatch error detected!")
            print(f"    Error: {result.stderr[:200] if result.stderr else result.stdout[:200]}")
            
            # Try to check what's in the container
            print(f"    Checking container Python installation...")
            check_cmd = [
                'docker', 'run', '--rm',
                '--platform', 'linux/amd64',
                image_name,
                'file', '/usr/local/bin/python3'
            ]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=30)
            if check_result.returncode == 0:
                print(f"    Python info: {check_result.stdout.strip()}")
            
            # Try alternative Python paths
            print(f"    Trying alternative Python paths...")
            alt_python_paths = ['python', '/usr/bin/python3', 'python3.9', 'python3.10', 'python3.11']
            for alt_python in alt_python_paths:
                alt_cmd = [
                    'docker', 'run', '--rm',
                    '--platform', 'linux/amd64',
                    '-v', f'{repo_path}:/workspace',
                    '-w', '/workspace',
                    image_name,
                    alt_python, str(test_relative_path)
                ]
                alt_result = subprocess.run(alt_cmd, capture_output=True, text=True, timeout=300)
                if alt_result.returncode == 0:
                    print(f"    ✓ Success with {alt_python}!")
                    return True, alt_result.stdout + alt_result.stderr
                elif 'cannot execute' not in (alt_result.stderr or "").lower():
                    # If we got a different error (not architecture), this Python works
                    return False, alt_result.stdout + alt_result.stderr
        
        # Return if successful or has meaningful output
        if result.returncode == 0:
            return True, result.stdout + result.stderr
        elif result.stdout or result.stderr:
            # If we got output, return it (even if exit code is non-zero)
            # This helps with debugging
            return False, result.stdout + result.stderr
    
    return False, "All test run methods failed. Architecture mismatch may be the issue. Check Dockerfile base image."


def run_docker_tests(repo_path: Path, dockerfile_path: Path, issue_json_path: Path):
    """Main function to run Docker tests"""
    print(f"\n{'='*80}")
    print("Running Docker Tests")
    print(f"{'='*80}")
    
    # Read issue information first to get issue number
    with open(issue_json_path, 'r', encoding='utf-8') as f:
        issue_data = json.load(f)
    
    issue_number = issue_data.get('number')
    
    # Check Docker availability
    docker_available, docker_error = check_docker_available()
    if not docker_available:
        print("\n" + "=" * 80)
        print("ERROR: Docker is not available")
        print("=" * 80)
        print(f"Docker check failed: {docker_error}")
        
        # Provide specific fix based on error type
        if "permission denied" in docker_error.lower() or "docker group" in docker_error.lower():
            print("\n" + "=" * 80)
            print("PERMISSION ISSUE DETECTED")
            print("=" * 80)
            print("Your user is not in the docker group.")
            print("\nTo fix this:")
            print("1. Add your user to the docker group:")
            print("   sudo usermod -aG docker $USER")
            print("2. Apply the new group membership:")
            print("   newgrp docker")
            print("   # OR log out and log back in")
            print("3. Verify with: docker ps")
        else:
            print("\nPlease:")
            print("1. Install Docker: https://docs.docker.com/get-docker/")
            print("2. Ensure Docker is in your PATH")
            print("3. Verify with: docker --version")
        
        # Try to find test file to suggest manual run command
        test_file = find_test_file(repo_path, issue_number) if issue_number else None
        if test_file:
            print(f"\nAlternatively, you can run the test manually (without Docker):")
            print(f"   cd {repo_path}")
            print(f"   python3 {test_file.name}")
        else:
            print(f"\nAlternatively, you can run the test manually after finding it in: {repo_path}")
        
        return False
    
    pr_info = get_pr_info(issue_json_path)
    
    if not pr_info:
        print("Error: Cannot get PR information")
        return False
    
    # Get patch
    patch_content = pr_info.get('patch')
    if not patch_content:
        print("Warning: PR has no patch information, will try using git checkout")
        use_patch = False
    else:
        use_patch = True
    
    # Save current git state
    original_branch = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    original_sha = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=repo_path,
        capture_output=True,
        text=True
    ).stdout.strip()
    
    print(f"Current branch: {original_branch}")
    print(f"Current SHA: {original_sha}")
    
    try:
        # Find test file
        test_file = find_test_file(repo_path, issue_number)
        if not test_file:
            print(f"Error: Cannot find test file (issue #{issue_number})")
            print("Please ensure test file has been generated")
            return False
        
        print(f"Found test file: {test_file}")
        
        # Test 1: Run on buggy version (before applying patch)
        print(f"\n{'='*80}")
        print("Test 1: Buggy Version (before applying patch)")
        print(f"{'='*80}")
        
        if use_patch:
            # Restore to base state
            base_sha = get_base_sha(pr_info)
            if base_sha:
                if not checkout_commit(repo_path, base_sha):
                    print("Warning: Cannot checkout base SHA, using current state")
            else:
                print("Warning: No base SHA found in PR info, using current state")
        else:
            print("Note: No patch information, using current git state as buggy version")
        
        success_before, output_before = run_test_in_docker(
            repo_path, dockerfile_path, test_file, "Buggy Version"
        )
        
        print(f"\nBuggy version test result: {'PASS' if not success_before else 'FAIL'}")
        print("Output:")
        print(output_before)
        
        expected_before = not success_before  # Buggy version should fail
        
        # Test 2: Run on fixed version (after applying patch)
        print(f"\n{'='*80}")
        print("Test 2: Fixed Version (after applying patch)")
        print(f"{'='*80}")
        
        if use_patch and patch_content:
            # Apply patch
            if not apply_patch(repo_path, patch_content):
                print("Warning: Cannot apply patch, trying to checkout head SHA")
                head_sha = get_head_sha(pr_info)
                if head_sha:
                    checkout_commit(repo_path, head_sha)
        else:
            head_sha = get_head_sha(pr_info)
            if head_sha:
                if not checkout_commit(repo_path, head_sha):
                    print("Warning: Cannot checkout head SHA")
        
        success_after, output_after = run_test_in_docker(
            repo_path, dockerfile_path, test_file, "Fixed Version"
        )
        
        print(f"\nFixed version test result: {'PASS' if success_after else 'FAIL'}")
        print("Output:")
        print(output_after)
        
        expected_after = success_after  # Fixed version should pass
        
        # Summary
        print(f"\n{'='*80}")
        print("Test Summary")
        print(f"{'='*80}")
        print(f"Buggy version test: {'✓ Failed as expected' if expected_before else '✗ Unexpectedly passed'}")
        print(f"Fixed version test: {'✓ Passed as expected' if expected_after else '✗ Unexpectedly failed'}")
        
        if expected_before and expected_after:
            print("\n✓ Test verification successful!")
            return True
        else:
            print("\n⚠ Test results do not match expectations")
            return False
        
    finally:
        # Restore original state
        print(f"\nRestoring git state to: {original_branch} ({original_sha})")
        try:
            # First try to reset all changes
            subprocess.run(['git', 'reset', '--hard', original_sha], cwd=repo_path, check=False)
            # Then checkout to original branch
            subprocess.run(['git', 'checkout', original_branch], cwd=repo_path, check=False)
        except Exception as e:
            print(f"Warning: Error restoring git state: {e}")
            print("Please manually restore git state")


def main():
    """Main function"""
    if len(sys.argv) < 4:
        print("Usage: python run_docker_tests.py <repo_path> <dockerfile_path> <issue_json_path>")
        sys.exit(1)
    
    repo_path = Path(sys.argv[1]).resolve()
    dockerfile_path = Path(sys.argv[2]).resolve()
    issue_json_path = Path(sys.argv[3]).resolve()
    
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
    
    success = run_docker_tests(repo_path, dockerfile_path, issue_json_path)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
