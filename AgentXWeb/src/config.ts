export const config = {
  apiBase: (() => {
    const runtime = (globalThis as any).__AGENTXWEB_CONFIG__?.apiBase as string | undefined;
    const runtimeTrimmed = (runtime ?? "").trim();
    if (runtimeTrimmed.length > 0) return runtimeTrimmed;

    const raw = (import.meta as any).env?.VITE_AGENTX_API_BASE as string | undefined;
    const trimmed = (raw ?? "").trim();
    if (trimmed.length > 0) return trimmed;

    return "http://127.0.0.1:8420";
  })(),
  showInspector: (() => {
    const runtime = (globalThis as any).__AGENTXWEB_CONFIG__?.showInspector as boolean | undefined;
    if (typeof runtime === "boolean") return runtime;

    const hostname = (globalThis as any)?.location?.hostname as string | undefined;
    const host = (hostname ?? "").trim().toLowerCase();
    return host === "localhost" || host === "127.0.0.1";
  })(),
  threadTitleDefault: "New thread",
  threadTitleMax: 64,
  threadTitleWordLimit: 8,
  projectStorageKey: "agentxweb.projects.v1",
  threadProjectMapKey: "agentxweb.threadProjects.v1",
  codeCanvasStateKey: "agentxweb.codeCanvas.v1",
} as const;
