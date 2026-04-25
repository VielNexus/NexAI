# Repository Map

## Root Files

| Path | Purpose |
| --- | --- |
| `README.md` | Main project overview, install instructions, lifecycle commands, auth notes |
| `install.sh` | Fresh Ubuntu installer that clones/builds/provisions AgentX |
| `install-agentx.sh` | Bundle-local bootstrap installer for the `agentx` launcher |
| `start-agentx.ps1` | Windows PowerShell helper |
| `RELEASE.md` | Release packaging instructions |
| `scripts/package_release.py` | Deterministic release archive builder |
| `LICENSE` | Apache-2.0 license |

## `AgentX`

`AgentX` is the Python package that contains the core runtime and CLI.

| Path | Purpose |
| --- | --- |
| `AgentX/pyproject.toml` | Python package metadata; exposes `agentx` and `agentx` console scripts |
| `AgentX/config/agentx.toml` | Default runtime configuration |
| `AgentX/agentx/cli/` | CLI parser and command implementations |
| `AgentX/agentx/core/` | Agent, LLM, policy, memory, audit, orchestration, context, unsafe-mode logic |
| `AgentX/agentx/tools/` | Built-in tools such as filesystem, web, RAG, repo, exec, selfcheck |
| `AgentX/agentx/install/` | Setup wizard, install model, runtime provisioning, service lifecycle helpers |
| `AgentX/agentx/runtime/` | Runtime service construction and path management |
| `AgentX/agentx/plugins/` | Plugin discovery, validation, enable/disable state, tool registration |
| `AgentX/agentx/skills/` | `SKILL.md` import/discovery logic |
| `AgentX/agentx/jobs/` | Supervised autonomous job runner and storage |
| `AgentX/tests/` | Python tests for install, CLI, runtime, jobs, health, plugins, LLM, and packaging |

## `apps/api`

`apps/api` is the FastAPI service used by the web UI and CLI runtime bridge.

| Path | Purpose |
| --- | --- |
| `apps/api/agentx_api/app.py` | FastAPI app factory and router registration |
| `apps/api/agentx_api/config.py` | Environment-driven API configuration |
| `apps/api/agentx_api/auth.py` | Optional bearer-token auth session store |
| `apps/api/agentx_api/agentx_bridge.py` | Bridge from API requests into `AgentX` runtime services |
| `apps/api/agentx_api/routes/` | HTTP endpoint modules |
| `apps/api/agentx_api/rag/` | API-side SQLite RAG store and chunking |
| `apps/api/agentx_api/fs_access/` | API-side filesystem policy and operations |
| `apps/api/agentx_api/web_access/` | API-side web policy, search, fetch, and errors |
| `apps/api/tests/` | API tests |

## `AgentXWeb`

`AgentXWeb` is the browser UI.

| Path | Purpose |
| --- | --- |
| `AgentXWeb/package.json` | Vite/React scripts and dependencies |
| `AgentXWeb/public/agentxweb.config.js` | Runtime API base URL without rebuilding |
| `AgentXWeb/src/api/client.ts` | Typed API client |
| `AgentXWeb/src/ui/App.tsx` | Main React application |
| `AgentXWeb/src/ui/pages/` | Settings and customization pages |
| `AgentXWeb/src/ui/components/` | Chat, inspector, panels, code canvas, message rendering |

## `apps/desktop`

`apps/desktop` is the Tauri desktop client.

| Path | Purpose |
| --- | --- |
| `apps/desktop/package.json` | Vite, React, and Tauri commands |
| `apps/desktop/src-tauri/tauri.conf.json` | Tauri app config |
| `apps/desktop/src-tauri/src/main.rs` | Rust desktop entry point |
| `apps/desktop/src/` | Desktop React UI and API client |
