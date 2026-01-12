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
from typing import Optional, Tuple, Dict


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


def force_clean_repo(repo_path: Path, protected_paths: list[Path] = None):
    """
    Force cleans the repository to remove untracked files (like .prettierrc.toml)
    BUT preserves critical generated files (Dockerfile, test scripts).
    """
    try:
        print(f"   Cleaning repository at {repo_path}...")
        
        # 1. Reset tracked files to HEAD (reverts modifications to tracked files)
        #    This does NOT delete new untracked files.
        subprocess.run(
            ['git', 'reset', '--hard', 'HEAD'], 
            cwd=repo_path, 
            check=True, 
            capture_output=True
        )
        
        # 2. Build git clean command with exclusions
        clean_cmd = ['git', 'clean', '-fd']
        
        if protected_paths:
            for p in protected_paths:
                try:
                    # git clean -e requires paths relative to the repo root
                    # We convert absolute paths to relative ones
                    if p.is_absolute():
                        rel_path = p.relative_to(repo_path.resolve())
                    else:
                        rel_path = p
                    
                    # Add exclusion flag
                    clean_cmd.extend(['-e', str(rel_path)])
                    print(f"   Note: Protecting file {rel_path}")
                except ValueError:
                    # File is outside repo (e.g. /tmp/...), safe from git clean
                    pass

        # 3. Run git clean (Removes untracked files EXCEPT protected ones)
        result = subprocess.run(
            clean_cmd, 
            cwd=repo_path, 
            check=True, 
            capture_output=True,
            text=True
        )
        
        print(f"   ✓ Repository cleaned (preserved protected files).")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error cleaning repository: {e.stderr if e.stderr else str(e)}")
        return False

def apply_patch(repo_path: Path, patch_content: str) -> bool:
    """Apply patch to repository with multiple strategies"""
    try:
        # Create temporary patch file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.patch', delete=False) as f:
            f.write(patch_content)
            patch_file = f.name
        
        # Strategy 1: Try direct apply
        cmd = ['git', 'apply', patch_file]
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        if result.returncode == 0:
            os.unlink(patch_file)
            return True
        
        print(f"Warning: Direct git apply failed: {result.stderr[:200]}")
        
        # Strategy 2: Try 3-way merge
        cmd = ['git', 'apply', '--3way', patch_file]
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✓ Patch applied using 3-way merge")
            os.unlink(patch_file)
            return True
        
        print(f"Warning: 3-way merge failed: {result.stderr[:200]}")
        
        # Strategy 3: Try with reject files (partial apply)
        cmd = ['git', 'apply', '--reject', patch_file]
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("⚠ Patch applied with some rejections (check .rej files)")
            os.unlink(patch_file)
            return True
        
        # Clean up temporary file
        os.unlink(patch_file)
        print(f"Error: All patch application strategies failed")
        return False
        
    except Exception as e:
        print(f"Error: Failed to apply patch: {e}")
        return False


