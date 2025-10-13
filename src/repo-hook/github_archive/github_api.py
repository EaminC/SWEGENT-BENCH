"""
GitHub API module for fetching repository details
"""

import urllib.request
import urllib.error
import json
import base64
from typing import Optional, Dict, List
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


class GitHubAPI:
    """GitHub API client for fetching repository information"""
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub API client
        
        Args:
            token: GitHub personal access token (optional, but recommended to avoid rate limits)
        """
        self.token = token
        self.request_count = 0
        self.rate_limit_remaining = 60  # Default for unauthenticated requests
        self.cache = {}  # Simple cache to avoid duplicate requests
    
    def _make_request(self, url: str) -> Optional[Dict]:
        """
        Make a request to GitHub API
        
        Args:
            url: API endpoint URL
            
        Returns:
            Response JSON or None if failed
        """
        try:
            req = urllib.request.Request(url)
            req.add_header('Accept', 'application/vnd.github.v3+json')
            
            if self.token:
                req.add_header('Authorization', f'token {self.token}')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                # Update rate limit info
                self.rate_limit_remaining = int(response.headers.get('X-RateLimit-Remaining', 60))
                data = json.loads(response.read().decode('utf-8'))
                self.request_count += 1
                return data
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            elif e.code == 403:
                print(f"Rate limit exceeded, waiting...")
                time.sleep(60)
                return self._make_request(url)  # Retry after waiting
            else:
                print(f"HTTP error {e.code} for {url}")
                return None
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def get_repo_readme(self, repo_name: str) -> Optional[str]:
        """
        Get repository README content
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            README content as string, or None if not found
        """
        url = f"{self.BASE_URL}/repos/{repo_name}/readme"
        data = self._make_request(url)
        
        if not data or 'content' not in data:
            return None
        
        try:
            # Decode base64 content
            content = base64.b64decode(data['content']).decode('utf-8')
            # Limit to first 3000 characters to avoid too long prompts
            return content[:3000]
        except Exception as e:
            print(f"Error decoding README for {repo_name}: {e}")
            return None
    
    def get_repo_info(self, repo_name: str) -> Optional[Dict]:
        """
        Get repository basic information
        
        Args:
            repo_name: Repository name in format "owner/repo"
            
        Returns:
            Repository info dict or None
        """
        # Check cache first
        if repo_name in self.cache:
            return self.cache[repo_name]
        
        url = f"{self.BASE_URL}/repos/{repo_name}"
        data = self._make_request(url)
        
        if not data:
            return None
        
        result = {
            'name': data.get('full_name', repo_name),
            'description': data.get('description', ''),
            'language': data.get('language', ''),
            'stars': data.get('stargazers_count', 0),
            'topics': data.get('topics', [])
        }
        
        # Cache the result
        self.cache[repo_name] = result
        
        return result
    
    def get_repos_info_batch(self, repo_names: List[str], max_workers: int = 10) -> Dict[str, Optional[Dict]]:
        """
        Get repository information for multiple repos in parallel
        
        Args:
            repo_names: List of repository names
            max_workers: Maximum number of concurrent threads
            
        Returns:
            Dict mapping repo names to their info
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_repo = {
                executor.submit(self.get_repo_info, repo_name): repo_name 
                for repo_name in repo_names
            }
            
            for future in as_completed(future_to_repo):
                repo_name = future_to_repo[future]
                try:
                    results[repo_name] = future.result()
                except Exception as e:
                    print(f"Error fetching {repo_name}: {e}")
                    results[repo_name] = None
        
        return results

