# AgentX V13 — Model Profile Visibility and Routing Warnings

V13 polishes the model routing features AgentX already has instead of replacing them.

## Existing Foundation

AgentX already reports:

- `default`, `fast`, and `heavy` Ollama endpoints
- endpoint reachability
- endpoint model lists
- GPU pin metadata
- benchmark and fast/heavy comparison actions
- model runtime status

## V13 Adds

- Endpoint profile cards on the Models page.
- Human-readable endpoint purpose text.
- GPU pin visibility.
- Model count visibility per endpoint.
- Routing warnings when Fast and Heavy use the same base URL.
- Warnings for unreachable endpoints.
- Warnings for endpoints with no models.
- Health page warnings for duplicate/offline Ollama endpoints.

## Why This Matters

V13 makes the existing multi-endpoint routing easier to understand at a glance.
It avoids adding a new routing engine while making the current routing behavior safer and clearer.

## Validation

```bash
python3 -m compileall AgentX/agentx apps/api/agentx_api apps/api/tests
./scripts/smoke-test-v10.sh

cd AgentXWeb
npm run typecheck
npm test
npm run build
```
