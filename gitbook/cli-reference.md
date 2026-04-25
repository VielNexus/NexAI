# CLI Reference

The Python package exposes two console scripts:

```text
agentx
agentx
```

`agentx` is the supported command. `agentx` exists as a compatibility alias during migration.

## Global Options

```bash
agentx --config config/agentx.toml <command>
agentx --install-config ~/.config/agentx/install.json <command>
```

| Option | Meaning |
| --- | --- |
| `--config` | Runtime TOML config path for direct runtime commands |
| `--install-config` | Product install metadata JSON path |

## Lifecycle Commands

```bash
agentx setup
agentx start
agentx stop
agentx restart
agentx status
agentx uninstall
agentx doctor
agentx health
agentx paths
```

## Service Commands

```bash
agentx service install
agentx service uninstall
agentx service enable
agentx service disable
agentx service status
```

These manage systemd-user service files when the install uses systemd user services.

## Runtime And Config Inspection

```bash
agentx runtime inspect
agentx config show
agentx logs api --tail 100
agentx logs web --tail 100
```

## Chat And Task Execution

```bash
agentx run "your task"
agentx run --file task.txt
cat task.txt | agentx run
agentx run
```

`agentx run` sends the prompt to `/v1/chat` on the local API when an installed runtime is present.

## Tool Execution

Run a tool through the audited agent loop:

```bash
agentx tool fs.list --reason "Inspect workspace" --json "{\"path\":\"F:/AgentX Folder\"}"
```

The CLI requires a non-empty `--reason` for tool calls. This is intentional because tool activity is audited.

## RAG Ingest

```bash
agentx ingest --path ./docs --reason "Index project docs" --recursive --max_files 200
```

The ingest command goes through the agent loop and stores content in the memory/RAG backend according to policy.

## Memory Commands

```bash
agentx memory stats --reason "Check memory size"
agentx memory prune --older-than-days 30 --dry-run --reason "Review old memory cleanup"
agentx memory prune --older-than-days 30 --reason "Clean old memory"
```

Non-dry-run pruning is destructive and is blocked by unsafe-mode policy unless explicitly enabled for the active thread/context.

## Selfcheck

```bash
agentx selfcheck --mode quick
agentx selfcheck --mode full --json
agentx selfcheck --mode full --fix
```

## Jobs

```bash
agentx job create --goal "Inspect repository health" --max-steps 10
agentx job run <job_id>
agentx job show <job_id>
agentx job cancel <job_id> --reason "No longer needed"
agentx job approve <job_id>
agentx job approve <job_id> --deny --note "Plan was too risky"
```

Jobs are supervised. High-risk or destructive plans can block and require approval before continuing.

## Plugins

```bash
agentx plugins list
agentx plugins enable <plugin_id>
agentx plugins disable <plugin_id>
```

## Skills

```bash
agentx skills list
agentx skills import-pack ./path/to/skill-pack
agentx skills import-pack ./path/to/skill-pack --skill-id custom_id
```

Skill packs must contain `SKILL.md`.
