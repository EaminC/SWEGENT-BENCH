#!/usr/bin/env python3
"""
Convenience script: Can be run from repo directory
Usage: python gen_test.py <dockerfile_path> <issue_json_path>
"""

import sys
import subprocess
from pathlib import Path


def main():
    """Main function"""
    # Get test-gen directory path
    test_gen_dir = Path(__file__).parent.resolve()
    main_script = test_gen_dir / "main.py"
    
    # Get current working directory (should be repo directory)
    repo_path = Path.cwd()
    
    if len(sys.argv) < 3:
        print("Usage: python gen_test.py <dockerfile_path> <issue_json_path>")
        print("\nDescription:")
        print("  This script should be run from the repo root directory")
        print("  dockerfile_path: Path to dockerfile relative to repo root")
        print("  issue_json_path: Path to issue JSON file (can be absolute or relative)")
        print("\nExamples:")
        print("  # Run from repo directory:")
        print("  cd /home/cc/SWEGENT-BENCH/codex")
        print("  python /home/cc/SWEGENT-BENCH/src/test-gen/gen_test.py \\")
        print("    claude.dockerfile \\")
        print("    /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json")
        print("\n  # Or use relative paths:")
        print("  python /home/cc/SWEGENT-BENCH/src/test-gen/gen_test.py \\")
        print("    claude.dockerfile \\")
        print("    ../data/issue-filtered/issue_128.json")
        sys.exit(1)
    
    dockerfile_path = sys.argv[1]
    issue_json_path = sys.argv[2]
    
    print(f"Current working directory: {repo_path}")
    print(f"Dockerfile: {dockerfile_path}")
    print(f"Issue JSON: {issue_json_path}")
    
    # Build absolute path for dockerfile
    dockerfile_path_abs = Path(dockerfile_path)
    if not dockerfile_path_abs.is_absolute():
        dockerfile_path_abs = repo_path / dockerfile_path
    dockerfile_path_abs = dockerfile_path_abs.resolve()
    
    # Build absolute path for issue_json
    issue_json_path_abs = Path(issue_json_path)
    if not issue_json_path_abs.is_absolute():
        issue_json_path_abs = Path.cwd() / issue_json_path
    issue_json_path_abs = issue_json_path_abs.resolve()
    
    # Validate paths
    if not dockerfile_path_abs.exists():
        print(f"Error: Dockerfile does not exist: {dockerfile_path_abs}")
        sys.exit(1)
    
    if not issue_json_path_abs.exists():
        print(f"Error: Issue JSON file does not exist: {issue_json_path_abs}")
        sys.exit(1)
    
    print(f"\nUsing paths:")
    print(f"  Repository: {repo_path}")
    print(f"  Dockerfile: {dockerfile_path_abs}")
    print(f"  Issue JSON: {issue_json_path_abs}")
    print()
    
    # Call main script
    cmd = [
        sys.executable,
        str(main_script),
        str(repo_path),
        str(dockerfile_path_abs),
        str(issue_json_path_abs)
    ]
    
    sys.exit(subprocess.run(cmd).returncode)


if __name__ == "__main__":
    main()

