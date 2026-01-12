Bug Fixes Summary Table

================================================================================
Original Issue (Repo)                    | Fix Location & Approach
================================================================================
namastexlabs/automagik-genie #42         | Location: src/pipeline/build-run/main.py (708-715)
pnpm link --global failed                |          src/test-gen/run_docker_tests.py (293-301)
                                          |          src/repo-build/claude/run_claude.py (123-126)
                                          | Approach: Add error detection for pnpm global config failures.
                                          |          Provide guidance to set PNPM_HOME env var and add to PATH.
                                          |
ValueCell-ai/valuecell #228              | Location: src/test-gen/run_docker_tests.py (140-183, 256-263)
Commit not found                         | Approach: Enhance checkout_commit() to automatically run git fetch --all
                                          |          when commit not found locally. Add error classification.
                                          |
TransformerOptimus/SuperAGI #254         | Location: src/pipeline/build-run/main.py (724-730)
lxml compilation failed                  |          src/test-gen/run_docker_tests.py (313-321)
                                          |          src/repo-build/claude/run_claude.py (133-136)
                                          | Approach: Detect lxml compilation errors. Add error classification for
                                          |          missing C libraries. Provide apt-get commands to install
                                          |          libxml2-dev, libxslt1-dev, python3-dev, gcc.
                                          |
reworkd/AgentGPT #288                    | Location: src/pipeline/build-run/main.py (23-37, 101-106)
pyproject.toml not found but exists     |          src/repo-build/claude/run_claude.py (29-35, 178-189, 118-121)
                                          | Approach: Add validate_repo_structure() to check file existence.
                                          |          Pass structure info to LLM via REPO_STRUCTURE env var.
                                          |          Emphasize conditional COPY in prompt.
                                          |
strands-agents/sdk-python #337           | Location: src/pipeline/build-run/main.py (237-283, 343-360)
Network issue + COPY file not found      |          src/test-gen/run_docker_tests.py (343-360)
                                          |          src/repo-build/claude/run_claude.py (118-121)
                                          | Approach: Add network error retry mechanism (3 attempts, exponential
                                          |          backoff: 2, 4, 8 seconds). Detect Docker vs general network errors.
                                          |          Validate file existence before COPY.
                                          |
strands-agents/sdk-python #350           | Location: src/pipeline/build-run/main.py (237-283, 362-370)
Network timeout + Windows path separator |          src/test-gen/run_docker_tests.py (362-370, 468-482)
                                          |          src/repo-build/claude/run_claude.py (145-147)
                                          | Approach: Include timeout in network retry mechanism. Normalize path
                                          |          separators (backslash to forward slash). Use absolute paths
                                          |          in container (/workspace/tests/test350.py).
                                          |
namastexlabs/automagik-genie #390        | Location: src/pipeline/build-run/main.py (23-37, 695-700)
requirements.txt not found               |          src/repo-build/claude/run_claude.py (118-121)
                                          | Approach: Add has_requirements_txt and has_requirements_test_txt to
                                          |          structure validation. Detect requirements.txt missing errors.
                                          |          Emphasize conditional file operations.
                                          |
BloopAI/vibe-kanban #917                 | Location: src/pipeline/build-run/main.py (716-723)
externally-managed-environment           |          src/test-gen/run_docker_tests.py (303-311)
                                          |          src/repo-build/claude/run_claude.py (128-131)
                                          | Approach: Detect PEP 668 errors. Provide three solutions: use virtual
                                          |          environment, --break-system-packages flag, or --user flag.
                                          |          Add guidance in prompt.
                                          |
restatedev/restate #423                  | Location: src/pipeline/build-run/main.py (23-37, 731-738)
Rust project trying to use pip install   |          src/test-gen/run_docker_tests.py (333-341)
                                          |          src/repo-build/claude/run_claude.py (77, 81-85, 139-142)
                                          | Approach: Add has_cargo_toml check in structure validation. Detect Rust
                                          |          project errors. Add Rust base image selection and project type
                                          |          detection in prompt. Guide to use cargo build instead of pip install.
                                          |
reworkd/AgentGPT #749                    | Location: src/pipeline/build-run/main.py (739-746)
poetry executable not found               |          src/test-gen/run_docker_tests.py (323-331)
                                          |          src/repo-build/claude/run_claude.py (127-130)
                                          | Approach: Detect poetry not found errors. Provide solution to add pipx bin
                                          |          to PATH: ENV PATH="/root/.local/bin:$PATH". Add poetry installation
                                          |          guidance in prompt.
                                          |
reworkd/AgentGPT #878                    | Location: src/test-gen/run_docker_tests.py (372-382)
ModuleNotFoundError: platform is not      | Approach: Detect ModuleNotFoundError with platform module conflicts.
a package                                |          Provide suggestions: check PYTHONPATH, use absolute imports,
                                          |          check for directory naming conflicts with stdlib.
                                          |

================================================================================
File Summary
================================================================================
src/pipeline/build-run/main.py          | ~190 lines changed
                                         | Added validate_repo_structure(), enhanced error classification,
                                         | network retry mechanism
                                         |
src/repo-build/claude/run_claude.py     | ~74 lines added
                                         | Added repository structure info to prompt, enhanced Dockerfile
                                         | best practices guidance
                                         |
src/test-gen/run_docker_tests.py        | ~116 lines added
                                         | Enhanced error classification, improved path handling, added
                                         | module import error detection
                                         |

================================================================================
Fix Categories
================================================================================
1. Error Classification: 11 new error types added across 2 files
2. Prompt Enhancement: 8 new guidance sections added
3. Functionality: Network retry, path normalization, structure validation
