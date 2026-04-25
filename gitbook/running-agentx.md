# Running AgentX

## Normal Lifecycle

Use the installed launcher:

```bash
agentx start
agentx status
agentx stop
agentx restart
```

Useful diagnostics:

```bash
agentx doctor
agentx doctor --fix
agentx health
agentx paths
agentx runtime inspect
```

Read logs:

```bash
agentx logs api --tail 100
agentx logs web --tail 100
```

Uninstall:

```bash
agentx uninstall
```

Keep the checked-out app bundle during uninstall:

```bash
agentx uninstall --keep-app-root
```

## Opening The UI

After `agentx start`, open:

```text
http://127.0.0.1:5173
```

The web UI talks to the API at:

```text
http://127.0.0.1:8420
```

The API base is controlled by `AgentXWeb/public/agentxweb.config.js` for static web builds.

## Chat Providers

AgentX supports these provider paths:

| Provider | Behavior |
| --- | --- |
| `stub` | Local echo-style fallback, no real model |
| `ollama` | Local model generation through Ollama |
| `openai` | OpenAI-compatible chat completions using `AGENTX_OPENAI_API_KEY` |

Ollama is the intended default for local-first installs. Make sure the model exists:

```bash
ollama list
ollama pull llama3.2
```

Then select the model in AgentXWeb settings or use the generated runtime config.

## CLI Chat

Send a single task:

```bash
agentx run "Summarize what this system can do."
```

Read task content from a file:

```bash
agentx run --file prompt.txt
```

Pipe input:

```bash
cat prompt.txt | agentx run
```

Start interactive mode:

```bash
agentx run
```

In interactive mode:

```text
/quit
```

## Important Runtime Separation

AgentX separates immutable application files from mutable runtime state:

| Category | Meaning |
| --- | --- |
| App root | Checked-out or installed application bundle |
| Runtime root | Managed virtualenv, config, data, logs, cache, plugins, skills, jobs |
| Working directory | Directory exposed as the user's workspace for tool operations |

This separation is central to upgrades, uninstall behavior, auditability, and release packaging.
