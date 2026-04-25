First thing before using this system. I am in no way, shape or form how you use AgentX! This system is being ran on your local hardware with/without models ran by other providers other than me. I have NO control over this system once installed on your system therefor you are the sole responsible person on how it is used, and how it reacts! I have no say of ANYTHING once you download/install AgentX!
# AgentX

AgentX is a local-first, supervised AI assistant platform designed for inspectable, policy-aware operation on user-controlled infrastructure. It combines a CLI agent runtime, FastAPI backend, web UI, installable extension model, and an evolving autonomous job/plugin/skill architecture while keeping auditability and approval gates central to the design.

## Overview

AgentX is built to run as a practical local system rather than a cloud-only assistant. The project separates immutable app files from mutable runtime state, supports supervised tool execution, and is being refactored toward durable Linux/WSL installs with explicit lifecycle management.

## Key Features

- Local-first runtime with explicit `app_root`, `runtime_root`, and `working_dir` separation
- Supervised agent execution with audit logging, policy enforcement, and approval-gated risky actions
- CLI, API, and web UI surfaces
- Autonomous job runner with bounded retries, reflection, and learned hints
- Manifest-driven tool plugins and instruction-based skills
- Built-in versus user-installed extension separation
- Install/runtime tooling for product-style lifecycle management

## Repository Layout

- `AgentX/`: core agent runtime, CLI, install/runtime system, plugins, skills, tests
- `apps/api/`: FastAPI backend bridge and service surface
- `AgentXWeb/`: React/Vite web UI
- `apps/desktop/`: desktop client work

## Ubuntu 24 Install

Fresh Ubuntu 24 installs are intended to start with:

```bash
curl -fsSL https://raw.githubusercontent.com/VielAgentX/AgentX/main/install.sh | bash
```

That root installer:

- installs required Ubuntu packages when they are missing
- clones AgentX into `~/.local/share/agentx/app`
- builds `AgentXWeb/dist`
- bootstraps the AgentX CLI into `~/.local/bin/agentx`
- provisions the managed runtime under `~/.local/share/agentx`

The installer uses the existing product-style runtime model:

- app bundle: `~/.local/share/agentx/app`
- bootstrap launcher: `~/.local/bin/agentx`
- managed runtime: `~/.local/share/agentx`

After install:

```bash
agentx start
agentx status
```

Lifecycle commands:

```bash
agentx start
agentx stop
agentx restart
agentx status
agentx uninstall
```

Then open:

```text
http://127.0.0.1:5173
```

Notes:

- Fresh local installs default to local-first mode with login disabled.
- The default model provider is Ollama at `http://127.0.0.1:11434`
- The installer updates `PATH` for the current install session and persists `~/.local/bin` into `.bashrc` or `.zshrc` when needed.

Repo-local installs are still supported from a checked-out bundle:

```bash
./install-agentx.sh
```

For repo-local installs, the same lifecycle commands are available through `agentx` after setup:

```bash
agentx start
agentx stop
agentx restart
agentx status
agentx uninstall
```

## Auth Mode

Fresh local/demo installs now default to no-login local mode.

- Persistent install/runtime flag: `auth.enabled`
- Managed installs store it in `~/.config/agentx/install.json` and mirror it into `~/.local/share/agentx/config/agentx.toml`
- Direct API override: `AGENTX_AUTH_ENABLED=false|true`

When `auth.enabled` is `false`, the backend accepts the local app flow without login and AgentXWeb does not show the sign-in gate.

To enable auth later:

1. Set `auth.enabled` to `true` in `~/.config/agentx/install.json`.
2. Restart AgentX so it rewrites runtime config and restarts the API with auth enabled.
3. Set credentials with `AGENTX_AUTH_USER` plus `AGENTX_AUTH_PASSWORD` or `AGENTX_AUTH_PASSWORD_SHA256`.

If you are running the API directly outside the managed installer flow, set `AGENTX_AUTH_ENABLED=true` before startup.

## Platform Support

- Current focus: Linux and WSL
- Product-style install/runtime support is being hardened for Linux/WSL first
- Windows-native support is planned later and is not the current target for install/service behavior

## Status

AgentX is under active architecture work. The current direction is production-minded, but the platform is still evolving in areas such as install flow, extension lifecycle, autonomous job execution, and release packaging.

## Development

Python components live primarily under `AgentX/` and `apps/api/`. The web UI lives under `AgentXWeb/`. Local runtime data, dependency folders, caches, and logs are intentionally excluded from version control.

Verified grounded demo flows are documented in `AgentX/docs/reliability-demos.md`.

## Clean Source Repository Guide

The repository should contain source code, manifests, lockfiles, installer scripts, tests, documentation, and checked-in examples only. Generated output and local runtime state should stay out of git.

Canonical source areas:

- `AgentX/`: Python runtime package, CLI, tests, default config, built-in plugins, built-in skills
- `apps/api/`: FastAPI backend service and tests
- `AgentXWeb/`: React/Vite web UI source and npm lockfile
- `apps/desktop/`: Tauri desktop client source, npm lockfile, Rust manifest, and Cargo lockfile
- `scripts/`: release and maintenance scripts
- `install.sh`, `install-agentx.sh`, `start-agentx.ps1`: installer and launcher helpers

