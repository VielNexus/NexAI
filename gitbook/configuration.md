# Configuration

AgentX has two major config layers:

- API config from environment variables in `apps/api/agentx_api/config.py`.
- Runtime config from TOML in `AgentX/config/agentx.toml` or the generated install runtime config.

## Runtime TOML

Default repo config:

```text
AgentX/config/agentx.toml
```

Generated installs write a runtime config under the managed runtime root and point the launcher/API at it.

Major sections:

| Section | Purpose |
| --- | --- |
| `[agent]` | Agent mode, max steps, auto-tool behavior |
| `[audit]` | JSONL audit log path |
| `[memory]` | SQLite FTS memory backend and event log |
| `[paths]` | Data, logs, UI project roots |
| `[fs]` | Filesystem allowed roots, denied drives, denied substrings, size limits |
| `[exec]` | Command execution allowlist and timeout |
| `[web]` | Web access defaults |
| `[web.policy]` | Managed fetch/crawl allowlist/denylist |
| `[web.search]` | Search providers and result limits |
| `[rag]` | Retrieval settings |
| `[voice]` | Voice stub settings |
| `[vision]` | Vision stub settings |
| `[llm]` | Provider selection |
| `[llm.openai]` | OpenAI-compatible settings |
| `[llm.ollama]` | Ollama settings |

## Important Runtime Defaults

| Setting | Default Meaning |
| --- | --- |
| `agent.mode = "supervised"` | Human-supervised tool execution |
| `agent.refuse_unattended = true` | Fail closed for unattended mode |
| `fs.allowed_roots = ["D:/", "E:/", "F:/"]` | Repo default allows non-C Windows drives |
| `fs.deny_drive_letters = ["C"]` | Blocks C drive |
| `exec.allowed_commands = ["python", "git", "npm", "node"]` | Command allowlist |
| `web.policy.allow_all_hosts = false` | Fetch/crawl is allowlist-based |
| `llm.provider = "ollama"` | Runtime CLI provider default |
| `llm.ollama.model = "llama3.2"` | Default Ollama model |

## API Environment Variables

`AGENTX_*` names are preferred. Existing `SOL_*` runtime variables and `NEXAI_*` variables are deprecated fallbacks when the matching `AGENTX_*` variable is unset.

Core API:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_API_HOST` | `127.0.0.1` | API bind host |
| `AGENTX_API_PORT` | `8420` | API port |
| `AGENTX_API_DATA_DIR` | API package `data` dir | Settings, threads, RAG DB |

Auth:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_AUTH_ENABLED` | `false` | Enable bearer auth |
| `AGENTX_AUTH_SESSION_TTL_S` | `604800` | Session lifetime, min 300 seconds |
| `AGENTX_AUTH_USERS_JSON` | unset | JSON map of username to SHA256 digest |
| `AGENTX_AUTH_USER` | `agentx` | Single default auth user |
| `AGENTX_AUTH_PASSWORD` | unset | Plain password converted to SHA256 at startup |
| `AGENTX_AUTH_PASSWORD_SHA256` | legacy digest | Password digest |

OpenAI:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_OPENAI_API_KEY` | unset | Enables OpenAI provider |
| `AGENTX_OPENAI_MODEL` | `gpt-4o-mini` | Default OpenAI model |
| `AGENTX_OPENAI_BASE_URL` | `https://api.openai.com` | OpenAI-compatible base URL |
| `AGENTX_OPENAI_TIMEOUT_S` | `20` | HTTP timeout |
| `AGENTX_OPENAI_TOOL_MAX_ITERS` | `4` | Tool loop limit |

Ollama:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_OLLAMA_BASE_URL` | `http://127.0.0.1:11434` | Ollama endpoint |
| `AGENTX_OLLAMA_TIMEOUT_S` | `5` | Model discovery timeout |
| `AGENTX_OLLAMA_REQUEST_TIMEOUT_S` | `60` | Generation timeout |
| `AGENTX_OLLAMA_TOOLS_ENABLED` | `false` | Best-effort text-protocol tool use |
| `AGENTX_OLLAMA_TOOL_MAX_ITERS` | `4` | Ollama tool loop limit |

RAG:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_RAG_ENABLED` | `true` | Enable API RAG |
| `AGENTX_RAG_TOP_K` | `5` | Query hits |
| `AGENTX_RAG_CHUNK_CHARS` | `1200` | Chunk size |
| `AGENTX_RAG_CHUNK_OVERLAP` | `200` | Chunk overlap |
| `AGENTX_RAG_ALLOWED_ROOTS` | API data dir | Semicolon-separated gather roots |
| `AGENTX_RAG_INGEST_THREADS` | `true` | Ingest thread context |
| `AGENTX_RAG_TOOL_MAX_CHARS` | `8000` | Model-driven RAG write limit |

Filesystem API:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_FS_ENABLED` | `false` | Enable `/v1/fs/*` |
| `AGENTX_FS_ALLOW_ALL` | `false` | Allow all paths |
| `AGENTX_FS_ALLOWED_ROOTS` | API data dir | Semicolon-separated roots |
| `AGENTX_FS_WRITE_ENABLED` | `false` | Enable writes |
| `AGENTX_FS_DELETE_ENABLED` | `false` | Enable deletes |
| `AGENTX_FS_WRITE_DENY_DRIVES` | `C` | Deny writes on drives |
| `AGENTX_FS_MAX_READ_BYTES` | `200000` | Read size limit |
| `AGENTX_FS_MAX_WRITE_BYTES` | `200000` | Write size limit |

Web API:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AGENTX_WEB_ENABLED` | `false` | Enable web tools in API fallback paths |
| `AGENTX_WEB_ALLOW_ALL` | `false` | Allow all hosts |
| `AGENTX_WEB_ALLOWED_HOSTS` | `duckduckgo.com;wikipedia.org` equivalent defaults | Host allowlist |
| `AGENTX_WEB_BLOCK_PRIVATE` | `true` | Block private networks |
| `AGENTX_WEB_TIMEOUT_S` | `10` | Fetch timeout |
| `AGENTX_WEB_MAX_BYTES` | `400000` | Fetch size limit |
| `AGENTX_WEB_USER_AGENT` | `AgentXWebAccess/0.1` | User agent |
| `AGENTX_WEB_MAX_REDIRECTS` | `5` | Redirect limit |
| `AGENTX_WEB_MAX_SEARCH_RESULTS` | `5` | Search result limit |

## AgentX Bridge Environment

| Variable | Purpose |
| --- | --- |
| `AGENTX_APP_ROOT` | Override app root used by API bridge |
| `AGENTX_CONFIG_PATH` | Override runtime TOML path used by API bridge |

## Web UI Config

Runtime UI config is served from:

```text
AgentXWeb/public/agentxweb.config.js
```

It controls `apiBase` and optional inspector visibility without rebuilding the site.
