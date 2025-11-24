import os
import json

base_dir = "../../data/hooked_issue"
total_sum = 0
unique_agents = set()

for agent_folder in os.listdir(base_dir):
    folder_path = os.path.join(base_dir, agent_folder)
    issue_file = os.path.join(folder_path, "issue.json")
    if os.path.isdir(folder_path) and os.path.isfile(issue_file):
        # Extract agent name by removing the last '-' and date part
        agent_name = agent_folder.rsplit('-', 1)[0]
        unique_agents.add(agent_name)
        with open(issue_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            total_count = data.get("total_count", 0)
            total_sum += total_count

print("Sum of all issue candidates:", total_sum)
print("Number of unique agent repositories checked:", len(unique_agents))