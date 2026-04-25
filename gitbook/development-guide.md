# Development Guide

## Prerequisites

Useful local development tools:

- Python 3.11+
- Node.js 20.19+ on Node 20, or Node.js 22.12+ or newer for AgentXWeb and apps/desktop builds
- npm
- Git
- Rust toolchain for Tauri desktop work
- Ollama if testing local model generation

## Python Runtime Development

From the repo root:

```bash
python -m pytest AgentX/tests apps/api/tests
```

From `AgentX`:

```bash
cd AgentX
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[developer]"
python -m pytest tests
```

On PowerShell:

```powershell
cd AgentX
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip setuptools wheel
python -m pip install -e ".[developer]"
python -m pytest tests
```

## API Development

The API imports `agentx` through the bridge, so make sure `AgentX` is importable or set `AGENTX_APP_ROOT`.

Example PowerShell session:

```powershell
$env:AGENTX_APP_ROOT = "F:\AgentX Folder"
$env:AGENTX_AUTH_ENABLED = "false"
cd apps\api
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:PYTHONPATH = "F:\AgentX Folder\AgentX;$PWD"
python -m agentx_api --host 127.0.0.1 --port 8420
```

Example bash session:

```bash
export AGENTX_APP_ROOT="$PWD"
export AGENTX_AUTH_ENABLED=false
cd apps/api
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
export PYTHONPATH="$(pwd)/../../AgentX:$(pwd)"
python -m agentx_api --host 127.0.0.1 --port 8420
```

## Web Development

AgentXWeb uses the Vite 8 toolchain and requires Node.js 20.19+ on Node 20, or Node.js 22.12+ or newer.

```bash
cd AgentXWeb
npm install
npm run dev
```

Make sure `AgentXWeb/public/agentxweb.config.js` points to the API:

```js
window.__AGENTXWEB_CONFIG__ = {
  apiBase: "http://127.0.0.1:8420",
  showInspector: undefined
};
```

Tests and checks:

```bash
npm run test
npm run typecheck
npm run build
```

## Desktop Development

The desktop frontend uses the Vite 8 toolchain and requires Node.js 20.19+ on Node 20, or Node.js 22.12+ or newer.

```bash
cd apps/desktop
npm install
npm run tauri:dev
```

For production build:

```bash
npm run tauri:build
```

## API Tests

```bash
python -m pytest apps/api/tests
```

For API-only setup from `apps/api`:

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt pytest
export PYTHONPATH="$(pwd):$(pwd)/../../AgentX"
python -m pytest tests
```

On PowerShell, set:

```powershell
$env:PYTHONPATH = "$PWD;F:\AgentX Folder\AgentX"
```

## Repository Test Areas

The existing tests cover:

- Bootstrap install lifecycle.
- CLI run behavior.
- Doctor fixes.
- Runtime unification.
- Service management.
- Plugin manager.
- Skill import.
- Job runner.
- Health checks.
- Ollama endpoint behavior.
- API auth and auth isolation.
- Release packaging.
- Frontend chat send, layout persistence, code canvas, customization page.

## Grounded Demo Flows

`AgentX/docs/reliability-demos.md` documents practical flows:

- Create, read, edit, and delete a file.
- Inspect the repo to find implementation locations.
- Explain runtime behavior from inspected code.
- Fail safely when context is ambiguous.

These are useful smoke tests for real agent behavior.
