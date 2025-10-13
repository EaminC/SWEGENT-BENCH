#!/bin/bash
# 示例：使用不同模式运行合并工具

echo "=== 示例1: 完整模式（默认） ==="
python main.py

echo ""
echo "=== 示例2: 简化模式（只输出仓库名称列表） ==="
python main.py --simple

echo ""
echo "=== 示例3: 自定义输出路径 ==="
# python main.py --output ~/my_agent_repos.json

echo ""
echo "=== 示例4: 指定数据目录 ==="
# python main.py --data-dir /path/to/your/data

echo ""
echo "完成！查看输出文件："
echo "  cat /home/cc/SWGENT-Bench/data/hooked_repo/agent_repo.json"

