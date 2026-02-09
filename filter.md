cd /home/cc/SWEGENT-BENCH

# After merging two recall streams, keep only repos that have test paths; output includes test_paths and writes detailed agent_repo.json
python -m src.repo_hook.repo_merge.main --detailed --filter-has-test

# If running directly under the repo_merge directory
cd src/repo-hook/repo_merge
python main.py --detailed --filter-has-test

# Specify heuristic path JSON (default is data/inlight/test_path_patterns_topk.json)
python main.py --detailed --filter-has-test --test-patterns-json /path/to/test_path_patterns_topk.json

cd /home/cc/SWEGENT-BENCH

# When disabled: same as before, PRs are not required to contain test
python -m src.issue-hook.issue_crawler TsinghuaDatabaseGroup/DB-GPT --local-clone

# When enabled: keep only issues where at least one linked PR's patch modifies test files
python -m src.issue-hook.issue_crawler TsinghuaDatabaseGroup/DB-GPT --local-clone 
