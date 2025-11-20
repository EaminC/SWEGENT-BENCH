# Pipeline Build-Run 使用说明

完整的 pipeline，包含 Dockerfile 生成、构建验证和测试生成。

## 功能特性

### Phase 1: Dockerfile 生成循环
- 生成 `claude.dockerfile`（使用交互式 claude）
- 尝试构建 Docker 镜像
- 如果失败，将错误反馈给 agent 重新生成
- 循环直到成功或达到最大迭代次数

### Phase 2: 测试生成循环（可选）
- 生成测试用例（使用交互式 claude）
- 运行测试验证：
  - Buggy version 应该失败（FAIL）
  - Fixed version 应该成功（PASS）
- 如果不符合条件，继续循环改进测试

### 大循环（可选，默认关闭）
- 如果测试失败，询问 subagent 是否因为 Dockerfile 配置问题
- 如果是，同时重新生成 Dockerfile 和测试
- 需要 `--enable-full-loop` 参数启用

## 使用方法

### 基本用法（只生成 Dockerfile）

```bash
cd /path/to/repo
python3 /home/cc/SWEGENT-BENCH/src/pipeline/build-run/main.py
```

### 生成 Dockerfile + 测试

```bash
cd /path/to/repo
python3 /home/cc/SWEGENT-BENCH/src/pipeline/build-run/main.py \
  --issue-json /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json
```

### 完整参数示例

```bash
cd /path/to/repo
python3 /home/cc/SWEGENT-BENCH/src/pipeline/build-run/main.py \
  --max-dockerfile-retries 3 \  # Dockerfile 最大重试 3 次
  --max-test-retries 5 \  # 测试生成最大重试 5 次
  --issue-json /home/cc/SWEGENT-BENCH/data/issue-filtered/issue_128.json \
  --enable-cofix  # 启用协同修复模式（如果 Dockerfile 问题导致测试失败）
```

## 参数说明

- `--max-dockerfile-retries`: Dockerfile 生成最大重试次数（默认: 1）
- `--max-test-retries`: 测试生成最大重试次数（默认: 3）
- `-d, --dockerfile`: Dockerfile 名称（默认: claude.dockerfile）
- `--issue-json`: Issue JSON 文件路径（如果提供，会进入 Phase 2 测试生成）
- `--enable-cofix`: 启用协同修复模式（默认: 关闭）
  - 如果测试失败且 agent 判断是 Dockerfile 问题，会同时重新生成 Dockerfile 和测试
- `repo_path`: 仓库路径（可选，默认: 当前目录）

## 工作流程

```
┌─────────────────────────────────────┐
│ Phase 1: Dockerfile Generation      │
│ ┌─────────────────────────────────┐ │
│ │ 1. Generate Dockerfile (claude) │ │
│ │ 2. Build Docker image           │ │
│ │ 3. Agent判断是否成功            │ │
│ │ 4. 如果失败，反馈并循环          │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
           ↓ (如果成功)
┌─────────────────────────────────────┐
│ Phase 2: Test Generation (可选)     │
│ ┌─────────────────────────────────┐ │
│ │ 1. Generate Test (claude)       │ │
│ │ 2. Run Test Verification        │ │
│ │    - Buggy: 应该 FAIL           │ │
│ │    - Fixed: 应该 PASS           │ │
│ │ 3. 如果不符合条件，循环改进       │ │
│ └─────────────────────────────────┘ │
│                                      │
│ ┌─────────────────────────────────┐ │
│ │ Full Loop (可选，需启用)        │ │
│ │ 如果测试失败且 agent 判断是      │ │
│ │ Dockerfile 问题，则同时重新生成  │ │
│ │ Dockerfile 和测试               │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## 示例输出

### Phase 1: Dockerfile 生成

```
================================================================================
PHASE 1: Dockerfile Generation
================================================================================

================================================================================
Dockerfile Iteration 1/3
================================================================================
Generating claude.dockerfile...
[Claude 交互式运行...]
✓ Dockerfile generation completed

Building Docker image...
✓ Docker build succeeded
✓ Dockerfile build successful!
```

### Phase 2: 测试生成

```
================================================================================
PHASE 2: Test Generation
================================================================================

================================================================================
Test Iteration 1/3
================================================================================
Generating test case...
[Claude 交互式运行...]
✓ Test generation completed

Running test verification...
Buggy version test: ✓ Failed as expected
Fixed version test: ✓ Passed as expected
✓ SUCCESS: Test verification passed!
```

## 循环逻辑说明

### Dockerfile 循环
- 每次迭代只使用上一次的反馈
- 不保留历史反馈
- 成功则退出循环

### 测试生成循环
- 检查条件：Buggy FAIL + Fixed PASS
- 如果不符合，继续循环改进测试
- 成功则退出循环

### 协同修复模式（Co-fix Mode）
- 默认关闭，需要 `--enable-cofix` 启用
- 只在测试失败时触发
- 询问 subagent 是否 Dockerfile 问题
- 如果是，同时重新生成 Dockerfile 和测试
- 最多循环 3 次

## 注意事项

1. **交互式运行**: Claude 会以交互式方式运行，你可以与它交互
2. **反馈机制**: 每次循环只使用上一次的反馈，不保留历史
3. **Agent 判断**: 使用 subagent 判断构建/测试是否成功
4. **大循环**: 默认不启用，需要显式启用

## 故障排除

### Docker 权限问题
Pipeline 会自动检测并提示解决方案。

### 测试验证失败
- 检查测试文件是否正确生成
- 检查 Dockerfile 是否正确配置
- 可以启用 `--enable-cofix` 让 agent 判断是否需要同时重新生成 Dockerfile 和测试

### Claude 交互问题
- 确保 Claude CLI 已安装
- 确保 `~/.local/bin` 在 PATH 中
