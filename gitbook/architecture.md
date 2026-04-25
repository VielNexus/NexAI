# Architecture

## High-Level Flow

```text
User
  -> AgentXWeb or CLI
  -> FastAPI /v1 routes
  -> AgentX bridge
  -> Agent runtime
  -> Tool registry / LLM / memory / audit
  -> Response back to UI or CLI
```

The preferred runtime path is:

```text
UI -> API -> Agent -> Tools -> Audit -> Memory
```

The API keeps legacy fallback logic for OpenAI/Ollama chat when the AgentX bridge is unavailable, but the main design favors the unified agent path.

## Core Runtime Construction

`AgentX/agentx/runtime/bootstrap.py` builds a `RuntimeServices` object containing:

- Parsed config.
- `AgentXContext`.
- `ToolRegistry`.
- `Agent`.
- Runtime paths.
- Plugin manager.
- Skill manager.
- Hint store.
- Job store.

During startup it creates runtime directories for data, logs, config, run state, cache, temp files, audit, memory, working dir, plugins, skills, user plugins, user skills, and feature data.

## Agent Model

The agent in `AgentX/agentx/core/agent.py` is supervised-only by default.

The core pattern is:

```text
plan -> validate -> execute -> audit -> remember
```

Important behaviors:

- `unattended` mode is refused unless `agent.refuse_unattended=false`, and the default config warns that unattended guardrails are unfinished.
- Tool calls require reasons.
- Audit log writability is checked before sensitive actions.
- Memory can be enabled or replaced by a stub.
- Retrieved untrusted context is explicitly labeled and guarded.
- Per-thread unsafe mode gates destructive actions.

## FastAPI Service

`apps/api/agentx_api/app.py` creates the service and mounts routers:

- `status`
- `auth`
- `chat`
- `settings`
- `threads`
- `unsafe`
- `rag`
- `fs`
- `agentx`

The API includes CORS origins for localhost web dev, localhost static hosting, and Tauri origins.

## AgentX Bridge

`apps/api/agentx_api/agentx_bridge.py` imports `AgentX` dynamically from the app root, initializes runtime services, and exposes handles to routes.

Bridge behavior:

- Uses `AGENTX_APP_ROOT` if set; otherwise resolves the repo root.
- Uses `AGENTX_CONFIG_PATH` if set; otherwise uses `AgentX/config/agentx.toml`.
- Caches one global runtime handle.
- Creates per-request agents for thread/user-specific context.
- Supports per-session web domain allowlists.
- Updates the managed `[web.policy]` block inside the TOML config and reloads the handle.

## State And Persistence

Important state locations:

| State | Location |
| --- | --- |
| API settings | `AGENTX_API_DATA_DIR/settings.json` or API package data dir |
| API threads | `AGENTX_API_DATA_DIR/threads` or API package data dir |
| API RAG DB | `AGENTX_API_DATA_DIR/rag.sqlite3` |
| Runtime audit log | Configured by `[audit].log_path` |
| Runtime memory DB | Configured by `[memory].db_path` |
| Runtime memory events | Configured by `[memory].events_path` |
| Jobs | Runtime `jobs/` directory |
| Plugin state | Runtime `plugins/state.json` |
| Learned hints | Runtime `learning/hints.jsonl` |

## Client Architecture

AgentXWeb is a thin client:

- It stores auth session data in browser `localStorage`.
- It calls the API through `AgentXWeb/src/api/client.ts`.
- It does not own providers, tools, or config policy.
- It sends active artifact context for code canvas/file/tool-output-aware chat.

Desktop follows the same broad client model, but through a Tauri app shell.
