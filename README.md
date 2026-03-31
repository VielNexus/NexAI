# NexAI

NexAI is a local-first, supervised AI assistant platform designed for inspectable, policy-aware operation on user-controlled infrastructure. It combines a CLI agent runtime, FastAPI backend, web UI, installable extension model, and an evolving autonomous job/plugin/skill architecture while keeping auditability and approval gates central to the design.

## Overview

NexAI is built to run as a practical local system rather than a cloud-only assistant. The project separates immutable app files from mutable runtime state, supports supervised tool execution, and is being refactored toward durable Linux/WSL installs with explicit lifecycle management.

## Key Features

- Local-first runtime with explicit `app_root`, `runtime_root`, and `working_dir` separation
- Supervised agent execution with audit logging, policy enforcement, and approval-gated risky actions
- CLI, API, and web UI surfaces
- Autonomous job runner with bounded retries, reflection, and learned hints
- Manifest-driven tool plugins and instruction-based skills
- Built-in versus user-installed extension separation
- Install/runtime tooling for product-style lifecycle management

## Repository Layout

- `SolVersion2/`: core agent runtime, CLI, install/runtime system, plugins, skills, tests
- `apps/api/`: FastAPI backend bridge and service surface
- `SolWeb/`: React/Vite web UI
- `apps/desktop/`: desktop client work

## Ubuntu 24 Install

Fresh Ubuntu 24 installs are intended to start with:

```bash
curl -fsSL https://raw.githubusercontent.com/VielNexus/NexAI/main/install.sh | bash
```

That root installer:

- installs required Ubuntu packages when they are missing
- clones NexAI into `~/.local/share/nexai/app`
- builds `SolWeb/dist`
- bootstraps the NexAI CLI into `~/.local/bin/nexai`
- provisions the managed runtime under `~/.local/share/sol`

The installer uses the existing product-style runtime model:

- app bundle: `~/.local/share/nexai/app`
- bootstrap launcher: `~/.local/bin/nexai`
- managed runtime: `~/.local/share/sol`

After install:

```bash
~/.local/bin/nexai start
~/.local/bin/nexai status
```

Then open:

```text
http://127.0.0.1:5173
```

Notes:

- The default model provider is Ollama at `http://127.0.0.1:11434`
- If `~/.local/bin` is not on your `PATH`, add:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Repo-local installs are still supported from a checked-out bundle:

```bash
./install-sol.sh
```

## Platform Support

- Current focus: Linux and WSL
- Product-style install/runtime support is being hardened for Linux/WSL first
- Windows-native support is planned later and is not the current target for install/service behavior

## Status

Sol is under active architecture work. The current direction is production-minded, but the platform is still evolving in areas such as install flow, extension lifecycle, autonomous job execution, and release packaging.

## Development

Python components live primarily under `SolVersion2/` and `apps/api/`. The web UI lives under `SolWeb/`. Local runtime data, dependency folders, caches, and logs are intentionally excluded from version control.

## License

Apache-2.0
