# Installable Runtime

This feature moves AgentX toward a product-style Linux/WSL install instead of a repo-bound dev checkout.

## Goals

- installable under any app directory
- mutable runtime data stored under a chosen runtime root
- no runtime dependence on repo-relative `config/agentx.toml`
- CLI lifecycle management
- standard profile can serve built AgentXWeb assets without Node on the target machine

## CLI

- `./install-agentx.sh`
- `agentx setup`
- `agentx start`
- `agentx stop`
- `agentx restart`
- `agentx status`
- `agentx doctor`
- `agentx paths`
- `agentx config show`

## Runtime Layout

Generated under the chosen runtime root:

- `config/agentx.toml`
- `extensions/plugins/`
- `extensions/skills/`
- `data/`
- `memory/`
- `logs/`
- `audit/`
- `cache/`
- `tmp/`
- `run/`
- `state/plugins/`
- `state/skills/`
- `state/web/agentxweb.config.js`

## Service Mode

Linux/WSL support is currently scoped to user services.

- `systemd --user` units are generated when `service_mode=systemd-user`
- native Windows services are intentionally not implemented yet

## Standard Install

Standard installs expect built web assets in `AgentXWeb/dist`. If those assets ship with the product bundle, the target machine does not need Node or Vite just to run AgentX.

## One-Command Bootstrap

From a repo or release bundle root:

```bash
./install-agentx.sh
```

The bootstrap installer:

- checks for `python3`, `python3-venv`, and `curl`
- creates a lightweight bootstrap virtual environment automatically
- installs the AgentX CLI into that bootstrap environment
- writes a stable launcher to `~/.local/bin/agentx`
- keeps `~/.local/bin/agentx` as a compatibility alias
- runs `agentx setup` so the real managed runtime can be provisioned under the selected runtime root

This keeps the design split intact:

- bootstrap environment: installer + CLI entrypoint
- managed runtime: created by `agentx setup` under `runtime_root/venv`

Example transcript:

```text
$ ./install-agentx.sh
AgentX
Local-first AI assistant platform

Bootstrap install
  App bundle:      /home/agentx/src/agentx
  Platform:        wsl
  Bootstrap env:   /home/agentx/.local/share/agentx/bootstrap/venv
  Launcher:        /home/agentx/.local/bin/agentx

Creating bootstrap virtual environment...
Installing AgentX CLI into bootstrap environment...

Bootstrap install complete.
  Bootstrap env:      /home/agentx/.local/share/agentx/bootstrap/venv
  User launcher:      /home/agentx/.local/bin/agentx
  Compatibility alias: /home/agentx/.local/bin/agentx
  CLI fallback:       /home/agentx/.local/share/agentx/bootstrap/venv/bin/python -m agentx
  Default runtime:    /home/agentx/.local/share/agentx
  Install log:        /home/agentx/.local/share/agentx/bootstrap/install.log

Launching AgentX setup with the bootstrap environment...
  Command: /home/agentx/.local/share/agentx/bootstrap/venv/bin/python -m agentx setup
```

After bootstrap setup:

- `agentx start`
- `agentx status`
- open the web UI at `http://127.0.0.1:5173`
