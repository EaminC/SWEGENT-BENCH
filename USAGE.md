# SWEGENT-BENCH 使用说明

## 概述

SWEGENT-BENCH 是一个用于生成和验证 Dockerfile 和单元测试的自动化工作流系统。最新版本包含了多项改进，提高了成功率和错误处理能力。

## 主要改进（v2.0）

### 1. Git 操作改进
- **自动 fetch**: 如果 commit 不存在，会自动从远程获取
- **3-way merge**: Patch 应用失败时自动尝试 3-way merge
- **更好的错误处理**: 提供详细的错误信息和解决建议

### 2. 文件存在性检查
- **仓库结构验证**: 在生成 Dockerfile 前检查关键文件/目录
- **智能 COPY**: 避免 COPY 不存在的文件导致构建失败

### 3. 错误分类和建议
- **自动错误分类**: 识别常见错误类型（缺少文件、setuptools 冲突等）
- **针对性建议**: 为每种错误类型提供修复建议

### 4. Setuptools 冲突处理
- **测试文件位置优化**: 优先将测试文件放在 `tests/` 目录
- **避免冲突**: 防止多个测试文件导致 setuptools 构建失败

## 使用方法

### 1. 生成 Dockerfile

```bash
cd /home/cc/SWEGENT-BENCH
python src/pipeline/build-run/main.py <repo_path> [选项]
```

**示例**:
```bash
# 基本用法
python src/pipeline/build-run/main.py /path/to/repo

# 使用 agentless 初始化（推荐）
python src/pipeline/build-run/main.py /path/to/repo --use-agentless-init

# 指定最大重试次数
python src/pipeline/build-run/main.py /path/to/repo --max-dockerfile-retries 3
```

**选项**:
- `--max-dockerfile-retries N`: Dockerfile 生成最大重试次数（默认: 1）
- `--dockerfile NAME`: Dockerfile 名称（默认: claude.dockerfile）
- `--use-agentless-init`: 使用 agentless 方法生成初始 Dockerfile
- `--issue-json PATH`: 指定 issue JSON 文件（用于测试生成）

### 2. 生成测试用例

```bash
cd /home/cc/SWEGENT-BENCH
python src/test-gen/main.py <repo_path> <issue_json_path>
```

**示例**:
```bash
python src/test-gen/main.py /path/to/repo /path/to/issue_128.json
```

**功能**:
- 自动扩展 issue JSON（获取 PR patch 信息）
- 使用 AI 生成测试用例
- 测试文件会优先保存在 `tests/` 目录（如果存在）

### 3. 运行 Docker 测试

```bash
cd /home/cc/SWEGENT-BENCH
python src/test-gen/run_docker_tests.py <repo_path> <dockerfile_path> <issue_json_path>
```

**示例**:
```bash
python src/test-gen/run_docker_tests.py \
  /path/to/repo \
  /path/to/repo/claude.dockerfile \
  /path/to/issue_128.json
```

**功能**:
- 在 buggy 版本上运行测试（应该失败）
- 在 fixed 版本上运行测试（应该通过）
- 自动处理 Git checkout 和 patch 应用
- 提供错误分类和建议

### 4. 完整工作流

```bash
# 步骤 1: 生成 Dockerfile
python src/pipeline/build-run/main.py /path/to/repo \
  --use-agentless-init \
  --max-dockerfile-retries 3

# 步骤 2: 生成测试用例
python src/test-gen/main.py /path/to/repo /path/to/issue.json

# 步骤 3: 验证测试
python src/test-gen/run_docker_tests.py \
  /path/to/repo \
  /path/to/repo/claude.dockerfile \
  /path/to/issue.json
```

## 错误处理

### 常见错误及解决方案

#### 1. "tests/: not found" 或 "pyproject.toml: not found"

**原因**: Dockerfile 尝试 COPY 不存在的文件/目录

**解决方案**:
- 系统会自动检查仓库结构
- 在 Dockerfile 生成时提供文件存在性信息
- 使用条件 COPY: `RUN if [ -d "tests" ]; then cp -r tests/ /app/tests/; fi`

#### 2. "Multiple top-level modules discovered"

**原因**: 多个测试文件在根目录导致 setuptools 冲突

**解决方案**:
- 测试文件会自动优先保存在 `tests/` 目录
- 如果 `tests/` 不存在，会在生成时提示创建
- 可以在 `pyproject.toml` 中排除: `[tool.setuptools] exclude = ["test*.py"]`

#### 3. "Cannot checkout commit" 或 "patch does not apply"

**原因**: Git commit 不存在或代码已改变

**解决方案**:
- 系统会自动尝试 `git fetch --all`
- Patch 应用失败时会尝试 3-way merge
- 如果仍然失败，会提供详细错误信息

#### 4. "pnpm install" 或 "npm run build" 失败

**原因**: 依赖安装或构建失败

**解决方案**:
- 检查网络连接
- 使用镜像源: `npm config set registry https://registry.npmmirror.com`
- 查看详细错误信息（系统会自动分类）

## 输出说明

### Dockerfile 生成输出

```
================================================================================
Generating claude.dockerfile...
================================================================================

Repository structure check:
  ✓ has_tests_dir: True
  ✗ has_pyproject: False
  ✓ has_package_json: True
  ...
```

### 测试运行输出

```
================================================================================
Running Docker Tests
================================================================================

Test 1: Buggy Version (before applying patch)
================================================================================
Running test in Docker (Buggy Version)...
Building Docker image: test-buggy-version
...

Buggy version test result: FAIL
Output:
...

Error classification: missing_directory
Suggestions:
  - Check if tests/ directory exists before COPY
  - Use conditional COPY or create empty directory
```

## 环境要求

- Python 3.8+
- Docker（需要运行权限）
- Git
- Claude CLI（用于 AI 生成）

## 配置

### 环境变量

创建 `.env` 文件（在项目根目录）:

```bash
# Claude API 配置
ANTHROPIC_API_KEY=your_api_key_here

# 其他配置...
```

### Docker 权限

如果遇到 Docker 权限问题:

```bash
sudo usermod -aG docker $USER
newgrp docker  # 或重新登录
```

## 故障排除

### 1. Docker 不可用

```bash
# 检查 Docker 状态
docker ps

# 如果权限被拒绝，添加到 docker 组
sudo usermod -aG docker $USER
```

### 2. Git 操作失败

```bash
# 确保仓库是最新的
cd /path/to/repo
git fetch --all
git pull
```

### 3. 测试文件找不到

系统会按以下顺序查找测试文件:
1. `tests/test{issue_number}.py`（优先）
2. `test{issue_number}.py`（根目录）
3. 其他可能的命名格式

确保测试文件使用正确的命名格式。

## 最佳实践

1. **使用 agentless 初始化**: 使用 `--use-agentless-init` 获得更好的起始点
2. **多次重试**: 设置 `--max-dockerfile-retries 3` 提高成功率
3. **检查仓库结构**: 在生成 Dockerfile 前确保关键文件存在
4. **使用 tests/ 目录**: 将测试文件放在 `tests/` 目录避免冲突
5. **查看错误分类**: 注意系统提供的错误分类和建议

## 更新日志

### v2.0 (最新)
- ✅ 改进 Git checkout 和 patch 应用
- ✅ 添加文件存在性检查
- ✅ 添加错误分类和建议
- ✅ 优化测试文件位置
- ✅ 改进错误处理

### v1.0
- 基础 Dockerfile 生成
- 基础测试生成
- Docker 测试运行

## 贡献

欢迎提交 Issue 和 Pull Request！

## 许可证

[根据项目许可证]

