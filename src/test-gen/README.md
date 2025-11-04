# Test Case Generation and Verification Tool

This tool is used to create and verify test cases for agent-related repositories.

## Features

1. **Expand issue JSON**: Fetch PR patch information from GitHub API
2. **Generate test cases**: Use AI (Claude) to generate unittest test cases based on issue and patch information
3. **Run Docker tests**: Run tests on buggy version (before applying patch) and fixed version (after applying patch)

## Prerequisites

1. A repository path (e.g., `/home/cc/SWEGENT-BENCH/codex`)
2. A prepared dockerfile for the repo (e.g., `/home/cc/SWEGENT-BENCH/codex/claude.dockerfile`)
3. An issue JSON file (e.g., `/home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json`)
4. Docker installed
5. Claude command-line tool installed
6. Configured `.env` file (containing `FORGE_API_KEY` and other environment variables)
7. (Optional) Configured `GITHUB_TOKEN` environment variable to fetch PR patch information

## Usage

### Method 1: Run from repo directory (Recommended)

Run the convenience script from repo root directory:

```bash
cd /home/cc/SWEGENT-BENCH/codex
python3 /home/cc/SWEGENT-BENCH/src/test-gen/gen_test.py \
  claude.dockerfile \
  /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json
```

Or use relative paths:
```bash
cd /home/cc/SWEGENT-BENCH/codex
python3 /home/cc/SWEGENT-BENCH/src/test-gen/gen_test.py \
  claude.dockerfile \
  ../data/issue-filtered/issue_128.json
```

### Method 2: Run from any directory (using absolute paths)

```bash
# Run from any directory
python3 /home/cc/SWEGENT-BENCH/src/test-gen/main.py \
  /home/cc/SWEGENT-BENCH/codex \
  /home/cc/SWEGENT-BENCH/codex/claude.dockerfile \
  /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json
```

### Method 3: Run from test-gen directory

```bash
cd /home/cc/SWEGENT-BENCH/src/test-gen
python3 main.py \
  /home/cc/SWEGENT-BENCH/codex \
  /home/cc/SWEGENT-BENCH/codex/claude.dockerfile \
  /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json
```

### Step-by-step execution

#### Step 1: Expand issue JSON

```bash
python3 expand_issue_json.py <issue_json_path> [output_file]
```

This fetches PR patch information from GitHub API and adds it to the JSON.

#### Step 2: Generate test case

```bash
python3 claude/run_claude.py <repo_path> <expanded_issue_json_path>
```

This uses Claude AI to generate test cases. Test files will be saved in repo root directory.

#### Step 3: Run Docker tests

```bash
python3 run_docker_tests.py <repo_path> <dockerfile_path> <issue_json_path>
```

This runs tests in Docker:
1. Run test on buggy version (before applying patch) - should fail
2. Run test on fixed version (after applying patch) - should pass

## Workflow

```
1. Expand issue JSON
   ↓
2. AI reads repo and issue information
   ↓
3. AI generates test case file (test{issue_number}.py) in repo root
   ↓
4. Verify test file was created (stop if not found)
   ↓
5. Run test on buggy version (should fail)
   ↓
6. Apply patch
   ↓
7. Run test on fixed version (should pass)
```

## Test File Naming

The generated test file will be named `test{issue_number}.py` in the repository root directory.
For example:
- Issue #128 → `test128.py`
- Issue #9 → `test9.py`

The tool will automatically verify that the test file was created before proceeding to Docker tests.

## File Descriptions

- `expand_issue_json.py`: Expand issue JSON, fetch PR patch information
- `claude/run_claude.py`: Script to generate test cases using AI
- `main.py`: Main script that orchestrates the entire workflow
- `run_docker_tests.py`: Script to run tests in Docker
- `filter_issues.py`: Filter issues with only one PR (tool created earlier)

## Test Case Requirements

Generated test cases should:

1. Use Python's `unittest` framework
2. Mock all remote API calls (LLM providers, external services, etc.)
3. Fail on buggy version (FAIL)
4. Pass on fixed version (PASS)
5. Be deterministic and not depend on external services

## Notes

1. **Git state**: The tool will modify git working directory state (checkout different commits), and will attempt to restore it after completion
2. **Docker images**: Each run will build a new Docker image, which may take some time
3. **Network connection**: Expanding JSON requires access to GitHub API, recommend configuring `GITHUB_TOKEN` to avoid rate limits
4. **Test file location**: Generated test files will be saved in repo root directory, with filename format `test{number}.py` (e.g., `test128.py` for issue #128)
5. **Test file verification**: The tool automatically verifies that the test file was created before proceeding to Docker tests. If the file is not found, the process will stop with an error message.

## Troubleshooting

### Cannot fetch PR patch information

- Check if `GITHUB_TOKEN` environment variable is configured
- Check network connection
- Check error messages from `expand_issue_json.py` output

### AI cannot generate test cases

- Check if claude command is in PATH
- Check if `.env` file is configured correctly
- Check error messages from `claude/run_claude.py` output

### Docker tests fail

- Check if Docker is running
- Check if dockerfile is correct
- Check if test file has been generated
- Check detailed output from `run_docker_tests.py`
