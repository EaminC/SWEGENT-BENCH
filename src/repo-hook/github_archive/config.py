"""
Configuration file
"""

# Agent-related keywords list (for initial filtering)
AGENT_KEYWORDS = [
    "agent",
    "llm",
    "langchain",
    "autogen",
    "openai",
    "chatgpt",
    "gpt",
    "claude",
    "anthropic",
    "assistant",
    "chatbot",
    "ai assistant",
    "autonomous",
    "tool calling",
    "function calling",
    "prompt",
    "memory store",
    "vector store",
    "embedding",
    "rag",
    "retrieval",
    "planner",
    "orchestration",
    "multi-agent",
    "workflow",
]

# Agent Repository definition (for LLM判断)
AGENT_REPO_DEFINITION = """
## Agent Repository Definition

An **Agent Repository** refers to a codebase that implements or contains an **LLM-based agent system**.

### Core Component Characteristics:

1. **LLM-Controlled "Brain"**:
   - Contains task decomposition and scheduling (planning) logic
   - Maintains and retrieves historical actions or conversation records (memory)

2. **Perception Component**:
   - Receives and processes information from the environment or external inputs (e.g., user inputs, events, files, or sensors)

3. **Action/Tooling Component**:
   - Executes actions by invoking external tools or APIs (e.g., search, shell execution, database queries, third-party service calls, or custom plugins)

4. **Single/Multi-Agent Architecture Support**:
   - Supports either single-agent operation or multi-agent orchestration logic for collaboration

5. **Integration with LLM Providers**:
   - Explicitly uses or is compatible with one or more LLM providers (via SDKs, API keys, or model configuration parameters)

### Judgment Criteria (3+ criteria = likely Agent Repository, 5+ = highly likely):

1. README or code explicitly mentions "agent", "planner", "tool invocation", "memory", or "LLM"
2. Code calls or depends on an LLM provider's SDK
3. Contains prompt/, templates/, or prompts/ directories, or code managing prompts
4. Implements memory storage (e.g., vector database, session store, memory module)
5. Includes wrappers or calls to external tools/plugins
6. Contains orchestration or an agent loop (planner/scheduler)
"""

# LLM judgment prompt template
JUDGE_PROMPT_TEMPLATE = """
{agent_repo_definition}

Now, please determine whether the following GitHub repository is an Agent Repository.

**Repository Name**: {repo_name}
**Repository Description**: {repo_description}
**Repository README** (first 3000 chars):
{repo_readme}

Please carefully analyze the repository information to determine if it fits the Agent Repository definition.

IMPORTANT: You must answer with ONLY "YES" or "NO". No explanations, no other text.
- Answer "YES" if this is clearly an Agent Repository
- Answer "NO" if it is not or if information is insufficient

Your answer (YES or NO only):
"""

