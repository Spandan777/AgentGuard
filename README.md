# AgentGuard

Interactive runtime security sandbox for tool-using AI agents.

## Core idea
AgentGuard evaluates agent actions using policy checks, explainable risk scoring, trajectory context, and behavioural anomaly detection.

## Safety
All tools are simulated. The application does not access real credentials, real files, real email accounts, or external servers.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Demo flow

1. Open **Agent Simulator**.
2. Start a normal task and advance through safe actions.
3. Simulate **Prompt Injection** or **Privilege Escalation**.
4. Advance actions one at a time and observe the complete trajectory.
5. At HIGH risk, AgentGuard pauses before execution and requests human approval.
6. Approve once to demonstrate human-in-the-loop control, then observe the next action being re-evaluated.
7. At CRITICAL risk, AgentGuard terminates the action before the simulated tool executes.

## Attack scenarios

- **Prompt injection:** sensitive database access → external communication → simulated data upload.
- **Privilege escalation:** privilege request → admin-panel access → permission modification.

## Research prototype
The anomaly detector uses trajectory-level temporal and behavioural features with Isolation Forest. The current simulator is deterministic for reproducible demonstrations.

## Dynamic two-agent live demonstration

The project now also contains a second, dynamic runtime path for the next research demonstration:

```text
User prompt
    ↓
Agent 1 (LLM task agent)
    ↓ tool request
AgentGuard / Agent 2 (independent evaluator)
    ├── task authorization
    ├── technical safety
    ├── objective alignment
    └── trajectory risk
    ↓
ALLOW / FLAG / PAUSE / TERMINATE
    ↓ if allowed
Real public API
    ↓ result
Agent 1 chooses the next action
```

Files:

- `dynamic_agents.py` — independent Agent 1 and Agent 2 roles.
- `live_runtime.py` — enforcement boundary and trajectory logging.
- `live_tools.py` — bounded public APIs: weather, currency, country and news.
- `live_demo.py` — step-by-step agent/evaluator/API loop.
- `live_app.py` — Streamlit UI for the live demonstration.
- `llm_provider.py` — Gemini/Groq provider abstraction; keys are read from environment variables only.
- `.env.example` — configuration template with no secrets.

Run the new UI with:

```bash
streamlit run live_app.py
```

The real APIs are read-only public information services. The agent is not given arbitrary network access or credentials. Agent 1 never calls an API directly: every requested tool call passes through AgentGuard first.
