# Episode 3 Agentic Architecture

This implementation adds:

- specialist agents under `app/agents/`
- typed tools under `app/tools/`
- runtime orchestration under `app/agent_runtime/`
- API endpoints for agent chat, traces, workflows, and approvals
- Foundry deployment artifacts under `infra/foundry-agents/`

Core flow:

1. `POST /agents/chat` starts a trace.
2. The router chooses a specialist agent.
3. The specialist agent invokes only typed, permission-checked tools.
4. The runtime records memory and trace events.
5. Workflows such as private dining can create approval records.
