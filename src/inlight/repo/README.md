# inlight.repo — 按测试路径筛选 Repo 的启发式流程

用「README + 文件树（最多 2 层）」让 AI 推断每个 repo 的测试路径，再聚合出前 k 个常用路径，供后续严格筛查使用。

## 流程

1. **复用手头已有的 agent repo 列表**
   - **默认**从 `data/hooked_repo/agent_repo.json` 的 `repositories[].name` 读取（即现有爬取得到的大量 agent 相关 repo）。
   - 若加 `--small`，则只使用 `src/inlight/repo/repos.json` 里的小列表（适合本地试跑）。

2. **单 repo：README + 2 层文件树 → AI → 仅 JSON**
   - 拉取 README（raw）和默认分支的 git tree（递归一层，再按路径深度保留最多 2 层）。
   - 把 README 和树文本发给 LLM，提示词里带示例，要求**只返回一个 JSON**：
     - 键：`test_paths`，值：字符串数组，表示推断出的测试路径/文件；
     - 若无任何测试则返回 `{"test_paths": []}`。
   - 每个 repo 结果存为：`data/inlight/repo_results/<owner>-<repo>.json`。

3. **聚合**
   - 扫描 `data/inlight/repo_results/*.json`，统计所有 `test_paths` 中路径出现次数。
   - 取前 k 个最常出现的路径/文件名，写入 `data/inlight/test_path_patterns_topk.json`（含 `paths` 与 `counts`），供后续算法使用。

## 用法

在项目根执行（需配置 `.env` 中的 `GITHUB_TOKEN`、`FORGE_API_KEY` 等）。

### 1) discover_tests — 按 repo 拉 README + 文件树，调 AI 得到 test_paths

```bash
# 默认：用 data/hooked_repo/agent_repo.json 的完整列表
python -m src.inlight.repo.discover_tests

# 只跑前 100 个 repo
python -m src.inlight.repo.discover_tests --limit 100

# 只用 repos.json 里的小列表试跑
python -m src.inlight.repo.discover_tests --small

# 组合：小列表且只跑前 5 个
python -m src.inlight.repo.discover_tests --small --limit 5
```

| 参数 | 说明 |
|------|------|
| `--small` | 不用 agent_repo.json，改用 `src/inlight/repo/repos.json` 的小列表 |
| `--limit N` | 只处理前 N 个 repo（如 `--limit 100`） |

### 2) aggregate — 汇总为 top-k 路径（可加最小出现次数）

```bash
# 默认：top 50，不筛 count
python -m src.inlight.repo.aggregate

# 只要前 20 个，且只保留出现次数 > 3 的路径
python -m src.inlight.repo.aggregate 20 --min-count 3

# 前 100 个，count > 5
python -m src.inlight.repo.aggregate 100 --min-count 5
```

| 参数 | 说明 |
|------|------|
| `top_k` | 位置参数，取出现次数最高的前 k 个路径（默认 50） |
| `--min-count N` | 只保留在多个 repo 中出现次数 **大于 N** 的路径（如 `--min-count 3`） |

## 输出

- `data/inlight/repo_results/<owner>-<repo>.json`：`{"repo": "owner/repo", "test_paths": ["...", ...]}`
- `data/inlight/test_path_patterns_topk.json`：`{"top_k": 50, "min_count": 0, "paths": [...], "counts": {"path": n, ...}}`

## 依赖

- 复用 `src/forge/api.py` 的 LLM 调用。
- GitHub API：需 `GITHUB_TOKEN`（可选，建议设置以免限流）。
