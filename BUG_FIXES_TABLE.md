# Bug Fixes Summary Table

| Original Issue | Fix Location & Approach |
|----------------|------------------------|
| **#1: pnpm link --global 失败**<br/>namastexlabs/automagik-genie #42<br/>`pnpm does not know where to store global binaries` | **Location**: `main.py` (708-715), `run_docker_tests.py` (293-301), `run_claude.py` (123-126)<br/>**Approach**: Add error detection for pnpm global config failures. Provide guidance to set `PNPM_HOME` env var and add to PATH in Dockerfile prompt. |
| **#2: Commit 不存在**<br/>ValueCell-ai/valuecell #228<br/>`Commit c764c8dc52e18a78c98c1f3eb64aeca300160f39 not found` | **Location**: `run_docker_tests.py` (140-183, 256-263)<br/>**Approach**: Enhance `checkout_commit()` to automatically run `git fetch --all` when commit not found locally. Add error classification with suggestions. |
| **#3: lxml 编译失败**<br/>TransformerOptimus/SuperAGI #254<br/>`lacks the necessary C development libraries` | **Location**: `main.py` (724-730), `run_docker_tests.py` (313-321), `run_claude.py` (133-136)<br/>**Approach**: Detect lxml compilation errors. Add error classification for missing C libraries. Provide apt-get commands to install libxml2-dev, libxslt1-dev, python3-dev, gcc. |
| **#4: pyproject.toml 找不到但文件存在**<br/>reworkd/AgentGPT #288<br/>`"/platform/pyproject.toml": not found; even though the file exists` | **Location**: `main.py` (23-37, 101-106), `run_claude.py` (29-35, 178-189, 118-121)<br/>**Approach**: Add `validate_repo_structure()` to check file existence. Pass structure info to LLM via `REPO_STRUCTURE` env var. Emphasize conditional COPY in prompt. |
| **#5: 网络问题 + COPY 文件找不到**<br/>strands-agents/sdk-python #337<br/>`Network issue: could not connect to auth.docker.io`<br/>`COPY .github/scripts/python/requirements.txt ... failed` | **Location**: `main.py` (237-283, 343-360), `run_docker_tests.py` (343-360), `run_claude.py` (118-121)<br/>**Approach**: Add network error retry mechanism (3 attempts, exponential backoff: 2, 4, 8 seconds). Detect Docker vs general network errors. Validate file existence before COPY. |
| **#6: 网络超时 + Windows 路径分隔符**<br/>strands-agents/sdk-python #350<br/>`Network timeout`<br/>`can't open file '/workspace/tests\\test350.py'` | **Location**: `main.py` (237-283, 362-370), `run_docker_tests.py` (362-370, 468-482), `run_claude.py` (145-147)<br/>**Approach**: Include timeout in network retry mechanism. Normalize path separators (backslash to forward slash). Use absolute paths in container (`/workspace/tests/test350.py`). |
| **#7: requirements.txt 文件不存在**<br/>namastexlabs/automagik-genie #390<br/>`"/requirements.txt": not found "/requirements-test.txt": not found` | **Location**: `main.py` (23-37, 695-700), `run_claude.py` (118-121)<br/>**Approach**: Add `has_requirements_txt` and `has_requirements_test_txt` to structure validation. Detect requirements.txt missing errors. Emphasize conditional file operations. |
| **#8: externally-managed-environment**<br/>BloopAI/vibe-kanban #917<br/>`error: externally-managed-environment hint: See PEP 668` | **Location**: `main.py` (716-723), `run_docker_tests.py` (303-311), `run_claude.py` (128-131)<br/>**Approach**: Detect PEP 668 errors. Provide three solutions: use virtual environment, `--break-system-packages` flag, or `--user` flag. Add guidance in prompt. |
| **#9: Rust 项目尝试 pip install**<br/>restatedev/restate #423<br/>`tried to RUN pip install --no-cache-dir . but there is no setup.py or pyproject.toml` | **Location**: `main.py` (23-37, 731-738), `run_docker_tests.py` (333-341), `run_claude.py` (77, 81-85, 139-142)<br/>**Approach**: Add `has_cargo_toml` check in structure validation. Detect Rust project errors. Add Rust base image selection and project type detection in prompt. Guide to use `cargo build` instead of `pip install`. |
| **#10: poetry 可执行文件找不到**<br/>reworkd/AgentGPT #749<br/>`poetry executable not found in PATH after installation via pipx` | **Location**: `main.py` (739-746), `run_docker_tests.py` (323-331), `run_claude.py` (127-130)<br/>**Approach**: Detect poetry not found errors. Provide solution to add pipx bin to PATH: `ENV PATH="/root/.local/bin:$PATH"`. Add poetry installation guidance in prompt. |
| **#11: ModuleNotFoundError: 'platform' is not a package**<br/>reworkd/AgentGPT #878<br/>`ModuleNotFoundError: No module named 'platform.reworkd_platform'` | **Location**: `run_docker_tests.py` (372-382)<br/>**Approach**: Detect ModuleNotFoundError with platform module conflicts. Provide suggestions: check PYTHONPATH, use absolute imports, check for directory naming conflicts with stdlib. |

## File Summary

| File | Lines Changed | Main Changes |
|------|---------------|--------------|
| `src/pipeline/build-run/main.py` | ~190 lines | Added `validate_repo_structure()`, enhanced error classification, network retry mechanism |
| `src/repo-build/claude/run_claude.py` | ~74 lines | Added repository structure info to prompt, enhanced Dockerfile best practices guidance |
| `src/test-gen/run_docker_tests.py` | ~116 lines | Enhanced error classification, improved path handling, added module import error detection |

## Fix Categories

1. **Error Classification**: 11 new error types added across 2 files
2. **Prompt Enhancement**: 8 new guidance sections added
3. **Functionality**: Network retry, path normalization, structure validation

