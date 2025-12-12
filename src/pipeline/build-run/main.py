#!/usr/bin/env python3
"""
Pipeline for building Docker images with iterative feedback.
Generates claude.dockerfile, attempts to build, and uses agent feedback to improve.
"""

import os
import sys
import json
import re
import subprocess
import argparse
from pathlib import Path
from typing import Tuple, Optional

# Add parent directories to path to import forge api
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from forge.api import LLMClient

# Import agentless initialization
import importlib.util


def agentless_init_dockerfile(repo_path: Path) -> bool:
    """
    Use agentless method to initialize env.dockerfile
    
    Args:
        repo_path: Path to repository
        
    Returns:
        True if initialization succeeded, False otherwise
    """
    print(f"\n{'='*80}")
    print("Agentless Initialization: Generating env.dockerfile")
    print(f"{'='*80}")
    
    # Locate the docker-build-init script
    project_root = Path(__file__).parent.parent.parent.parent  # SWEGENT-BENCH root
    init_script = project_root / "source" / "tools" / "docker-build-init" / "main.py"
    
    if not init_script.exists():
        print(f"Warning: Agentless init script not found: {init_script}")
        print("Skipping agentless initialization, will start from scratch")
        return False
    
    try:
        # Load the module dynamically
        spec = importlib.util.spec_from_file_location("docker_build_init", init_script)
        if spec is None or spec.loader is None:
            print(f"Error: Cannot load module from {init_script}")
            return False
            
        module = importlib.util.module_from_spec(spec)
        sys.modules["docker_build_init"] = module
        spec.loader.exec_module(module)
        
        # Call the run_docker_build_flow function
        print("Calling agentless generator...")
        result_path = module.run_docker_build_flow(repo_path)
        
        if result_path and result_path.exists():
            print(f"\n✓ env.dockerfile generated successfully: {result_path}")
            
            # Copy env.dockerfile as the starting point for claude.dockerfile
            claude_dockerfile = repo_path / "claude.dockerfile"
            claude_dockerfile.write_text(result_path.read_text())
            print(f"✓ Copied to claude.dockerfile as starting point")
            
            return True
        else:
            print("✗ env.dockerfile was not created")
            return False
            
    except Exception as e:
        print(f"Error during agentless initialization: {e}")
        import traceback
        traceback.print_exc()
        return False


