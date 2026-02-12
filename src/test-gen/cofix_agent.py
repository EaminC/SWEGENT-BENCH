#!/usr/bin/env python3
"""
Co-fix agent: Fixes both Dockerfile and test file based on test execution results
"""

import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from forge.api import LLMClient


def main():
    if len(sys.argv) < 2:
        print("Usage: cofix_agent.py <prompt_file>", file=sys.stderr)
        sys.exit(1)
    
    prompt_file = Path(sys.argv[1])
    
    if not prompt_file.exists():
        print(f"Error: Prompt file not found: {prompt_file}", file=sys.stderr)
        sys.exit(1)
    
    prompt = prompt_file.read_text()
    
    # Initialize LLM client
    llm_client = LLMClient()
    
    system_prompt = """You are a debugging expert specialized in fixing Docker and test configurations.
Your task is to analyze test failures and provide minimal fixes for both Dockerfile and test files.

CRITICAL RULES:
1. Make ONLY the MINIMAL necessary changes
2. Output MUST be in the exact format specified
3. Include complete file contents in your output
4. Focus on making tests pass while preserving existing functionality"""
    
    try:
        response = llm_client.simple_chat(
            prompt,
            system_prompt=system_prompt,
            temperature=0.2
           #max_tokens=4000
        )
        
        # Output the response (will be parsed by main.py)
        print(response)
        
    except Exception as e:
        print(f"Error calling LLM: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()