Do not commit:

- `node_modules/`, `dist/`, `build/`, Rust `target/`
- Python caches, pytest caches, virtual environments, egg-info
- runtime `data/`, `threads/`, logs, audit logs, memory files, SQLite databases, uploaded files
- `.env` files, tokens, private keys, certificates, or credentials

If a folder is named `data` but contains source documentation, preserve it. For example, `AgentX/Server/data/features/` currently contains feature documentation and is intentionally tracked.

## Prerequisites

Recommended development tools:

- Python 3.11 or newer
- Node.js 20.19+ on Node 20, or Node.js 22.12+ or newer for AgentXWeb and apps/desktop builds
- npm
- Git
- Rust and Cargo for desktop/Tauri checks
- Ollama if testing the local model provider

## Backend And Runtime Setup

Install the Python runtime in editable mode:

```bash
cd AgentX
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[developer]"
```

PowerShell:

```powershell
cd AgentX
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[developer]"
```

Run Python tests from the repository root:

```bash
python -m pytest AgentX/tests apps/api/tests
```

Or run the AgentX tests from inside the package directory:

```bash
cd AgentX
python -m pytest tests
```

Run the API directly for development:

```bash
cd apps/api
python -m pip install -r requirements.txt
PYTHONPATH="../../AgentX:." python -m agentx_api --host 127.0.0.1 --port 8420
```

## Web UI Setup

AgentXWeb uses the Vite 8 toolchain and requires Node.js 20.19+ on Node 20, or Node.js 22.12+ or newer.

```bash
cd AgentXWeb
npm ci
npm run typecheck
npm run test
npm run build
```

The generated `AgentXWeb/dist/` folder is build output and should not be committed.

Runtime API configuration for the web UI is in:

```text
AgentXWeb/public/agentxweb.config.js
```

For local development it should point at:

```text
http://127.0.0.1:8420
```

## Desktop Setup

The desktop frontend uses the Vite 8 toolchain and requires Node.js 20.19+ on Node 20, or Node.js 22.12+ or newer.

```bash
cd apps/desktop
npm ci
npm run build
cargo check --manifest-path src-tauri/Cargo.toml
```

For Tauri dev mode:

```bash
npm run tauri:dev
```

Generated `apps/desktop/dist/`, `apps/desktop/node_modules/`, and `apps/desktop/src-tauri/target/` are not source files.

## Environment Variables

Use `.env.example` as a safe template for local settings. Do not commit `.env` or real secrets.

Common variables:

- `AGENTX_API_HOST`, `AGENTX_API_PORT`
- `AGENTX_AUTH_ENABLED`, `AGENTX_AUTH_USER`, `AGENTX_AUTH_PASSWORD`, `AGENTX_AUTH_PASSWORD_SHA256`
- `AGENTX_OPENAI_API_KEY`, `AGENTX_OPENAI_MODEL`, `AGENTX_OPENAI_BASE_URL`
- `AGENTX_OLLAMA_BASE_URL`, `AGENTX_OLLAMA_REQUEST_TIMEOUT_S`
- `AGENTX_RAG_ENABLED`, `AGENTX_RAG_ALLOWED_ROOTS`
- `AGENTX_FS_ENABLED`, `AGENTX_FS_ALLOWED_ROOTS`, `AGENTX_FS_WRITE_ENABLED`, `AGENTX_FS_DELETE_ENABLED`
- `AGENTX_WEB_ENABLED`, `AGENTX_WEB_ALLOWED_HOSTS`

`AGENTX_*` names are preferred. Existing `SOL_*` runtime variables and `NEXAI_*` installer/runtime variables are accepted as deprecated fallbacks when the matching `AGENTX_*` value is unset.

## Runtime Data Locations

The source tree should remain rebuildable without local runtime state.

Recommended runtime locations:

- Linux config: `~/.config/agentx/`
- Linux data: `~/.local/share/agentx/`
- Linux logs: `~/.local/state/agentx/logs/`
- Windows config/data/logs: user AppData locations
- macOS config/data/logs: user Library locations

The current installer already separates app files from managed runtime files for Linux/WSL installs:

- app bundle: `~/.local/share/agentx/app`
- launcher: `~/.local/bin/agentx`
- managed runtime: `~/.local/share/agentx`

Deprecated `nexai` and `sol` command aliases may exist for compatibility, but new docs and scripts use `agentx`.

## Local Cleanup And Reset

To return a checkout to source-only form, remove generated files and reinstall dependencies from lockfiles:

```bash
git status --short
```

Safe generated folders to delete locally include:

- `**/node_modules/`
- `**/dist/`
- `**/build/`
- `**/__pycache__/`
- `**/.pytest_cache/`
- `**/.venv/`
- `AgentX/data/`
- `AgentX/logs/`
- `apps/api/agentx_api/data/`

After cleanup, rebuild from source using the setup commands above.

## License

Apache-2.0
