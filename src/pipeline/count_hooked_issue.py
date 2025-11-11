import os
import json

base_dir = "../../data/hooked_issue"
total_sum = 0

# Loop through each folder in base_dir
for agent_folder in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, agent_folder)
    issue_file = os.path.join(folder_path, "issue.json")
    if os.path.isdir(folder_path) and os.path.isfile(issue_file):
        with open(issue_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_count = data.get("total_count", 0)
            total_sum += total_count

print("Sum of all total_count:", total_sum)