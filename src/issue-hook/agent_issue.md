## 1. Definition of an Agent Issue

An **agent issue** refers to a user-reported problem (e.g., a bug report or a feature request) that occurs in an LLM-based agent system and that is related to components or behaviors unique to agent systems. According to the paper, agent issues include failures or maintenance needs tied to LLM provider integration, tool invocation, memory mechanisms, LLM operation, workflows, and utilities within agent systems.


 

## 2. Taxonomy of Agent Issues

Here we presents a taxonomy consisting of **6 major categories** and **20 sub-categories**. Below is the taxonomy as reported.

### A. Incompatibility with LLM providers  

* **Incompatible dependencies**: Missing or misused libraries of LLM providers.
* **Unsupported models**: Lack of support for recently released LLMs.
* **Incompatible parameters to LLM providers**: Use of undefined parameters or missing parameters in LLM query interfaces.

### B. Tool-related issues  

* **Tool dependency issues**: Missing or misused libraries required for agent-invoked tools.
* **Tool configuration issues**: Misconfiguration of settings for agent-invoked tools.
* **Tool implementation errors**: Incorrect implementation of self-developed agent-invoked tools.
* **Misuse tool interfaces**: Incorrect tool invocation due to missing or wrong parameters.

### C. Memory-related issues  

* **Memory initialization issues**: Incomplete or inconsistent memory states due to database initialization or workspace resetting problems.
* **Memory content errors**: Incorrect message attributes, misleading content, or content loss caused by faulty storage logic.
* **Memory dependency issues**: Incorrect internal module dependencies or external libraries required by memory operations.

### D. LLM operation issues 

* **Model access misconfiguration**: Misconfiguration such as incorrect model binding or authentication credentials (e.g., API keys).
* **Token usage misconfiguration**: LLM token management issues such as incorrect limits or pricing configuration.
* **Incorrect model output handlers**: Incorrect parsing logic for model output or missing handlers for unexpected model behaviors (e.g., empty or exceptional responses).
* **Model dependency issues**: Missing or incompatible libraries related to model operation (e.g., tokenization or transformer dependency conflicts).
* **Context length issues**: Truncated outputs caused by exceeding context limits or miscalculating context length.
* **Prompt-related issues**: Suboptimal prompt content or prompt management issues (e.g., failure to set or update prompts).

### E. Workflow issues  

* Abnormal agent workflows such as hanging, repeated loops, or other execution anomalies in the agent orchestration.

### F. Utility issues

* **Utility implementation issues**: Implementation errors in LLM-unrelated components (e.g., UI, Docker, logging).
* **Utility dependency issues**: Missing or incompatible libraries required by general utilities (e.g., testing or file operations).
* **Utility configuration issues**: External component misconfiguration (e.g., I/O paths, network settings).

 
## 3. Indicators that an Issue is an Agent Issue

According to your analysis and inclusion criteria, the following signals indicate that a GitHub issue likely qualifies as an agent issue:

* The issue is tied to LLM provider usage (e.g., SDK parameters, model names, provider authentication).
* The issue references prompt behaviors, prompt templates, or incorrect prompt management.
* The issue concerns memory behaviors (e.g., incorrect storage, missing history, content corruption).
* The issue involves tool invocation failures, tool configuration, or tool implementation errors.
* The issue reports workflow anomalies (e.g., hanging agent loop, repeated tasks, failed orchestrations).
* The issue includes developer-committed patches that change code in the aforementioned agent-specific components.

 

## 4. Practical Checklist to Decide if an Issue is an Agent Issue

* Does the issue explicitly reference an LLM provider, model name, SDK, or API key? (Yes → Agent Issue)
* Does the issue mention prompt content, prompt templates, or prompt management problems? (Yes → Agent Issue)
* Does the issue report memory-related symptoms (missing history, corrupted stored content, initialization issues)? (Yes → Agent Issue)
* Does the issue involve tool invocation, tool parameters, tool configuration, or tool implementation errors? (Yes → Agent Issue)
* Does the issue describe agent workflow anomalies (hangs, loops, unexpected repeated actions)? (Yes → Agent Issue)
* Is the issue resolved by a developer patch that changes components such as LLM calls, memory store logic, tool wrappers, prompt templates, or orchestration code? (Yes → Agent Issue)

If at least one of the above is true and the issue is closed with a developer-committed patch addressing that concern, the issue aligns with the paper’s definition of an agent issue.
 