#!/usr/bin/env python3
"""
GitHub Archive Agent Repository Collection Tool

Collect agent-related repositories that have been modified in the last day from GitHub Archive
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict
import argparse
import os
from dotenv import load_dotenv

from github_fetcher import GitHubArchiveFetcher
from agent_filter import AgentRepoFilter

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../../.env'))


def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Collect agent-related repositories from GitHub Archive')
    parser.add_argument('--no-ai', action='store_true', help='Do not use AI for secondary filtering (keyword filtering only)')
    parser.add_argument('--date', type=str, help='Specify date (format: YYYY-MM-DD), defaults to yesterday')
    parser.add_argument('--limit', type=int, default=None, help='Limit the number of output repositories')
    parser.add_argument('--github-token', type=str, default=None, help='GitHub token for API access (to avoid rate limits)')
    parser.add_argument('--min-stars', type=int, default=10, help='Minimum stars required (default: 10)')
    args = parser.parse_args()
    
    # Use environment variable if token not provided via command line
    if not args.github_token:
        args.github_token = os.getenv('GITHUB_TOKEN')
    
    # Determine date
    if args.date:
        try:
            target_date = datetime.strptime(args.date, '%Y-%m-%d')
        except ValueError:
            print(f"Error: Invalid date format, should be YYYY-MM-DD")
            return
    else:
        target_date = datetime.now() - timedelta(days=1)
    
    date_str = target_date.strftime('%Y-%m-%d')
    
    print("=" * 60)
    print(f"GitHub Archive Agent Repository Collection Tool")
    print(f"Target date: {date_str}")
    print(f"AI filtering: {'No' if args.no_ai else 'Yes'}")
    print("=" * 60)
    
    # Step 1: Fetch GitHub Archive data
    print("\n[Phase 1] Fetching GitHub Archive data...")
    fetcher = GitHubArchiveFetcher()
    events = fetcher.fetch_day_data(
        target_date.year,
        target_date.month,
        target_date.day
    )
    
    if not events:
        print("Error: No data retrieved")
        return
    
    # Step 2: Extract repository information
    print("\n[Phase 2] Extracting repository information...")
    repos = fetcher.extract_repos(events)
    print(f"Found {len(repos)} active repositories")
    
    # Get detailed repository information
    print("Collecting detailed repository information...")
    repos_info = []
    from tqdm import tqdm
    for repo_name in tqdm(repos, desc="Collection progress"):
        repo_info = fetcher.get_repo_info(events, repo_name)
        repos_info.append(repo_info)
    
    # Step 3: Filter Agent Repositories
    print("\n[Phase 3] Filtering Agent Repositories...")
    filter_obj = AgentRepoFilter(use_ai=not args.no_ai, github_token=args.github_token)
    agent_repos = filter_obj.filter_repos(repos_info, min_stars=args.min_stars)
    
    # Limit quantity
    if args.limit and len(agent_repos) > args.limit:
        agent_repos = agent_repos[:args.limit]
        print(f"Limited output to first {args.limit} repositories")
    
    # Step 4: Save results
    print("\n[Phase 4] Saving results...")
    output_dir = "/home/cc/SWGENT-Bench/data/hooked_repo"
    os.makedirs(output_dir, exist_ok=True)
    
    output_file = os.path.join(
        output_dir,
        f"github_archive_repo_{date_str}.json"
    )
    
    result = {
        "date": date_str,
        "total_events": len(events),
        "total_repos": len(repos),
        "agent_repos_count": len(agent_repos),
        "used_ai_filter": not args.no_ai,
        "min_stars": args.min_stars,
        "agent_repos": agent_repos
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    
    print(f"\nResults saved to: {output_file}")
    print("\n" + "=" * 60)
    print("Summary:")
    print(f"  - Total events: {len(events)}")
    print(f"  - Active repositories: {len(repos)}")
    print(f"  - Agent repositories: {len(agent_repos)}")
    print("=" * 60)
    
    # Display partial results
    if agent_repos:
        print("\nSample of Agent repositories:")
        for repo in agent_repos[:10]:
            if isinstance(repo, dict):
                print(f"  - {repo['name']} ({repo.get('stars', 0)} stars)")
            else:
                print(f"  - {repo}")
        if len(agent_repos) > 10:
            print(f"  ... and {len(agent_repos) - 10} more repositories")


if __name__ == "__main__":
    main()

