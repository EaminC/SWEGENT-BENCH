"""Prompt for LLM to infer test paths from README + file tree."""

SYSTEM_PROMPT = """You are a codebase analyst. Given a repository README and a shallow file tree (at most 2 directory levels), you must identify which paths are test-related: test directories, test files, or config files that define test locations (e.g. pytest.ini, jest.config.js).

Rules:
- Output ONLY valid JSON. No markdown, no explanation, no other text.
- Use this exact format: {"test_paths": ["path1", "path2", ...]}
- Paths must be exactly as they appear in the file tree (same spelling and depth).
- If there are no test-related paths, output: {"test_paths": []}
"""


def build_user_message(readme: str, tree_text: str, repo: str) -> str:
    return f"""Repository: {repo}

=== README (excerpt) ===
{readme[:8000] if readme else "(no README)"}

=== File tree (paths, max 2 levels) ===
{tree_text}

Return a JSON object with one key "test_paths" (array of strings). Example:
{{"test_paths": ["tests", "tests/test_example.py", "pytest.ini"]}}

If no test paths exist, return:
{{"test_paths": []}}

Output only the JSON object, nothing else."""
