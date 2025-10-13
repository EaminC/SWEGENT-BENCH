#!/usr/bin/env python3
"""
GitHub Issue Crawler for Agent Issues
Crawls GitHub repository issues and filters agent-related issues
"""

import os
import sys
import json
import requests
import time
import subprocess
import shutil
import re
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Set
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

# Add forge directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from forge.api import LLMClient


class GitHubIssueCrawler:
    """GitHub Issue Crawler Class"""
    
    def __init__(self, repo: str, github_token: Optional[str] = None, use_local_clone: bool = False, max_workers: int = 5):
        """
        Initialize crawler
        
        Args:
            repo: GitHub repository in format "owner/repo"
            github_token: GitHub API token (optional but recommended to avoid rate limits)
            use_local_clone: Whether to use local clone mode (more accurate but requires disk space)
            max_workers: Maximum number of concurrent workers for issue filtering (default: 5)
        """
        self.repo = repo
        self.github_token = github_token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json"
        }
        if self.github_token:
            self.headers["Authorization"] = f"token {self.github_token}"
        
        # Initialize LLM client
        self.llm_client = LLMClient()
        
        # Load agent issue criteria
        self.agent_issue_criteria = self._load_agent_criteria()
        
        # Local clone mode
        self.use_local_clone = use_local_clone
        self.local_repo_path = None
        if use_local_clone:
            # Use relative path from script location
            script_dir = Path(__file__).resolve().parent
            project_root = script_dir.parent.parent
            self.cached_repo_dir = project_root / "data" / "cached_repo"
            self.cached_repo_dir.mkdir(parents=True, exist_ok=True)
        
        # Concurrent processing
        self.max_workers = max_workers
        self.print_lock = Lock()
    
    def _load_agent_criteria(self) -> str:
        """Load agent issue criteria"""
        criteria_path = os.path.join(os.path.dirname(__file__), "agent_issue.md")
        try:
            with open(criteria_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Warning: Failed to load agent issue criteria: {e}")
            return ""
    
    def _clone_repo(self) -> bool:
        """
        Clone repository to local disk
        
        Returns:
            Whether clone was successful
        """
        repo_name = self.repo.replace('/', '-')
        self.local_repo_path = self.cached_repo_dir / repo_name
        
        # Delete if already exists
        if self.local_repo_path.exists():
            print(f"Removing existing cached repository: {self.local_repo_path}")
            shutil.rmtree(self.local_repo_path)
        
        # Clone repository
        clone_url = f"https://github.com/{self.repo}.git"
        print(f"Cloning repository: {clone_url}")
        print(f"Target location: {self.local_repo_path}")
        
        try:
            cmd = ["git", "clone", clone_url, str(self.local_repo_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                print(f"✓ Repository cloned successfully")
                return True
            else:
                print(f"✗ Clone failed: {result.stderr}")
                return False
        except Exception as e:
            print(f"✗ Clone error: {e}")
            return False
    
    def _cleanup_repo(self):
        """
        Clean up local cloned repository (temporary cache only)
        Note: This only deletes the cloned repo in data/cached_repo/
        Results in data/hooked_issue/ are preserved
        """
        if self.local_repo_path and self.local_repo_path.exists():
            print(f"\nCleaning up cached repository: {self.local_repo_path}")
            print("(Results in data/hooked_issue/ are preserved)")
            try:
                shutil.rmtree(self.local_repo_path)
                print("✓ Cleanup complete")
            except Exception as e:
                print(f"✗ Cleanup failed: {e}")
    
    def _get_issue_linked_prs_from_git(self, issue_number: int) -> Set[int]:
        """
        Find linked PR numbers from local git repository
        
        Args:
            issue_number: Issue number
            
        Returns:
            Set of PR numbers
        """
        if not self.local_repo_path:
            return set()
        
        pr_numbers = set()
        
        try:
            # Search commits that mention this issue
            cmd = ["git", "log", "--all", "--oneline", "--grep", f"#{issue_number}"]
            result = subprocess.run(
                cmd, 
                cwd=self.local_repo_path,
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout:
                commit_lines = result.stdout.strip().split('\n')
                
                for line in commit_lines:
                    # Extract commit SHA
                    parts = line.split(maxsplit=1)
                    if len(parts) < 2:
                        continue
                    commit_sha = parts[0]
                    
                    # Get full commit message
                    cmd = ["git", "show", "--format=%B", "-s", commit_sha]
                    result = subprocess.run(
                        cmd,
                        cwd=self.local_repo_path,
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if result.returncode == 0:
                        commit_msg = result.stdout
                        
                        # Find PR number in commit message
                        # GitHub merge commits: "Merge pull request #123"
                        pr_match = re.search(r'Merge pull request #(\d+)', commit_msg)
                        if pr_match:
                            pr_numbers.add(int(pr_match.group(1)))
                        
                        # Squash merge format: "(#123)"
                        pr_match = re.search(r'\(#(\d+)\)', commit_msg)
                        if pr_match:
                            pr_numbers.add(int(pr_match.group(1)))
            
        except Exception as e:
            print(f"    Git analysis error: {e}")
        
        return pr_numbers
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """
        Send GitHub API request
        
        Args:
            url: Request URL
            params: Request parameters
            
        Returns:
            Response JSON data or None
        """
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return None
    
    def _get_all_closed_issues(self) -> List[Dict]:
        """
        Get all closed issues
        
        Returns:
            List of issues
        """
        issues = []
        page = 1
        per_page = 100
        
        print(f"Fetching closed issues from repository {self.repo}...")
        
        while True:
            url = f"{self.base_url}/repos/{self.repo}/issues"
            params = {
                "state": "closed",
                "per_page": per_page,
                "page": page
            }
            
            data = self._make_request(url, params)
            if not data:
                break
            
            if len(data) == 0:
                break
            
            # Filter out pull requests (GitHub API includes PRs in issues)
            page_issues = [item for item in data if 'pull_request' not in item]
            issues.extend(page_issues)
            
            print(f"Fetched page {page}, total {len(issues)} issues so far")
            page += 1
            
            # If fewer results than per_page, this is the last page
            if len(data) < per_page:
                break
        
        print(f"Total {len(issues)} closed issues fetched")
        return issues
    
    def _get_issue_linked_prs(self, issue_number: int, issue_body: str = "") -> List[Dict]:
        """
        Get linked PRs for an issue (using multiple detection methods)
        
        Args:
            issue_number: Issue number
            issue_body: Issue content
            
        Returns:
            List of linked PRs
        """
        linked_prs = []
        pr_numbers = set()
        
        # If local clone mode is enabled, use git analysis first
        if self.use_local_clone and self.local_repo_path:
            git_prs = self._get_issue_linked_prs_from_git(issue_number)
            pr_numbers.update(git_prs)
            if git_prs:
                print(f"    Found {len(git_prs)} PR(s) from Git history: {sorted(git_prs)}")
        
        # If not local mode or no results found, use API methods
        if not self.use_local_clone or not pr_numbers:
            # Method 1: Timeline API
            url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/timeline"
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.mockingbird-preview+json"
            
            try:
                response = requests.get(url, headers=headers)
                response.raise_for_status()
                events = response.json()
                
                for event in events:
                    if event.get('event') in ['cross-referenced', 'connected']:
                        source = event.get('source')
                        if source and source.get('issue') and source['issue'].get('pull_request'):
                            pr = source['issue']
                            pr_numbers.add(pr['number'])
            except Exception:
                pass
            
            # Method 2: Find PRs that closed this issue
            try:
                url = f"{self.base_url}/repos/{self.repo}/issues/{issue_number}/events"
                response = requests.get(url, headers=self.headers)
                response.raise_for_status()
                events = response.json()
                
                for event in events:
                    if event.get('event') == 'closed':
                        commit_id = event.get('commit_id')
                        if commit_id:
                            # Find PRs containing this commit
                            prs = self._find_prs_with_commit(commit_id)
                            for pr_num in prs:
                                pr_numbers.add(pr_num)
            except Exception:
                pass
            
            # Method 3: Search PRs mentioning this issue (only in non-local mode to avoid rate limits)
            if not self.use_local_clone:
                try:
                    url = f"{self.base_url}/search/issues"
                    params = {
                        'q': f'repo:{self.repo} type:pr #{issue_number}',
                        'per_page': 10
                    }
                    # Search API has stricter rate limits, add delay
                    time.sleep(2)
                    response = requests.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    data = response.json()
                    
                    for item in data.get('items', []):
                        if item.get('pull_request'):
                            pr_numbers.add(item['number'])
                except Exception as e:
                    # Ignore search API errors (likely rate limit)
                    pass
        
        # Get detailed info for all found PRs
        for pr_num in pr_numbers:
            pr_info = self._get_pr_info(pr_num)
            if pr_info:
                linked_prs.append(pr_info)
        
        return linked_prs
    
    def _find_prs_with_commit(self, commit_sha: str) -> List[int]:
        """
        Find PRs containing a specific commit
        
        Args:
            commit_sha: Commit SHA
            
        Returns:
            List of PR numbers
        """
        try:
            url = f"{self.base_url}/repos/{self.repo}/commits/{commit_sha}/pulls"
            headers = self.headers.copy()
            headers["Accept"] = "application/vnd.github.groot-preview+json"
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            prs = response.json()
            return [pr['number'] for pr in prs]
        except Exception:
            return []
    
    def _get_pr_info(self, pr_number: int) -> Optional[Dict]:
        """
        Get detailed PR information
        
        Args:
            pr_number: PR number
            
        Returns:
            PR information dictionary
        """
        try:
            url = f"{self.base_url}/repos/{self.repo}/pulls/{pr_number}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            pr = response.json()
            return {
                'number': pr['number'],
                'state': pr['state'],
                'title': pr['title'],
                'url': pr['html_url'],
                'merged': pr.get('merged', False),
                'base_branch': pr.get('base', {}).get('ref', '')
            }
        except Exception:
            return None
    
    def _check_pr_merged_to_main(self, pr_info: Dict) -> bool:
        """
        Check if PR is merged to main branch
        
        Args:
            pr_info: PR information dictionary
            
        Returns:
            Whether PR is merged to main
        """
        # Check if PR is merged
        if not pr_info.get('merged'):
            return False
        
        # Check if merged to main or master branch
        base_branch = pr_info.get('base_branch', '')
        return base_branch in ['main', 'master']
    
    def _has_text_description(self, issue: Dict) -> bool:
        """
        Check if issue has text description
        
        Args:
            issue: Issue data
            
        Returns:
            Whether issue has text description
        """
        body = issue.get('body', '')
        return body is not None and len(body.strip()) > 0
    
    def _is_agent_issue(self, issue: Dict) -> Tuple[bool, str]:
        """
        Use AI to determine if issue is an agent issue
        
        Args:
            issue: Issue data
            
        Returns:
            (is_agent_issue, AI response)
        """
        # Build prompt
        system_prompt = f"""You are a GitHub issue classification expert. Your task is to determine if a given issue is an "agent issue".

Agent Issue Definition and Criteria:
{self.agent_issue_criteria}

Based on the above criteria, determine if the given issue is an agent issue.
Answer with "Yes" or "No", followed by a brief explanation (max 50 words)."""

        user_message = f"""Issue Title: {issue.get('title', '')}

Issue Description:
{issue.get('body', '')}

Is this an agent issue? Please answer "Yes" or "No" with a brief explanation."""

        try:
            response = self.llm_client.simple_chat(
                user_message=user_message,
                system_prompt=system_prompt,
                temperature=0.3
            )
            
            # Check if response contains "Yes"
            response_lower = response.lower()
            is_agent = "yes" in response_lower and "no" not in response_lower[:10]
            return is_agent, response
        except Exception as e:
            print(f"AI judgment error: {e}")
            return False, f"Judgment failed: {str(e)}"
    
    def _process_single_issue(self, issue: Dict, idx: int, total: int) -> Optional[Dict]:
        """
        Process a single issue to check if it meets criteria (without AI judgment)
        
        Args:
            issue: Issue data
            idx: Current index (for progress display)
            total: Total number of issues
            
        Returns:
            Filtered issue dict if meets criteria, None otherwise
        """
        issue_number = issue['number']
        
        with self.print_lock:
            print(f"\nProgress: {idx}/{total} - Issue #{issue_number}")
        
        # Condition 1: Already filtered (state=closed)
        
        # Condition 2: Check if has text description
        if not self._has_text_description(issue):
            with self.print_lock:
                print(f"  ✗ No text description")
            return None
        
        with self.print_lock:
            print(f"  ✓ Has text description")
        
        # Condition 3: Get linked PRs
        linked_prs = self._get_issue_linked_prs(issue_number, issue.get('body', ''))
        if not linked_prs:
            with self.print_lock:
                print(f"  ✗ No linked PRs")
            return None
        
        with self.print_lock:
            print(f"  ✓ Found {len(linked_prs)} linked PR(s)")
        
        # Condition 4: Check if any PR is merged to main
        merged_prs = []
        for pr in linked_prs:
            if self._check_pr_merged_to_main(pr):
                merged_prs.append(pr)
        
        if not merged_prs:
            with self.print_lock:
                print(f"  ✗ No PRs merged to main branch")
            return None
        
        with self.print_lock:
            print(f"  ✓ {len(merged_prs)} PR(s) merged to main")
        
        # Create filtered issue (without AI judgment yet)
        filtered_issue = {
            'number': issue_number,
            'title': issue['title'],
            'url': issue['html_url'],
            'state': issue['state'],
            'created_at': issue['created_at'],
            'closed_at': issue['closed_at'],
            'body': issue['body'],
            'labels': [label['name'] for label in issue.get('labels', [])],
            'linked_prs': merged_prs,
        }
        
        with self.print_lock:
            print(f"  ✓✓ Issue #{issue_number} meets all criteria!")
        
        return filtered_issue
    
    def filter_issues(self, issues: List[Dict]) -> List[Dict]:
        """
        Filter issues that meet criteria (without AI judgment)
        Uses concurrent processing in local clone mode for better performance
        
        Args:
            issues: Original issues list
            
        Returns:
            Filtered issues list (without AI judgment)
        """
        filtered_issues = []
        total = len(issues)
        
        # Use concurrent processing only in local clone mode
        # Online API mode uses sequential processing to avoid rate limits
        if self.use_local_clone:
            print(f"\nFiltering issues with {self.max_workers} concurrent workers (local clone mode)...")
            
            # Use ThreadPoolExecutor for concurrent processing
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all tasks
                future_to_issue = {
                    executor.submit(self._process_single_issue, issue, idx, total): issue
                    for idx, issue in enumerate(issues, 1)
                }
                
                # Process completed tasks
                for future in as_completed(future_to_issue):
                    try:
                        result = future.result()
                        if result is not None:
                            filtered_issues.append(result)
                    except Exception as e:
                        issue = future_to_issue[future]
                        with self.print_lock:
                            print(f"  ✗ Error processing issue #{issue['number']}: {e}")
            
            # Sort by issue number for consistent output
            filtered_issues.sort(key=lambda x: x['number'])
        else:
            # Sequential processing for API mode (to avoid rate limits)
            print(f"\nFiltering issues sequentially (API mode - avoiding rate limits)...")
            
            for idx, issue in enumerate(issues, 1):
                result = self._process_single_issue(issue, idx, total)
                if result is not None:
                    filtered_issues.append(result)
        
        print(f"\nFiltering complete! Found {len(filtered_issues)} issues meeting criteria")
        return filtered_issues
    
    def batch_ai_judgment(self, issues: List[Dict]) -> List[Dict]:
        """
        Batch AI judgment for all filtered issues
        
        Args:
            issues: Filtered issues list
            
        Returns:
            Issues with AI judgment results
        """
        if not issues:
            return []
        
        print(f"\n{'='*60}")
        print(f"Starting batch AI judgment for {len(issues)} issues")
        print(f"{'='*60}\n")
        
        agent_issues = []
        
        for idx, issue in enumerate(issues, 1):
            issue_number = issue['number']
            print(f"AI Judgment Progress: {idx}/{len(issues)} - Issue #{issue_number}")
            
            is_agent, ai_response = self._is_agent_issue(issue)
            
            issue['ai_judgment'] = {
                'is_agent_issue': is_agent,
                'response': ai_response
            }
            
            if is_agent:
                agent_issues.append(issue)
                print(f"  ✓ AI: This is an agent issue")
                print(f"    Reason: {ai_response[:100]}...")
            else:
                print(f"  ✗ AI: Not an agent issue")
                print(f"    Reason: {ai_response[:100]}...")
        
        print(f"\n{'='*60}")
        print(f"AI judgment complete!")
        print(f"Total: {len(issues)} issues | Agent issues: {len(agent_issues)}")
        print(f"{'='*60}\n")
        
        return agent_issues
    
    def save_results(self, issues: List[Dict]) -> str:
        """
        Save results to JSON file
        
        Args:
            issues: Filtered issues
            
        Returns:
            Output file path
        """
        # Create output directory - use relative path from script location
        # This script is in: SWGENT-Bench/src/issue-hook/issue_crawler.py
        # Target directory: SWGENT-Bench/data/hooked_issue/
        script_dir = Path(__file__).resolve().parent  # src/issue-hook/
        project_root = script_dir.parent.parent       # SWGENT-Bench/
        base_dir = project_root / "data" / "hooked_issue"
        base_dir.mkdir(parents=True, exist_ok=True)
        
        # Create repository subdirectory (format: reponame-date)
        repo_name = self.repo.replace('/', '-')
        date_str = datetime.now().strftime('%Y%m%d')
        output_dir = base_dir / f"{repo_name}-{date_str}"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        output_file = output_dir / "issue.json"
        result = {
            'repo': self.repo,
            'crawl_time': datetime.now().isoformat(),
            'total_count': len(issues),
            'issues': issues
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        print(f"\nResults saved to: {output_file}")
        return str(output_file)
    
    def run(self) -> str:
        """
        Run complete crawling and filtering workflow
        
        Returns:
            Output file path
        """
        try:
            # 0. Clone repository if local clone mode is enabled
            if self.use_local_clone:
                if not self._clone_repo():
                    print("✗ Failed to clone repository, exiting")
                    return ""
            
            # 1. Get all closed issues
            issues = self._get_all_closed_issues()
            
            if not issues:
                print("No closed issues found")
                return ""
            
            # 2. Filter issues that meet criteria (without AI)
            filtered_issues = self.filter_issues(issues)
            
            if not filtered_issues:
                print("No issues meeting criteria found")
                # Save empty result
                output_file = self.save_results([])
                return output_file
            
            # 3. Batch AI judgment
            agent_issues = self.batch_ai_judgment(filtered_issues)
            
            # 4. Save results (these will be preserved)
            output_file = self.save_results(agent_issues)
            
            return output_file
            
        finally:
            # 5. Clean up temporary cloned repository (results in hooked_issue/ are kept)
            if self.use_local_clone:
                self._cleanup_repo()


def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='GitHub Issue Crawler for Agent Issues',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using API mode (default)
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT
  
  # Using local clone mode (more accurate, recommended)
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone
  
  # Specify GitHub token and concurrent workers
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --token YOUR_TOKEN --local-clone --workers 10
  
  # More concurrent workers for faster processing (be mindful of rate limits)
  python issue_crawler.py TsinghuaDatabaseGroup/DB-GPT --local-clone --workers 20
        """
    )
    parser.add_argument('repo', type=str, help='GitHub repository (format: owner/repo)')
    parser.add_argument('--token', type=str, help='GitHub API token (or set GITHUB_TOKEN env var)')
    parser.add_argument('--local-clone', action='store_true', 
                       help='Use local clone mode: clone repo locally for analysis (more accurate but requires time and disk space)')
    parser.add_argument('--workers', type=int, default=10,
                       help='Maximum number of concurrent workers for issue filtering (default: 10, recommended: 5-20)')
    
    args = parser.parse_args()
    
    # Create crawler instance and run
    crawler = GitHubIssueCrawler(
        args.repo, 
        args.token, 
        use_local_clone=args.local_clone,
        max_workers=args.workers
    )
    
    if args.local_clone:
        # Get project root for displaying paths
        script_dir = Path(__file__).resolve().parent
        project_root = script_dir.parent.parent
        cache_dir = project_root / "data" / "cached_repo"
        
        print("\n" + "="*60)
        print("Using local clone mode")
        print(f"Repository will be cloned to: {cache_dir}")
        print("Cloned repo will be deleted after analysis (results are preserved)")
        print(f"Concurrent workers: {args.workers} (parallel processing enabled)")
        print("="*60 + "\n")
    else:
        print("\n" + "="*60)
        print("Using API mode")
        print("Sequential processing (to avoid API rate limits)")
        print("Tip: Use --local-clone for faster concurrent processing")
        print("="*60 + "\n")
    
    crawler.run()


if __name__ == "__main__":
    main()
