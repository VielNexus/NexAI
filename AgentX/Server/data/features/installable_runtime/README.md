# AgentX Installable Runtime

This refactor makes AgentX behave like an installable Linux/WSL product instead of assuming a repo checkout is both the app root and the mutable runtime root.

## Profiles

- `cli`: interactive CLI only, no long-running API or web process
- `standard`: CLI + API + static web UI
- `server`: CLI + API, web disabled by default
- `developer`: CLI + API + web, plus slightly broader local tool roots for development

## Commands

- `./install-agentx.sh`
- `agentx setup`
- `agentx start`
- `agentx stop`
- `agentx restart`
- `agentx status`
- `agentx doctor`
- `agentx paths`
- `agentx config show`

## Path Model

Immutable app files:

- `app_root/AgentX`
- `app_root/apps/api`
- `app_root/AgentXWeb`

Mutable runtime files:

- `runtime_root/config/agentx.toml`
- `runtime_root/extensions/plugins`
- `runtime_root/extensions/skills`
- `runtime_root/data/`
- `runtime_root/memory/`
- `runtime_root/logs/`
- `runtime_root/audit/`
- `runtime_root/cache/`
- `runtime_root/tmp/`
- `runtime_root/run/`
- `runtime_root/state/plugins/`
- `runtime_root/state/skills/`
- `runtime_root/state/web/agentxweb.config.js`

Separate working directory:

- `working_dir/`

Bootstrap CLI files:

- `~/.local/share/agentx/bootstrap/venv`
- `~/.local/bin/agentx`
- `~/.local/bin/agentx` (compatibility alias)

The bootstrap environment is only the installer/CLI entrypoint. AgentX still provisions a separate managed runtime under the selected `runtime_root/venv` for profiles that run the API or web UI.

Built-in extensions stay in the immutable app bundle:

- `app_root/AgentX/plugins`
- `app_root/AgentX/skills`

Runtime extensions live under the mutable runtime root:

- `runtime_root/extensions/plugins`
- `runtime_root/extensions/skills`

## Runtime Resolution Rules

1. `AGENTX_APP_ROOT` wins when set.
2. `AGENTX_RUNTIME_ROOT` wins for mutable state when set.
3. `AGENTX_CONFIG_PATH` wins for the generated runtime config when set.
4. If AgentX loads a config from `.../config/agentx.toml`, it infers that directory's parent as the runtime root.
5. If `AGENTX_APP_ROOT` is not set and AgentX loads `.../config/agentx.toml`, it also infers that parent as the local app root for relative immutable paths. This keeps dev/test installs relocatable.

## Standard Install Behavior

The standard profile serves prebuilt AgentXWeb assets from `AgentXWeb/dist`.

- End users do not need Node/Vite if the bundle already contains `dist/`
- `agentx start` writes runtime web config to `runtime_root/state/web/agentxweb.config.js`
- the web server injects that config dynamically while serving immutable frontend assets from the app bundle

## Bootstrap Flow

Repo/dev flow:

```bash
./install-agentx.sh
```

Expected future release flow:

```bash
curl -fsSL <install-url> | bash
```

Both flows are intended to bootstrap the CLI first and then hand off to `agentx setup` for managed runtime provisioning.

## Product Bundle Hygiene

The repo now includes [`.productignore`](/F:/AgentX%20Folder/.productignore) to document which dev-only artifacts should stay out of product bundles, including `.git`, local virtual environments, `node_modules`, caches, tests, and local workspace notes.

## Service Setup

Current support is Linux/WSL-first:

- `systemd-user` unit file generation is implemented
- native Windows service installation is intentionally deferred

Generated user units:

- `~/.config/systemd/user/agentx-api.service`
- `~/.config/systemd/user/agentx-web.service`

## WSL Guidance

- Prefer storing runtime data under the Linux filesystem, not the mounted Windows filesystem, for better permissions and I/O behavior
- Example runtime root: `~/.local/share/agentx`
- Example working directory: `~/agentx-work`
- If `systemd --user` is unavailable in your WSL image, use `agentx start` / `agentx stop` directly instead of service mode

## Example Generated Layout

```text
~/.local/share/agentx/
  audit/
  cache/
  config/
    agentx.toml
  data/
    api/
  extensions/
    plugins/
    skills/
  logs/
  memory/
  run/
  state/
    plugins/
    skills/
    web/
      agentxweb.config.js
  tmp/
```

## Example Generated Config Notes

- runtime paths stay under `runtime_root`
- immutable app paths are stored as absolute paths pointing at the installed app bundle
- the API and web lifecycle commands populate `AGENTX_APP_ROOT`, `AGENTX_RUNTIME_ROOT`, `AGENTX_CONFIG_PATH`, and `AGENTX_API_DATA_DIR` so subprocesses do not depend on the caller's current working directory
