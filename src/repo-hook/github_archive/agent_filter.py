"""
Agent Repository filtering module
"""

import sys
import os
from typing import List, Dict, Set, Optional

# Add forge directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../../forge'))

from api import LLMClient
from config import AGENT_KEYWORDS, AGENT_REPO_DEFINITION, JUDGE_PROMPT_TEMPLATE
from github_api import GitHubAPI


class AgentRepoFilter:
    """Agent Repository filter"""
    
    def __init__(self, use_ai: bool = True, github_token: Optional[str] = None):
        """
        Initialize filter
        
        Args:
            use_ai: Whether to use AI for secondary filtering
            github_token: GitHub token for API access (optional)
        """
        self.keywords = [kw.lower() for kw in AGENT_KEYWORDS]
        self.use_ai = use_ai
        if use_ai:
            self.llm = LLMClient(model="OpenAI/gpt-4o-mini")  # Use more economical model
            self.github_api = GitHubAPI(token=github_token)
    
    def keyword_filter(self, repo_name: str, repo_description: str = "") -> bool:
        """
        Keyword filtering
        
        Args:
            repo_name: Repository name
            repo_description: Repository description
            
        Returns:
            Whether it passes keyword filtering
        """
        text = (repo_name + " " + repo_description).lower()
        
        for keyword in self.keywords:
            if keyword in text:
                return True
        
        return False
    
    def ai_filter(self, repo_name: str, repo_description: str = "") -> bool:
        """
        Filter using AI based on README content
        
        Args:
            repo_name: Repository name
            repo_description: Repository description
            
        Returns:
            Whether AI judges it as an Agent Repository
        """
        if not self.use_ai:
            return True
        
        # Fetch README from GitHub
        readme_content = self.github_api.get_repo_readme(repo_name)
        
        if not readme_content:
            # If no README, use description only
            readme_content = "No README available"
        
        if not repo_description:
            repo_description = "No description available"
        
        # Build prompt
        prompt = JUDGE_PROMPT_TEMPLATE.format(
            agent_repo_definition=AGENT_REPO_DEFINITION,
            repo_name=repo_name,
            repo_description=repo_description,
            repo_readme=readme_content
        )
        
        try:
            response = self.llm.simple_chat(
                user_message=prompt,
                temperature=0.1  # Very low temperature for consistent YES/NO
            ).strip().upper()
            
            # Strict check: only accept if response starts with YES
            return response.startswith("YES")
        except Exception as e:
            print(f"AI filtering error for {repo_name}: {e}")
            # If AI call fails, reject to be safe
            return False
    
    def filter_repos(self, repos_info: List[Dict], batch_size: int = 10, min_stars: int = 10) -> List[str]:
        """
        Filter Agent Repositories
        
        Args:
            repos_info: Repository information list
            batch_size: Batch size for AI filtering
            min_stars: Minimum stars required (default: 10)
            
        Returns:
            Filtered repository name list
        """
        print(f"\nStarting filtering, total {len(repos_info)} repositories")
        
        # Step 1: Keyword filtering
        print("\n[Step 1] Keyword filtering...")
        keyword_passed = []
        for repo_info in repos_info:
            if self.keyword_filter(repo_info['name'], repo_info.get('description', '')):
                keyword_passed.append(repo_info)
        
        print(f"Keyword filtering passed: {len(keyword_passed)} repositories")
        
        if not self.use_ai:
            return [repo['name'] for repo in keyword_passed]
        
        # Step 2: Star filtering (fetch from GitHub API)
        print(f"\n[Step 2] Star filtering (>= {min_stars} stars)...")
        star_passed = []
        
        from tqdm import tqdm
        
        for repo_info in tqdm(keyword_passed, desc="Checking stars"):
            repo_name = repo_info['name']
            github_info = self.github_api.get_repo_info(repo_name)
            
            if github_info and github_info.get('stars', 0) >= min_stars:
                star_passed.append({
                    'name': repo_name,
                    'description': github_info.get('description', ''),
                    'stars': github_info.get('stars', 0)
                })
        
        print(f"Star filtering passed: {len(star_passed)} repositories")
        
        if len(star_passed) == 0:
            print("No repositories passed star filtering")
            return []
        
        # Step 3: AI filtering
        print("\n[Step 3] AI deep filtering...")
        ai_passed = []
        
        for i, repo_info in enumerate(tqdm(star_passed, desc="AI filtering progress")):
            result = self.ai_filter(repo_info['name'], repo_info.get('description', ''))
            if result:
                ai_passed.append({
                    'name': repo_info['name'],
                    'stars': repo_info.get('stars', 0)
                })
                print(f"\n✓ Found: {repo_info['name']} ({repo_info.get('stars', 0)} stars)")
            
            # Avoid too frequent API calls (LLM)
            if (i + 1) % batch_size == 0:
                import time
                time.sleep(1)
        
        print(f"\nAI filtering passed: {len(ai_passed)} repositories")
        
        # Return list with stars info
        return ai_passed