def generate_dockerfile(repo_path: Path, feedback: Optional[str] = None, llm_client: Optional[LLMClient] = None) -> bool:
    """
    Generate claude.dockerfile using run_claude.py
    
    Args:
        repo_path: Path to repository
        feedback: Optional feedback from previous build attempt
        llm_client: Optional LLM client (not used, kept for compatibility)
        
    Returns:
        True if generation succeeded, False otherwise
    """
    print(f"\n{'='*80}")
    if feedback:
        print("Generating improved claude.dockerfile with feedback...")
    else:
        print("Generating claude.dockerfile...")
    print(f"{'='*80}")
    
    repo_build_script = Path(__file__).parent.parent.parent / "repo-build" / "claude" / "run_claude.py"
    
    if not repo_build_script.exists():
        print(f"Error: {repo_build_script} does not exist!")
        return False
    
    # If there's feedback, we need to pass it to the agent
    # We'll use environment variable to pass feedback to run_claude.py
    env = os.environ.copy()
    if feedback:
        env["DOCKERFILE_FEEDBACK"] = feedback
    
    # Build command
    cmd = [sys.executable, str(repo_build_script)]
    
    try:
        # Always run interactively - let run_claude.py handle the claude command
        # This allows claude to run in interactive mode and user can interact with it
        result = subprocess.run(
            cmd,
            cwd=repo_path,
            env=env
            # Don't capture output - let it go to terminal for interactive mode
        )
        
        if result.returncode == 0:
            print("\n✓ Dockerfile generation completed")
            return True
        else:
            print(f"\n✗ Dockerfile generation failed (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"Error generating Dockerfile: {e}")
        return False


def check_docker_permission() -> Tuple[bool, Optional[str]]:
    """
    Check if Docker is accessible (permission check)
    
    Returns:
        (is_accessible: bool, error_message: Optional[str])
    """
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            return True, None
        else:
            error_output = result.stderr.lower()
            if "permission denied" in error_output or "dial unix" in error_output:
                return False, "Docker permission denied. User may not be in docker group."
            else:
                return False, f"Docker check failed: {result.stderr[:100]}"
    except FileNotFoundError:
        return False, "Docker command not found. Please install Docker."
    except subprocess.TimeoutExpired:
        return False, "Docker check timed out."
    except Exception as e:
        return False, f"Error checking Docker: {str(e)}"


def build_docker_image(repo_path: Path, dockerfile_name: str = "claude.dockerfile") -> Tuple[bool, str]:
    """
    Attempt to build Docker image
    
    Args:
        repo_path: Path to repository
        dockerfile_name: Name of dockerfile to use
        
    Returns:
        (success: bool, output: str) - Build success status and output/error
    """
    print(f"\n{'='*80}")
    print("Building Docker image...")
    print(f"{'='*80}")
    
    # Check Docker permission first
    docker_accessible, docker_error = check_docker_permission()
    if not docker_accessible:
        error_msg = f"Docker is not accessible: {docker_error}\n\n"
        error_msg += "SOLUTION:\n"
        if "permission denied" in docker_error.lower() or "docker group" in docker_error.lower():
            error_msg += "1. Add your user to the docker group:\n"
            error_msg += "   sudo usermod -aG docker $USER\n"
            error_msg += "2. Apply the new group membership:\n"
            error_msg += "   newgrp docker  # or log out and back in\n"
            error_msg += "3. Verify with: docker ps\n"
        else:
            error_msg += "Please ensure Docker is installed and accessible.\n"
        return False, error_msg
    
    dockerfile_path = repo_path / dockerfile_name
    
    if not dockerfile_path.exists():
        return False, f"Dockerfile not found: {dockerfile_path}"
    
    # Build Docker image
    image_name = f"test-build-{repo_path.name.lower()}"
    cmd = [
        "docker", "build",
        "--platform", "linux/amd64",
        "-f", str(dockerfile_path),
        "-t", image_name,
        str(repo_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )
        
        output = result.stdout + result.stderr
        
        # Check if it's a permission error in the build output
        if result.returncode != 0 and ("permission denied" in output.lower() or "dial unix" in output.lower()):
            error_msg = output + "\n\n"
            error_msg += "NOTE: This appears to be a Docker permission issue, not a Dockerfile problem.\n"
            error_msg += "SOLUTION:\n"
            error_msg += "1. Add your user to the docker group:\n"
            error_msg += "   sudo usermod -aG docker $USER\n"
            error_msg += "2. Apply the new group membership:\n"
            error_msg += "   newgrp docker  # or log out and back in\n"
            error_msg += "3. Then re-run this pipeline\n"
            return False, error_msg
        
        if result.returncode == 0:
            print("✓ Docker build succeeded")
            return True, output
        else:
            print("✗ Docker build failed")
            return False, output
            
    except subprocess.TimeoutExpired:
        return False, "Docker build timed out after 10 minutes"
    except Exception as e:
        return False, f"Error building Docker image: {e}"


def ask_agent_if_successful(build_output: str, llm_client: LLMClient) -> bool:
    """
    Ask agent (subagent) if Docker build was successful
    
    Args:
        build_output: Output from Docker build
        llm_client: LLM client for agent communication
        
    Returns:
        True if agent says yes, False if no
    """
    system_prompt = """You are a subagent that analyzes Docker build output.
Your task is to determine if a Docker build was successful.
You must answer with ONLY "yes" or "no" - nothing else.
- "yes" if the build completed successfully
- "no" if the build failed or had errors"""
    
    user_message = f"""Analyze this Docker build output and answer with ONLY "yes" or "no":
Was the Docker build successful?

Build output:
{build_output}"""
    
    try:
        response = llm_client.simple_chat(
            user_message,
            system_prompt=system_prompt,
            temperature=0.1  # Low temperature for deterministic yes/no
        )
        
        # Clean response - get first word and lowercase
        response_clean = response.strip().lower().split()[0] if response.strip() else "no"
        
        print(f"\nAgent response: {response.strip()}")
        print(f"Interpreted as: {response_clean}")
        
        return response_clean == "yes"
        
    except Exception as e:
        print(f"Error asking agent: {e}")
        # Default to checking return code if agent fails
        return "error" not in build_output.lower() and "failed" not in build_output.lower()


def run_test_generation(repo_path: Path, dockerfile_path: Path, issue_json_path: Path) -> bool:
    """
    Run test generation using gen_test.py
    
    Args:
        repo_path: Path to repository
        dockerfile_path: Path to dockerfile
        issue_json_path: Path to issue JSON file
        
    Returns:
        True if test generation succeeded, False otherwise
    """
    print(f"\n{'='*80}")
    print("Generating test case...")
    print(f"{'='*80}")
    
    gen_test_script = Path(__file__).parent.parent.parent / "test-gen" / "gen_test.py"
    
    if not gen_test_script.exists():
        print(f"Error: {gen_test_script} does not exist!")
        return False
    
    # Build command
    cmd = [
        sys.executable,
        str(gen_test_script),
        str(dockerfile_path),
        str(issue_json_path)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            cwd=repo_path
            # Don't capture output - let it go to terminal
        )
        
        if result.returncode == 0:
            print("✓ Test generation completed")
            return True
        else:
            print(f"✗ Test generation failed (exit code: {result.returncode})")
            return False
    except Exception as e:
        print(f"Error generating test: {e}")
        return False


def run_test_verification(repo_path: Path, dockerfile_path: Path, issue_json_path: Path) -> Tuple[bool, bool, str]:
    """
    Run test verification (buggy version should fail, fixed version should pass)
    
    Args:
        repo_path: Path to repository
        dockerfile_path: Path to dockerfile
        issue_json_path: Path to issue JSON file
        
    Returns:
        (is_valid: bool, buggy_failed: bool, output: str)
        is_valid: True if buggy failed AND fixed passed
        buggy_failed: True if buggy version test failed
        output: Test output
    """
    print(f"\n{'='*80}")
    print("Running test verification...")
    print(f"{'='*80}")
    
    run_tests_script = Path(__file__).parent.parent.parent / "test-gen" / "run_docker_tests.py"
    
    if not run_tests_script.exists():
        return False, False, f"Error: {run_tests_script} does not exist!"
    
    # Check if expanded JSON exists (generated by test generation step)
    # If it exists, use it instead of the original issue JSON to include patch info
    test_gen_temp_dir = Path(__file__).parent.parent.parent / "test-gen" / "temp"
    issue_number = json.loads(issue_json_path.read_text()).get('number', 'unknown')
    expanded_json_path = test_gen_temp_dir / f"issue_{issue_number}_expanded.json"
    
    # Use expanded JSON if available, otherwise use original
    json_to_use = expanded_json_path if expanded_json_path.exists() else issue_json_path
    if expanded_json_path.exists():
        print(f"Using expanded JSON with patch information: {expanded_json_path}")
    else:
        print(f"Warning: Expanded JSON not found, using original (may not have patch info)")
    
    cmd = [
        sys.executable,
        str(run_tests_script),
        str(repo_path),
        str(dockerfile_path),
        str(json_to_use)
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minute timeout
        )
        
        output = result.stdout + result.stderr
        
        # Parse output to determine results
        # Look for "Buggy version test: ✓ Failed as expected" or "✗ Unexpectedly passed"
        # Look for "Fixed version test: ✓ Passed as expected" or "✗ Unexpectedly failed"
        buggy_failed = "Buggy version test: ✓ Failed as expected" in output
        fixed_passed = "Fixed version test: ✓ Passed as expected" in output
        
        # Also check return code - if it's 0, tests passed
        # But we need to verify the specific conditions
        is_valid = buggy_failed and fixed_passed
        
        # If return code is 0 and we have the expected messages, it's valid
        if result.returncode == 0 and is_valid:
            return True, buggy_failed, output
        # If return code is 0 but we don't have expected messages, check output more carefully
        elif result.returncode == 0:
            # Check if test verification was successful from output
            if "Test verification successful" in output:
                return True, buggy_failed, output
        
        return is_valid, buggy_failed, output
        
    except subprocess.TimeoutExpired:
        return False, False, "Test verification timed out after 30 minutes"
    except Exception as e:
        return False, False, f"Error running test verification: {e}"


def ask_agent_if_dockerfile_issue(test_output: str, llm_client: LLMClient) -> bool:
    """
    Ask subagent if test failures are due to Dockerfile issues (OLD METHOD - deprecated)
    
    Args:
        test_output: Test verification output
        llm_client: LLM client for agent communication
        
    Returns:
        True if agent says it's a Dockerfile issue, False otherwise
    """
    system_prompt = """You are a subagent that analyzes test failures.
Your task is to determine if test failures are caused by Dockerfile configuration issues.
You must answer with ONLY "yes" or "no" - nothing else.
- "yes" if the failures are likely due to Dockerfile configuration problems
- "no" if the failures are likely due to test code issues or other problems"""
    
    user_message = f"""Analyze this test output and answer with ONLY "yes" or "no":
Are the test failures likely caused by Dockerfile configuration issues?

Test output:
{test_output[:2000]}  # Limit length
"""
    
    try:
        response = llm_client.simple_chat(
            user_message,
            system_prompt=system_prompt,
            temperature=0.1
        )
        
        response_clean = response.strip().lower().split()[0] if response.strip() else "no"
        
        print(f"\nAgent response: {response.strip()}")
        print(f"Interpreted as: {response_clean}")
        
        return response_clean == "yes"
        
    except Exception as e:
        print(f"Error asking agent: {e}")
        return False


def cofix_both_files(repo_path: Path, dockerfile_path: Path, test_output: str, issue_json_path: Path) -> bool:
    """
    Ask agent to fix both Dockerfile and test file together based on test execution results
    
    Args:
        repo_path: Path to repository
        dockerfile_path: Path to Dockerfile
        test_output: Test execution output (failures)
        issue_json_path: Path to issue JSON
        
    Returns:
        True if agent successfully generated fixes, False otherwise
    """
    print(f"\n{'='*80}")
    print("Co-fix: Agent analyzing both Dockerfile and test file...")
    print(f"{'='*80}")
    
    # Read current files
    dockerfile_content = ""
    test_file_content = ""
    test_file_path = None
    
    try:
        dockerfile_content = dockerfile_path.read_text()
    except Exception as e:
        print(f"Error reading Dockerfile: {e}")
        return False
    
    # Find test file
    issue_data = json.loads(issue_json_path.read_text())
    issue_number = issue_data.get('number', 'unknown')
    test_file_path = repo_path / f"test{issue_number}.py"
    
    if not test_file_path.exists():
        print(f"Test file not found: {test_file_path}")
        return False
    
    try:
        test_file_content = test_file_path.read_text()
    except Exception as e:
        print(f"Error reading test file: {e}")
        return False
    
    # Build prompt for agent
    prompt = f"""You are a debugging expert. You need to fix BOTH the Dockerfile and the test file to make the tests pass.

IMPORTANT RULES:
1. Make ONLY the MINIMAL necessary changes
2. Fix BOTH files if needed, or just one if that's sufficient
3. Preserve existing functionality
4. Focus on making the tests pass

================================================================================
CURRENT DOCKERFILE ({dockerfile_path.name}):
================================================================================
{dockerfile_content}

================================================================================
CURRENT TEST FILE ({test_file_path.name}):
================================================================================
{test_file_content}

================================================================================
TEST EXECUTION OUTPUT (FAILURES):
================================================================================
{test_output[-3000:]}  # Last 3000 chars

================================================================================
YOUR TASK:
================================================================================
Analyze the test failures and determine what needs to be fixed in:
1. The Dockerfile (environment, dependencies, configuration)
2. The test file (test logic, assertions, setup)

Output your fixes in this EXACT format:

===DOCKERFILE_START===
[Complete fixed Dockerfile content]
===DOCKERFILE_END===

===TESTFILE_START===
[Complete fixed test file content]
===TESTFILE_END===

Remember: Make MINIMAL changes. Only fix what's broken."""

    print("\nSending files and test output to agent...")
    
    # Call LLM (using subprocess to call test-gen script with custom mode)
    # For now, we'll write the prompt to a temp file and use it
    try:
        cofix_script = Path(__file__).parent.parent.parent / "test-gen" / "cofix_agent.py"
        temp_prompt = Path("/tmp/cofix_prompt.txt")
        temp_prompt.write_text(prompt)
        
        # Call cofix agent
        result = subprocess.run(
            [sys.executable, str(cofix_script), str(temp_prompt)],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        if result.returncode != 0:
            print(f"Agent cofix failed: {result.stderr}")
            return False
        
        # Parse agent output
        output = result.stdout
        
        # Extract Dockerfile
        dockerfile_match = re.search(r'===DOCKERFILE_START===\n(.*?)\n===DOCKERFILE_END===', output, re.DOTALL)
        if dockerfile_match:
            new_dockerfile = dockerfile_match.group(1)
            dockerfile_path.write_text(new_dockerfile)
            print(f"✓ Updated Dockerfile")
        
        # Extract test file
        testfile_match = re.search(r'===TESTFILE_START===\n(.*?)\n===TESTFILE_END===', output, re.DOTALL)
        if testfile_match:
            new_testfile = testfile_match.group(1)
            test_file_path.write_text(new_testfile)
            print(f"✓ Updated test file")
        
        if not dockerfile_match and not testfile_match:
            print("⚠ Agent did not provide files in expected format")
            return False
        
        return True
        
    except subprocess.TimeoutExpired:
        print("Agent cofix timed out")
        return False
    except Exception as e:
        print(f"Error during cofix: {e}")
        return False


def get_feedback_for_agent(build_output: str, iteration: int) -> str:
    """
    Format build output as feedback for agent
    
    Args:
        build_output: Output from Docker build
        iteration: Current iteration number
        
    Returns:
        Formatted feedback string
    """
    feedback = f"""The Docker build failed on iteration {iteration}.

Build output:
{build_output}

Please analyze the error and generate an improved Dockerfile that fixes these issues.
Focus on the specific errors shown in the output above."""
    
    return feedback


def main():
    parser = argparse.ArgumentParser(
        description="Pipeline for building Docker images with iterative feedback"
    )
    parser.add_argument(
        "--max-dockerfile-retries",
        type=int,
        default=1,
        metavar="N",
        help="Maximum number of Dockerfile generation retries (default: 1)"
    )
    parser.add_argument(
        "-d", "--dockerfile",
        type=str,
        default="claude.dockerfile",
        help="Dockerfile name (default: claude.dockerfile)"
    )
    parser.add_argument(
        "--max-test-retries",
        type=int,
        default=3,
        metavar="N",
        help="Maximum number of test generation retries (default: 3)"
    )
    parser.add_argument(
        "--max-cofix-retries",
        type=int,
        default=2,
        metavar="N",
        help="Maximum number of co-fix retries (default: 2)"
    )
    parser.add_argument(
        "--issue-json",
        type=str,
        metavar="PATH",
        help="Path to issue JSON file (required for test generation)"
    )
    parser.add_argument(
        "--enable-cofix",
        action="store_true",
        help="Enable co-fix mode: if test failures are due to Dockerfile issues, regenerate both Dockerfile and test together (default: disabled)"
    )
    parser.add_argument(
        "--use-agentless-init",
        action="store_true",
        help="Use agentless method to generate initial Dockerfile before agent loop (default: disabled, recommended for better starting point)"
    )
    parser.add_argument(
        "repo_path",
        type=str,
        nargs="?",
        default=".",
        help="Path to repository (default: current directory)"
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    repo_path = Path(args.repo_path).resolve()
    if not repo_path.exists():
        print(f"Error: Repository path does not exist: {repo_path}")
        sys.exit(1)
    
    print(f"\n{'='*80}")
    print("Docker Build Pipeline with Agent Feedback")
    print(f"{'='*80}")
    print(f"Repository: {repo_path}")
    print(f"Dockerfile: {args.dockerfile}")
    print(f"Max Dockerfile retries: {args.max_dockerfile_retries}")
    if args.issue_json:
        print(f"Max test retries: {args.max_test_retries}")
        print(f"Issue JSON: {args.issue_json}")
    print(f"Co-fix mode: {'Enabled' if args.enable_cofix else 'Disabled'}")
    if args.enable_cofix:
        print(f"Max co-fix retries: {args.max_cofix_retries}")
    print(f"Agentless init: {'Enabled' if args.use_agentless_init else 'Disabled'}")
    print(f"{'='*80}")
    
    # Validate issue_json if provided
    issue_json_path = None
    if args.issue_json:
        issue_json_path = Path(args.issue_json).resolve()
        if not issue_json_path.exists():
            print(f"Error: Issue JSON file does not exist: {issue_json_path}")
            sys.exit(1)
    
    # Initialize LLM client for agent
    llm_client = LLMClient()
    
    dockerfile_path = repo_path / args.dockerfile
    
    # ============================================================================
    # Phase 0: Agentless Initialization (Optional)
    # ============================================================================
    if args.use_agentless_init:
        print(f"\n{'='*80}")
        print("PHASE 0: Agentless Initialization")
        print(f"{'='*80}")
        
        agentless_success = agentless_init_dockerfile(repo_path)
        if agentless_success:
            print("\n✓ Agentless initialization completed successfully")
            print("  Starting agent loop from initialized Dockerfile...")
        else:
            print("\n⚠ Agentless initialization failed")
            print("  Starting agent loop from scratch...")
    else:
        print(f"\n{'='*80}")
        print("PHASE 0: Agentless Initialization - SKIPPED")
        print(f"{'='*80}")
        print("Starting agent loop from scratch (use --use-agentless-init to enable initialization)")
    
    # ============================================================================
    # Phase 1: Dockerfile Generation Loop
    # ============================================================================
    print(f"\n{'='*80}")
    print("PHASE 1: Dockerfile Generation (Agent Loop)")
    print(f"{'='*80}")
    
    dockerfile_feedback = None
    dockerfile_success = False
    
    for iteration in range(1, args.max_dockerfile_retries + 1):
        print(f"\n{'='*80}")
        print(f"Dockerfile Retry {iteration}/{args.max_dockerfile_retries}")
        print(f"{'='*80}")
        
        # Step 1: Generate Dockerfile
        if not generate_dockerfile(repo_path, dockerfile_feedback, llm_client):
            print("Failed to generate Dockerfile")
            if iteration < args.max_dockerfile_retries:
                print("Continuing to next iteration...")
                continue
            else:
                print("Max iterations reached.")
                break
        
        # Check if dockerfile was created
        if not dockerfile_path.exists():
            print(f"Error: Dockerfile was not created: {dockerfile_path}")
            if iteration < args.max_dockerfile_retries:
                print("Continuing to next iteration...")
                continue
            else:
                print("Max iterations reached.")
                break
        
        # Step 2: Build Docker image
        build_success, build_output = build_docker_image(repo_path, args.dockerfile)
        
        # Check if it's a Docker permission/system issue
        is_permission_error = (
            "permission denied" in build_output.lower() or 
            "dial unix" in build_output.lower() or
            "docker group" in build_output.lower()
        )
        
        if is_permission_error:
            print("\n" + "=" * 80)
            print("⚠ Docker Permission Error Detected")
            print("=" * 80)
            print("This is a system-level Docker permission issue, not a Dockerfile problem.")
            print("\nPlease fix the Docker permission issue and re-run the pipeline.")
            print("=" * 80)
            sys.exit(1)
        
        # Show build output for debugging
        if not build_success:
            print("\nBuild output/errors:")
            print("-" * 80)
            output_lines = build_output.split('\n')
            if len(output_lines) > 50:
                print("\n".join(output_lines[-50:]))
                print(f"\n... (showing last 50 lines of {len(output_lines)} total lines)")
            else:
                print(build_output)
            print("-" * 80)
        
        # Step 3: Ask agent if build was successful
        agent_says_success = ask_agent_if_successful(build_output, llm_client)
        
        if build_success and agent_says_success:
            print(f"\n✓ Dockerfile build successful!")
            dockerfile_success = True
            break
        else:
            print(f"\n✗ Build failed (iteration {iteration})")
            if iteration < args.max_dockerfile_retries:
                dockerfile_feedback = get_feedback_for_agent(build_output, iteration)
                print("Preparing feedback for next retry...")
            else:
                print("Max Dockerfile retries reached.")
    
    if not dockerfile_success:
        print("\nDockerfile generation did not succeed. Cannot proceed to test generation.")
        if not args.issue_json:
            sys.exit(1)
    
    # ============================================================================
    # Phase 2: Test Generation Loop (if issue_json provided)
    # ============================================================================
    if not args.issue_json:
        print(f"\n{'='*80}")
        print("✓ Pipeline completed successfully!")
        print(f"{'='*80}")
        print(f"Dockerfile: {dockerfile_path}")
        sys.exit(0)
    
    print(f"\n{'='*80}")
    print("PHASE 2: Test Generation")
    print(f"{'='*80}")
    
    test_feedback = None
    test_success = False
    full_loop_active = False
    max_full_loop = 3  # Maximum full loop iterations
    full_loop_iteration = 0
    
    # Outer loop: Full loop (Dockerfile + Test) if enabled and Dockerfile issue detected
    while True:
        if full_loop_active:
            full_loop_iteration += 1
            if full_loop_iteration > max_full_loop:
                print("\nMax full loop iterations reached.")
                break
            
            print(f"\n{'='*80}")
            print(f"FULL LOOP Iteration {full_loop_iteration}/{max_full_loop}")
            print(f"{'='*80}")
            print("Regenerating both Dockerfile and test...")
            
            # Reset and regenerate Dockerfile
            dockerfile_feedback = None
            dockerfile_success = False
            
            for iteration in range(1, args.max_dockerfile_retries + 1):
                if not generate_dockerfile(repo_path, dockerfile_feedback, llm_client):
                    continue
                if not dockerfile_path.exists():
                    continue
                build_success, build_output = build_docker_image(repo_path, args.dockerfile)
                agent_says_success = ask_agent_if_successful(build_output, llm_client)
                if build_success and agent_says_success:
                    dockerfile_success = True
                    break
                if iteration < args.max_dockerfile_retries:
                    dockerfile_feedback = get_feedback_for_agent(build_output, iteration)
            
            if not dockerfile_success:
                print("Dockerfile regeneration failed in full loop.")
                break
        
        # Test generation loop
        for test_iteration in range(1, args.max_test_retries + 1):
            print(f"\n{'='*80}")
            print(f"Test Retry {test_iteration}/{args.max_test_retries}")
            print(f"{'='*80}")
            
            # Step 1: Generate test
            if not run_test_generation(repo_path, dockerfile_path, issue_json_path):
                print("Failed to generate test")
                if test_iteration < args.max_test_retries:
                    continue
                else:
                    break
            
            # Step 2: Run test verification
            is_valid, buggy_failed, test_output = run_test_verification(
                repo_path, dockerfile_path, issue_json_path
            )
            
            # Show test output
            if test_output:
                print("\nTest output:")
                print("-" * 80)
                output_lines = test_output.split('\n')
                if len(output_lines) > 100:
                    print("\n".join(output_lines[-100:]))
                    print(f"\n... (showing last 100 lines of {len(output_lines)} total lines)")
                else:
                    print(test_output)
                print("-" * 80)
            
            # Check if test is valid (buggy failed AND fixed passed)
                print(f"\n{'='*80}")
            print("Test Verification Result:")
                print(f"{'='*80}")
            print(f"  Buggy version: {'FAIL ✓' if buggy_failed else 'PASS ✗ (should fail!)'}")
            
            fixed_passed = "Fixed version test: ✓ Passed as expected" in test_output
            print(f"  Fixed version: {'PASS ✓' if fixed_passed else 'FAIL ✗ (should pass!)'}")
            print(f"  Overall: {'VALID ✓' if is_valid else 'INVALID ✗'}")
            
            if is_valid:
                print(f"\n✓ SUCCESS: Test verification passed!")
                print(f"  → Buggy version FAILed (correct)")
                print(f"  → Fixed version PASSed (correct)")
                test_success = True
                break
            else:
                print(f"\n✗ Test verification failed (iteration {test_iteration}/{args.max_test_retries})")
                if not buggy_failed:
                    print("  Problem: Buggy version should FAIL but it PASSed")
                if not fixed_passed:
                    print("  Problem: Fixed version should PASS but it FAILed")
                
                if test_iteration >= args.max_test_retries:
                    print(f"\n⚠ Reached max test retries ({args.max_test_retries})")
        
        # If test succeeded, exit
        if test_success:
            break
        
        # If co-fix mode is enabled, try to fix both files together
        if args.enable_cofix and not full_loop_active:
            print(f"\n{'='*80}")
            print("PHASE 3: Co-fix Mode")
            print(f"{'='*80}")
            
            cofix_success = False
            
            # Co-fix loop
            for cofix_iteration in range(1, args.max_cofix_retries + 1):
                print(f"\n{'='*80}")
                print(f"Co-fix Retry {cofix_iteration}/{args.max_cofix_retries}")
                print(f"{'='*80}")
                print("Agent analyzing Dockerfile + Test + Execution errors...")
                
                # Try to fix both files
                if not cofix_both_files(repo_path, dockerfile_path, test_output, issue_json_path):
                    print(f"\n✗ Co-fix generation failed (iteration {cofix_iteration})")
                    if cofix_iteration < args.max_cofix_retries:
                        print("Retrying co-fix...")
                continue
            else:
                        print("\nMax co-fix retries reached")
                break
                
                print("\n✓ Agent generated fixes for both files")
                print("Re-running test verification...")
                
                # Re-run test verification
                is_valid, buggy_failed, new_test_output = run_test_verification(
                    repo_path, dockerfile_path, issue_json_path
                )
                
                # Update test_output for next iteration if needed
                test_output = new_test_output
                
                # Show test output
                if test_output:
                    print("\nTest output:")
                    print("-" * 80)
                    output_lines = test_output.split('\n')
                    if len(output_lines) > 50:
                        print("\n".join(output_lines[-50:]))
                        print(f"\n... (showing last 50 lines of {len(output_lines)} total lines)")
        else:
                        print(test_output)
                    print("-" * 80)
                
                # Check if tests now pass
                print(f"\n{'='*80}")
                print(f"Co-fix Result (Iteration {cofix_iteration}/{args.max_cofix_retries}):")
                print(f"{'='*80}")
                
                fixed_passed = "Fixed version test: ✓ Passed as expected" in new_test_output
                print(f"  Buggy version: {'FAIL ✓' if buggy_failed else 'PASS ✗ (should fail!)'}")
                print(f"  Fixed version: {'PASS ✓' if fixed_passed else 'FAIL ✗ (should pass!)'}")
                print(f"  Overall: {'VALID ✓' if is_valid else 'INVALID ✗'}")
                
                if is_valid and buggy_failed:
                    print(f"\n✓ SUCCESS: Tests now pass after co-fix!")
                    print(f"  → Buggy version FAILed (correct)")
                    print(f"  → Fixed version PASSed (correct)")
                    test_success = True
                    cofix_success = True
                    break
                else:
                    print(f"\n✗ Co-fix failed to fix the tests")
                    if not buggy_failed:
                        print("  Problem: Buggy version should FAIL but it PASSed")
                    if not fixed_passed:
                        print("  Problem: Fixed version should PASS but it FAILed")
                    
                    if cofix_iteration < args.max_cofix_retries:
                        print(f"\nRetrying co-fix ({cofix_iteration + 1}/{args.max_cofix_retries})...")
                        continue
                    else:
                        print(f"\n⚠ Max co-fix retries reached ({args.max_cofix_retries})")
                        break
            
            # Exit test loop if co-fix succeeded or max retries reached
            break
        else:
            break
    
    # Final summary
    print(f"\n{'='*80}")
    if dockerfile_success and (not args.issue_json or test_success):
        print("✓ Pipeline completed successfully!")
        print(f"{'='*80}")
        print(f"Dockerfile: {dockerfile_path}")
        if args.issue_json:
            print(f"Test verification: Passed")
        sys.exit(0)
    else:
        print("⚠ Pipeline completed with issues")
        print(f"{'='*80}")
        if not dockerfile_success:
            print("Dockerfile: Failed")
        if args.issue_json and not test_success:
            print("Test verification: Failed")
        sys.exit(1)


if __name__ == "__main__":
    main()

