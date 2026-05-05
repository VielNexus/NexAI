#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_models_page() -> None:
    path = ROOT / "AgentXWeb/src/ui/pages/ModelsPage.tsx"
    text = path.read_text()

    helper_marker = """function endpointLabel(endpoint: string): string {
  if (endpoint === "default") return "Default";
  if (endpoint === "fast") return "Fast";
  if (endpoint === "heavy") return "Heavy";
  if (endpoint === "cloud") return "Cloud";
  return endpoint;
}
"""

    helper_add = helper_marker + """
function endpointPurpose(endpoint: string): string {
  if (endpoint === "default") return "Primary fallback route";
  if (endpoint === "fast") return "Low-latency draft/chat route";
  if (endpoint === "heavy") return "Reasoning, review, and repair route";
  if (endpoint === "cloud") return "Remote provider route";
  return "Custom route";
}

function normalizeBaseUrl(value: string | null | undefined): string {
  return String(value || "").trim().replace(/\\/$/, "");
}
"""

    if "function endpointPurpose(endpoint: string): string" not in text:
        text = text.replace(helper_marker, helper_add)

    summary_marker = """  const endpointNames = Array.from(new Set(cards.map((card) => card.endpoint))).sort();
  const loadedRuntimeModels = useMemo(() => new Set((runtimePs?.models ?? []).map((model) => modelRuntimeName(model))), [runtimePs]);
"""

    summary_add = summary_marker + """
  const endpointProfiles = useMemo(() => {
    const endpoints = props.status.ollama_endpoints ?? {};
    return Object.entries(endpoints).map(([endpoint, info]) => ({
      endpoint,
      label: endpointLabel(endpoint),
      purpose: endpointPurpose(endpoint),
      baseUrl: normalizeBaseUrl(info.base_url || props.status.ollama_base_url || ""),
      reachable: typeof info.reachable === "boolean" ? info.reachable : null,
      gpuPin: info.gpu_pin ?? null,
      modelCount: (info.models ?? []).length,
      error: info.error || info.error_type || null,
    })).sort((a, b) => {
      const order: Record<string, number> = { default: 0, fast: 1, heavy: 2 };
      return (order[a.endpoint] ?? 9) - (order[b.endpoint] ?? 9) || a.endpoint.localeCompare(b.endpoint);
    });
  }, [props.status.ollama_base_url, props.status.ollama_endpoints]);

  const endpointWarnings = useMemo(() => {
    const warnings: string[] = [];
    const byName = Object.fromEntries(endpointProfiles.map((profile) => [profile.endpoint, profile]));
    const fastUrl = byName.fast?.baseUrl;
    const heavyUrl = byName.heavy?.baseUrl;
    if (fastUrl && heavyUrl && fastUrl === heavyUrl) {
      warnings.push("Fast and Heavy endpoints are using the same base URL. Use separate Ollama ports if you want true route separation.");
    }
    for (const profile of endpointProfiles) {
      if (profile.reachable === false) warnings.push(`${profile.label} endpoint is unreachable.`);
      if (profile.reachable !== false && profile.modelCount === 0) warnings.push(`${profile.label} endpoint reports zero models.`);
      if ((profile.endpoint === "fast" || profile.endpoint === "heavy") && !profile.gpuPin) {
        warnings.push(`${profile.label} endpoint has no GPU pin metadata.`);
      }
    }
    return warnings;
  }, [endpointProfiles]);
"""

    if "const endpointProfiles = useMemo(() =>" not in text:
        text = text.replace(summary_marker, summary_add)

    insert_marker = """      {props.status.models_error ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">{props.status.models_error}</div>
      ) : null}

      <div className="grid min-h-0 gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
"""

    profile_block = """      {props.status.models_error ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">{props.status.models_error}</div>
      ) : null}

      <div className="grid gap-3 xl:grid-cols-3">
        {endpointProfiles.map((profile) => (
          <Panel key={profile.endpoint} className="p-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <div className={tokens.smallLabel}>{profile.label} Profile</div>
                <div className="mt-1 text-sm font-semibold text-slate-100">{profile.purpose}</div>
              </div>
              <span className={profile.reachable === false ? "agentx-model-status agentx-model-status--bad" : "agentx-model-status agentx-model-status--ok"}>
                {profile.reachable === false ? "offline" : "online"}
              </span>
            </div>
            <div className="mt-3 grid gap-1 text-xs text-slate-300">
              <div>Base: <strong className="break-all">{profile.baseUrl || "unknown"}</strong></div>
              <div>GPU: <strong>{profile.gpuPin ? `GPU ${profile.gpuPin}` : "not pinned"}</strong></div>
              <div>Models: <strong>{profile.modelCount}</strong></div>
              {profile.error ? <div className="text-rose-200">Error: {String(profile.error)}</div> : null}
            </div>
          </Panel>
        ))}
      </div>

      {endpointWarnings.length ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 p-3 text-sm text-amber-100">
          <div className="mb-1 font-semibold">Routing warnings</div>
          <ul className="list-disc space-y-1 pl-5">
            {endpointWarnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
        </div>
      ) : null}

      <div className="grid min-h-0 gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
"""

    if "Routing warnings" not in text:
        text = text.replace(insert_marker, profile_block)

    path.write_text(text)


