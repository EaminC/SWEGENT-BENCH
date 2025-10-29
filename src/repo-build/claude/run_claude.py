#!/usr/bin/env python3
"""
Script that loads environment variables from .env file, prepares context files,
and runs the claude command with a comprehensive prompt.
"""

import os
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


def build_prompt(repo_build_dir):
    """Build the comprehensive prompt with all context files."""
    prompt_parts = []
    
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

YOUR TASK:
When creating/configuring the Dockerfile, set the appropriate environment variables to make the 
repository use Forge API instead of OpenAI API. The application code should remain unchanged.

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

APPROACH:
1. Set environment variables in the Dockerfile using ENV directives
2. These environment variables will override the default API endpoints
3. The existing code will automatically use Forge API through these environment variables
4. No code changes needed - only Dockerfile configuration
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
    
    prompt_parts.append("=" * 80)
    prompt_parts.append("SPECIFIC TASK")
    prompt_parts.append("=" * 80)
    prompt_parts.append(base_prompt)
    prompt_parts.append("")
    prompt_parts.append("REMINDER: Only configure environment variables in Dockerfile. Do NOT modify any source code.")
    
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
    full_prompt = build_prompt(repo_build_dir)
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