def checkout_commit(repo_path: Path, sha: str) -> bool:
    """Checkout specified commit with improved error handling"""
    try:
        # First check if commit exists locally
        check_cmd = ['git', 'cat-file', '-e', sha]
        check_result = subprocess.run(check_cmd, cwd=repo_path, capture_output=True)
        
        if check_result.returncode != 0:
            print(f"Warning: Commit {sha} does not exist in local repository")
            print("  Attempting to fetch from remote...")
            
            # Try to fetch from all remotes
            fetch_result = subprocess.run(
                ['git', 'fetch', '--all'],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if fetch_result.returncode == 0:
                # Check again after fetch
                check_result = subprocess.run(check_cmd, cwd=repo_path, capture_output=True)
                if check_result.returncode != 0:
                    print(f"Error: Commit {sha} not found even after fetch")
                    print("  This commit may be in a different repository or was never pushed")
                    return False
                else:
                    print("  ✓ Commit found after fetch")
            else:
                print(f"Error: Failed to fetch from remote: {fetch_result.stderr}")
                return False
        
        # Now try to checkout
        cmd = ['git', 'checkout', sha]
        result = subprocess.run(cmd, cwd=repo_path, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(f"Error: Cannot checkout commit {sha}: {result.stderr}")
            return False
        
        return True
    except Exception as e:
        print(f"Error: Failed to checkout commit: {e}")
        return False


def validate_repo_structure(repo_path: Path) -> Dict[str, bool]:
    """Check repository structure for common files/directories"""
    structure = {
        'has_tests_dir': (repo_path / 'tests').exists(),
        'has_pyproject': (repo_path / 'pyproject.toml').exists(),
        'has_poetry_lock': (repo_path / 'poetry.lock').exists(),
        'has_package_json': (repo_path / 'package.json').exists(),
        'has_requirements_txt': (repo_path / 'requirements.txt').exists(),
        'has_setup_py': (repo_path / 'setup.py').exists(),
        'has_sdk_typescript': (repo_path / 'sdk' / 'typescript').exists(),
    }
    return structure


def classify_build_error(build_output: str) -> Dict[str, any]:
    """Classify build error and provide suggestions"""
    error_info = {
        'type': 'unknown',
        'severity': 'high',
        'suggestions': [],
        'can_retry': False
    }
    
    build_lower = build_output.lower()
    
    # Check for missing files/directories
    if 'not found' in build_lower:
        if '/tests' in build_output or 'tests/' in build_output or 'tests":' in build_output:
            error_info['type'] = 'missing_directory'
            error_info['suggestions'] = [
                'Check if tests/ directory exists before COPY',
                'Use conditional COPY: RUN if [ -d "tests" ]; then cp -r tests/ /app/tests/; fi',
                'Or create empty tests/ directory if needed'
            ]
            error_info['can_retry'] = True
        elif 'pyproject.toml' in build_output:
            error_info['type'] = 'missing_file'
            error_info['suggestions'] = [
                'Check if pyproject.toml exists before COPY',
                'Use conditional COPY or check file existence first'
            ]
            error_info['can_retry'] = True
        elif 'sdk/typescript' in build_output or 'sdk/typescript' in build_lower:
            error_info['type'] = 'missing_directory'
            error_info['suggestions'] = [
                'Check if sdk/typescript directory exists',
                'Use conditional COPY or skip if not needed'
            ]
            error_info['can_retry'] = True
    
    # Check for setuptools conflicts
    elif 'multiple top-level modules' in build_lower:
        error_info['type'] = 'setuptools_conflict'
        error_info['suggestions'] = [
            'Move test*.py files to tests/ directory before pip install',
            'Add to pyproject.toml: [tool.setuptools] exclude = ["test*.py"]',
            'Or use: pip install --no-build-isolation .[dev]'
        ]
        error_info['can_retry'] = True
    
    # Check for git/patch errors
    elif 'git apply failed' in build_lower or 'patch does not apply' in build_lower:
        error_info['type'] = 'patch_failed'
        error_info['suggestions'] = [
            'Try using --3way merge (already attempted)',
            'Use git checkout instead of patch',
            'Skip version switch and test current code'
        ]
        error_info['can_retry'] = True
    
    elif 'cannot checkout commit' in build_lower or 'reference is not a tree' in build_lower:
        error_info['type'] = 'git_checkout_failed'
        error_info['suggestions'] = [
            'Fetch from remote first (already attempted)',
            'Check if commit exists in repository',
            'Use current code state instead'
        ]
        error_info['can_retry'] = True
    
    # Check for dependency install failures
    elif 'pnpm install' in build_lower and 'exit code' in build_lower:
        error_info['type'] = 'dependency_install_failed'
        error_info['suggestions'] = [
            'Check network connectivity',
            'Use mirror sources: npm config set registry https://registry.npmmirror.com',
            'Add retry logic with exponential backoff'
        ]
        error_info['can_retry'] = True
    
    elif 'npm run build' in build_lower and 'exit code' in build_lower:
        error_info['type'] = 'build_failed'
        error_info['suggestions'] = [
            'Check TypeScript compilation errors',
            'Verify all dependencies are installed',
            'Check for missing dependencies in package.json'
        ]
        error_info['can_retry'] = True
    
    # Check for system config issues
    elif 'sources.list' in build_lower and 'no such file' in build_lower:
        error_info['type'] = 'system_config'
        error_info['suggestions'] = [
            'Debian new version uses /etc/apt/sources.list.d/ instead',
            'Check if file exists before modifying: if [ -f /etc/apt/sources.list ]; then ...'
        ]
        error_info['can_retry'] = True
    
    # Check for pnpm link --global issues
    elif 'pnpm link --global' in build_output or 'pnpm does not know where to store global binaries' in build_lower:
        error_info['type'] = 'pnpm_global_config'
        error_info['suggestions'] = [
            'Set PNPM_HOME environment variable: ENV PNPM_HOME=/root/.local/share/pnpm',
            'Add to PATH: ENV PATH="$PNPM_HOME:$PATH"',
            'Or remove --global flag from pnpm link command'
        ]
        error_info['can_retry'] = True
    
    # Check for externally-managed-environment (PEP 668)
    elif 'externally-managed-environment' in build_lower or 'pep 668' in build_lower:
        error_info['type'] = 'pep668_error'
        error_info['suggestions'] = [
            'Use virtual environment: RUN python3 -m venv /venv && /venv/bin/pip install ...',
            'Or use --break-system-packages flag: RUN pip install --break-system-packages ...',
            'Or use --user flag: RUN pip install --user ...'
        ]
        error_info['can_retry'] = True
    
    # Check for lxml compilation errors (missing C libraries)
    elif 'lxml' in build_lower and ('error' in build_lower or 'failed' in build_lower):
        if 'gcc' in build_lower or 'compilation' in build_lower or 'c extension' in build_lower:
            error_info['type'] = 'missing_c_libraries'
            error_info['suggestions'] = [
                'Install build dependencies: RUN apt-get update && apt-get install -y libxml2-dev libxslt1-dev python3-dev gcc',
                'For lxml specifically: RUN apt-get install -y libxml2-dev libxslt1-dev'
            ]
            error_info['can_retry'] = True
    
    # Check for poetry executable not found
    elif 'poetry executable not found' in build_lower or 'poetry: command not found' in build_lower:
        error_info['type'] = 'poetry_not_found'
        error_info['suggestions'] = [
            'Install poetry via pipx: RUN pipx install poetry',
            'Add pipx bin to PATH: ENV PATH="/root/.local/bin:$PATH"',
            'Or use pip: RUN pip install poetry'
        ]
        error_info['can_retry'] = True
    
    # Check for Rust project trying to use pip install
    elif 'cargo.toml' in build_lower and ('pip install' in build_lower or 'setup.py' in build_lower):
        error_info['type'] = 'rust_project_error'
        error_info['suggestions'] = [
            'This is a Rust project, not Python',
            'Remove pip install commands from Dockerfile',
            'Use cargo build instead: RUN cargo build --release'
        ]
        error_info['can_retry'] = False  # This is a fundamental error, retry won't help
    
    # Check for network errors
    elif 'network' in build_lower or 'timeout' in build_lower or 'could not connect' in build_lower:
        if 'docker.io' in build_output or 'auth.docker.io' in build_output:
            error_info['type'] = 'docker_network_error'
            error_info['suggestions'] = [
                'Check network connectivity',
                'Retry Docker build with --network=host',
                'Use Docker mirror if available'
            ]
            error_info['can_retry'] = True
        else:
            error_info['type'] = 'network_error'
            error_info['suggestions'] = [
                'Check network connectivity',
                'Add retry logic to install commands',
                'Use mirror sources for package managers'
            ]
            error_info['can_retry'] = True
    
    # Check for Windows path separator issues
    elif '\\\\' in build_output or '\\test' in build_output.lower():
        error_info['type'] = 'path_separator_error'
        error_info['suggestions'] = [
            'Use forward slashes in paths: /workspace/tests/test350.py',
            'Normalize paths: RUN python3 /workspace/tests/test350.py',
            'Check path handling in test execution'
        ]
        error_info['can_retry'] = True
    
    # Check for ModuleNotFoundError with 'platform' module
    elif 'modulenotfounderror' in build_lower and 'platform' in build_lower:
        if 'platform.reworkd_platform' in build_output or "'platform' is not a package" in build_output:
            error_info['type'] = 'module_import_error'
            error_info['suggestions'] = [
                'Check Python path configuration',
                'Ensure the repository root is in PYTHONPATH',
                'Use absolute imports instead of relative imports',
                'Check if there is a directory named "platform" conflicting with Python stdlib'
            ]
            error_info['can_retry'] = True
    
    return error_info


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
    
    # Search in tests/ directory first (preferred location)
    tests_dir = repo_path / 'tests'
    if tests_dir.exists():
        for pattern in test_patterns:
            test_file = tests_dir / pattern
            if test_file.exists():
                return test_file
    
    # Search in repo root directory
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
    # Ensure path uses forward slashes for Docker compatibility (normalize all backslashes)
    test_relative_path_str = str(test_relative_path).replace('\\', '/')
    # Also normalize the parent directory path
    test_parent_path = str(test_file.parent).replace('\\', '/')
    
    # Use absolute path in container to avoid path issues
    test_absolute_path = f"/workspace/{test_relative_path_str}"
    
    # Try different test run methods
    run_commands = [
        # Method 1: Run python file directly with absolute path (most reliable)
        ['python3', test_absolute_path],
        # Method 2: Run with relative path (fallback)
        ['python3', test_relative_path_str],
        # Method 3: Run as unittest module
        ['python3', '-m', 'unittest', test_relative_path_str.replace('.py', '').replace('/', '.')],
        # Method 4: Use python -m unittest discover
        ['python3', '-m', 'unittest', 'discover', '-s', test_parent_path, '-p', test_file.name],
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
                    alt_python, test_absolute_path if 'absolute' in locals() else test_relative_path_str
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
        
        # Classify errors if build failed
        if not success_before and 'Docker build failed' in output_before:
            error_info = classify_build_error(output_before)
            if error_info['type'] != 'unknown':
                print(f"\nError classification: {error_info['type']}")
                print("Suggestions:")
                for suggestion in error_info['suggestions']:
                    print(f"  - {suggestion}")
        
        expected_before = not success_before  # Buggy version should fail
        
        # Test 2: Run on fixed version (after applying patch)
        print(f"\n{'='*80}")
        print("Test 2: Fixed Version (after applying patch)")
        print(f"{'='*80}")
        
        if use_patch and patch_content:
            # Apply patch
            if not apply_patch(repo_path, patch_content):
                print("Warning: Cannot apply patch, trying to checkout head SHA")
                force_clean_repo(repo_path, protected_paths=[dockerfile_path, test_file])
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
        
        # Classify errors if build failed
        if not success_after and 'Docker build failed' in output_after:
            error_info = classify_build_error(output_after)
            if error_info['type'] != 'unknown':
                print(f"\nError classification: {error_info['type']}")
                print("Suggestions:")
                for suggestion in error_info['suggestions']:
                    print(f"  - {suggestion}")
        
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