def patch_health_page() -> None:
    path = ROOT / "AgentXWeb/src/ui/pages/HealthPage.tsx"
    text = path.read_text()

    helper_marker = """function formatLatency(value: number | null | undefined): string {
  if (!Number.isFinite(Number(value))) return "-";
  return `${Number(value).toFixed(1)} ms`;
}
"""

    helper_add = helper_marker + """
function normalizedHealthUrl(check?: HealthCheckStatus | null): string {
  return String(check?.url || "").trim().replace(/\\/$/, "");
}

function buildOllamaProfileWarnings(data: FullHealthResponse | null): string[] {
  if (!data) return [];
  const warnings: string[] = [];
  const fastUrl = normalizedHealthUrl(data.ollama.fast);
  const heavyUrl = normalizedHealthUrl(data.ollama.heavy);
  if (fastUrl && heavyUrl && fastUrl === heavyUrl) {
    warnings.push("Fast and Heavy Ollama endpoints use the same URL. Configure separate ports for true fast/heavy routing.");
  }
  for (const [label, check] of Object.entries(data.ollama)) {
    if (!check) continue;
    if (!check.ok) warnings.push(`${label} Ollama endpoint is offline.`);
  }
  return warnings;
}
"""

    if "function buildOllamaProfileWarnings" not in text:
        text = text.replace(helper_marker, helper_add)

    warnings_marker = """  const warnings = useMemo(() => health?.diagnostics?.warnings || [], [health]);
  const errors = useMemo(() => health?.diagnostics?.errors || [], [health]);
"""

    warnings_add = """  const warnings = useMemo(() => health?.diagnostics?.warnings || [], [health]);
  const endpointWarnings = useMemo(() => buildOllamaProfileWarnings(health), [health]);
  const allWarnings = useMemo(() => [...endpointWarnings, ...warnings], [endpointWarnings, warnings]);
  const errors = useMemo(() => health?.diagnostics?.errors || [], [health]);
"""

    if "const endpointWarnings = useMemo(() => buildOllamaProfileWarnings(health)" not in text:
        text = text.replace(warnings_marker, warnings_add)

    summary_marker = """    `validation: ${data.validation.available ? "available" : "unavailable"}`,
    `warnings: ${warnings.length}`,
    `errors: ${errors.length}`,
"""

    summary_add = """    `validation: ${data.validation.available ? "available" : "unavailable"}`,
    `endpoint warnings: ${buildOllamaProfileWarnings(data).length}`,
    `warnings: ${warnings.length}`,
    `errors: ${errors.length}`,
"""

    if "`endpoint warnings:" not in text:
        text = text.replace(summary_marker, summary_add)

    render_marker = """                {warnings.length ? (
                  <ul className="space-y-2 text-sm text-amber-100">
                    {warnings.map((item) => (
                      <li key={item} className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-2">{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No warnings.</p>
                )}
"""

    render_add = """                {allWarnings.length ? (
                  <ul className="space-y-2 text-sm text-amber-100">
                    {allWarnings.map((item) => (
                      <li key={item} className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-2">{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No warnings.</p>
                )}
"""

    if "{allWarnings.map" not in text:
        text = text.replace(render_marker, render_add)

    path.write_text(text)


def write_doc() -> None:
    path = ROOT / "readme/README_V13_MODEL_PROFILES.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("""# AgentX V13 — Model Profile Visibility and Routing Warnings

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
""")


def main() -> None:
    patch_models_page()
    patch_health_page()
    write_doc()
    print("Applied AgentX V13 model profile polish.")


if __name__ == "__main__":
    main()
