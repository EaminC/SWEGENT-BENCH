#!/usr/bin/env python3
"""
Expand issue JSON to fetch PR patch information
"""

import json
import os
import sys
import requests
from pathlib import Path
from typing import Dict, Optional


def get_pr_patch(repo: str, pr_number: int, github_token: Optional[str] = None) -> Optional[str]:
    """
    Get PR patch/diff
    
    Args:
        repo: GitHub repository in format "owner/repo"
        pr_number: PR number
        github_token: GitHub API token (optional)
        
    Returns:
        PR patch string, or None if failed
    """
    base_url = "https://api.github.com"
    headers = {
        "Accept": "application/vnd.github.v3.diff"
    }
    
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"{base_url}/repos/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # Get PR diff
        diff_url = f"{base_url}/repos/{repo}/pulls/{pr_number}.diff"
        diff_response = requests.get(diff_url, headers=headers)
        diff_response.raise_for_status()
        
        return diff_response.text
    except Exception as e:
        print(f"Warning: Failed to get patch for PR #{pr_number}: {e}")
        return None


def get_pr_details(repo: str, pr_number: int, github_token: Optional[str] = None) -> Optional[Dict]:
    """
    Get PR detailed information
    
    Args:
        repo: GitHub repository in format "owner/repo"
        pr_number: PR number
        github_token: GitHub API token (optional)
        
    Returns:
        PR details dictionary, or None if failed
    """
    base_url = "https://api.github.com"
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    
    if github_token:
        headers["Authorization"] = f"token {github_token}"
    
    try:
        url = f"{base_url}/repos/{repo}/pulls/{pr_number}"
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Warning: Failed to get details for PR #{pr_number}: {e}")
        return None


def expand_issue_json(issue_json_path: str, output_path: Optional[str] = None) -> Dict:
    """
    Expand issue JSON to add PR patch information
    
    Args:
        issue_json_path: Path to issue JSON file
        output_path: Output file path (optional, prints to stdout if not provided)
        
    Returns:
        Expanded JSON dictionary
    """
    # Read issue JSON
    with open(issue_json_path, 'r', encoding='utf-8') as f:
        issue_data = json.load(f)
    
    # Get GitHub token
    github_token = os.getenv("GITHUB_TOKEN")
    
    # Extract repo info from issue URL
    issue_url = issue_data.get('url', '')
    if not issue_url:
        print("Error: No URL information in issue JSON")
        sys.exit(1)
    
    # Parse repo: https://github.com/owner/repo/issues/123 -> owner/repo
    parts = issue_url.replace('https://github.com/', '').split('/')
    if len(parts) < 2:
        print(f"Error: Cannot parse repo from URL: {issue_url}")
        sys.exit(1)
    repo = f"{parts[0]}/{parts[1]}"
    
    print(f"Repository: {repo}")
    print(f"Issue: #{issue_data.get('number')}")
    
    # Expand each linked PR
    linked_prs = issue_data.get('linked_prs', [])
    expanded_prs = []
    
    for pr in linked_prs:
        pr_number = pr.get('number')
        if not pr_number:
            continue
        
        print(f"  Fetching PR #{pr_number} information...")
        
        # Get PR details
        pr_details = get_pr_details(repo, pr_number, github_token)
        if pr_details:
            pr['body'] = pr_details.get('body', '')
            pr['created_at'] = pr_details.get('created_at', '')
            pr['merged_at'] = pr_details.get('merged_at', '')
            pr['head_sha'] = pr_details.get('head', {}).get('sha', '')
            pr['base_sha'] = pr_details.get('base', {}).get('sha', '')
        
        # Get PR patch
        patch = get_pr_patch(repo, pr_number, github_token)
        if patch:
            pr['patch'] = patch
            print(f"    Got patch ({len(patch)} characters)")
        else:
            pr['patch'] = None
            print(f"    Failed to get patch")
        
        expanded_prs.append(pr)
    
    # Update issue data
    issue_data['linked_prs'] = expanded_prs
    issue_data['repo'] = repo
    
    # Save or print
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(issue_data, f, indent=2, ensure_ascii=False)
        print(f"\nExpanded JSON saved to: {output_path}")
    else:
        print("\nExpanded JSON:")
        print(json.dumps(issue_data, indent=2, ensure_ascii=False))
    
    return issue_data


def main():
    """Main function"""
    if len(sys.argv) < 2:
        print("Usage: python expand_issue_json.py <issue_json_file> [output_file]")
        print("Example: python expand_issue_json.py ../data/issue-filtered/issue_128.json")
        sys.exit(1)
    
    issue_json_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) >= 3 else None
    
    if not os.path.exists(issue_json_path):
        print(f"Error: File does not exist: {issue_json_path}")
        sys.exit(1)
    
    try:
        expand_issue_json(issue_json_path, output_path)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

