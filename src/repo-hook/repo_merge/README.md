# GitHub Agent Repository Merge Tool

Intelligently merge agent repository data collected from different tools.

## Features

- 🔍 **Smart Detection**: Automatically identify two different JSON formats
  - `github_archive_repo_*.json` - Data collected from GitHub Archive
  - `github_repo_*.json` - Data extracted from Awesome lists
- 🔄 **Deduplication**: Automatically remove duplicate repositories
- 📊 **Statistics**: Provide detailed statistical information
- ⭐ **Stars Tracking**: Keep the highest star count
- 📝 **Source Tracking**: Record all sources for each repository

## Usage

### Basic Usage

```bash
cd /home/cc/SWGENT-Bench/src/repo-hook/repo_merge
python main.py
```

### Advanced Options

```bash
# Specify data directory
python main.py --data-dir /path/to/data

# Specify output file
python main.py --output /path/to/output.json

# Simplified output (repository names list only)
python main.py --simple
```

### Parameter Description

- `--data-dir`: Data file directory (default: `/home/cc/SWGENT-Bench/data/hooked_repo`)
- `--output`: Output file path (default: `agent_repo.json` in data directory)
- `--simple`: Simplified output mode, repository names list only

## Output Format

### Full Mode (Default)

```json
{
  "generated_at": "2025-10-13 12:00:00",
  "statistics": {
    "total_repos": 220,
    "from_github_archive": 4,
    "from_github_repo": 216,
    "from_both": 0,
    "multi_source": 50
  },
  "repositories": [
    {
      "name": "Shubhamsaboo/awesome-llm-apps",
      "stars": 71852,
      "sources": ["github_repo_2025-10-13.json"],
      "source_types": ["github_repo"],
      "original_sources": ["Shubhamsaboo/awesome-llm-apps", "rohitg00/awesome-ai-apps"],
      "source_count": 1
    }
  ]
}
```

### Simplified Mode

```json
{
  "generated_at": "2025-10-13 12:00:00",
  "total_repos": 220,
  "repositories": [
    "Shubhamsaboo/awesome-llm-apps",
    "microsoft/autogen",
    ...
  ]
}
```

## Workflow

1. **Scan Directory**: Read all JSON files in the specified directory
2. **Smart Detection**: Identify JSON type by filename and data structure
3. **Data Extraction**: 
   - GitHub Archive format: Extract `{name, stars}` objects
   - GitHub Repo format: Extract string list and associate stars
4. **Deduplication**: 
   - Keep highest stars for same repository
   - Merge all source information
5. **Sort Output**: Sort by stars in descending order

## Supported JSON Formats

### Format 1: GitHub Archive

```json
{
  "agent_repos": [
    {"name": "owner/repo", "stars": 1234}
  ]
}
```

### Format 2: GitHub Repo (Awesome lists)

```json
{
  "agent_repos": ["owner/repo1", "owner/repo2"],
  "awesome_repos": [
    {"name": "owner/repo1", "stars": 1234}
  ],
  "repo_sources": {
    "owner/repo1": ["awesome-list-1", "awesome-list-2"]
  }
}
```

## Examples

```bash
# Merge all data and generate full report
python main.py

# Generate repository names list only (for other tools)
python main.py --simple

# Custom output location
python main.py --output ~/my_agent_repos.json
```

## Notes

- The tool automatically skips files named `agent_repo.json` to avoid duplicate processing
- If the same repository appears in multiple sources, all source information is retained
- Star count takes the maximum value from all sources
- Output repository list is sorted by stars in descending order
