# Troubleshooting

## `agentx` Command Not Found

Cause: `~/.local/bin` is not on `PATH`.

Fix:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Then add the same line to `~/.bashrc` or `~/.zshrc` if the installer did not already do it.

## API Is Not Running

Symptoms:

- CLI says `AgentX API is not running. Try: agentx status or agentx start`.
- Web UI cannot load status.

Fix:

```bash
agentx status
agentx start
agentx logs api --tail 100
agentx doctor
```

## Web UI Does Not Connect

Check `AgentXWeb/public/agentxweb.config.js`:

```js
window.__AGENTXWEB_CONFIG__ = {
  apiBase: "http://127.0.0.1:8420"
};
```

Then verify API status:

```bash
curl http://127.0.0.1:8420/v1/status
```

## Ollama Is Unreachable

Symptoms:

- Provider endpoint status is `unreachable`.
- Chat status says the configured Ollama endpoint could not be reached.

Fix:

```bash
ollama serve
ollama list
ollama pull llama3.2
```

Confirm the configured URL:

```text
http://127.0.0.1:11434
```

## Selected Ollama Model Is Missing

Symptoms:

- Provider model status is `missing`.
- Status says the selected model is not available.

Fix:

```bash
ollama pull <model-name>
```

Then refresh AgentXWeb status or call:

```bash
curl "http://127.0.0.1:8420/v1/status?refresh=1"
```

## OpenAI Provider Fails

If OpenAI is selected, `AGENTX_OPENAI_API_KEY` must be set:

```bash
export AGENTX_OPENAI_API_KEY="..."
```

Optional:

```bash
export AGENTX_OPENAI_MODEL="gpt-4o-mini"
export AGENTX_OPENAI_BASE_URL="https://api.openai.com"
```

Restart the API after changing environment variables.

## Auth Login Is Not Available

If `/v1/auth/login` returns HTTP 409, auth is disabled. This is the default local install behavior.

Enable auth:

```bash
export AGENTX_AUTH_ENABLED=true
export AGENTX_AUTH_USER=agentx
export AGENTX_AUTH_PASSWORD="choose-a-password"
```

For managed installs, update `auth.enabled` in install metadata and restart AgentX.

## File Access Is Disabled

API filesystem endpoints are disabled by default.

Enable read access:

```bash
export AGENTX_FS_ENABLED=true
export AGENTX_FS_ALLOWED_ROOTS="/safe/path"
```

Enable writes only when needed:

```bash
export AGENTX_FS_WRITE_ENABLED=true
```

Enable deletes only when needed:

```bash
export AGENTX_FS_DELETE_ENABLED=true
```

Destructive operations still require unsafe mode for the relevant thread.

## Destructive Action Blocked

Symptoms:

```text
Destructive action blocked. Enable UNSAFE mode for this thread.
```

Fix:

- Confirm the target path and operation.
- Enable unsafe mode for that thread with a reason.
- Run the operation.
- Disable unsafe mode afterward.

## RAG Gather Path Rejected

Symptoms:

```text
Path is outside AGENTX_RAG_ALLOWED_ROOTS.
```

Fix:

```bash
export AGENTX_RAG_ALLOWED_ROOTS="/path/one;/path/two"
```

Restart the API.

## AgentX Bridge Fails

Symptoms:

- `/v1/capabilities` returns 503.
- Chat returns `AgentX agent error`.

Checks:

```bash
agentx runtime inspect
agentx doctor
```

For direct API development, set:

```bash
export AGENTX_APP_ROOT="/path/to/repo"
export AGENTX_CONFIG_PATH="/path/to/repo/AgentX/config/agentx.toml"
```

Also ensure `AgentX` is importable through `PYTHONPATH` or an editable install.

## Release Packaging Fails

Most common cause: `AgentXWeb/dist/index.html` does not exist.

Fix:

```bash
cd AgentXWeb
npm install
npm run build
cd ..
python scripts/package_release.py
```


## WSL web UI cannot be reached from Windows

On WSL installs, AgentX should bind the API and web UI to `0.0.0.0` by default so Windows can reach the WSL service through the WSL IP.

For older installs, re-run setup with explicit WSL-friendly bind hosts:

```bash
agentx stop
agentx setup --non-interactive --profile standard --app-root ~/.local/share/agentx/app --runtime-root ~/.local/share/agentx --working-dir ~ --model-provider ollama --ollama-base-url http://127.0.0.1:11434 --api-host 0.0.0.0 --api-port 8420 --web-host 0.0.0.0 --web-port 5173 --web-enabled true --service-mode none
agentx start
```

Then get the WSL IP:

```bash
hostname -I | awk '{print $1}'
```

Open `http://<wsl-ip>:5173` from Windows.
