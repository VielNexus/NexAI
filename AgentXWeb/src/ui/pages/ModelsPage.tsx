import React, { useEffect, useMemo, useState } from "react";
import { compareOllamaEndpoints, estimateContextBudget, getOllamaBenchmarkHistory, getOllamaPs, runOllamaBenchmark, type AgentXSettings, type ContextBudgetResponse, type OllamaBenchHistoryResponse, type OllamaBenchResponse, type OllamaCompareResponse, type OllamaPsResponse, type StatusResponse } from "../../api/client";
import { Panel } from "../components/Panel";
import { ScrollArea } from "../components/ScrollArea";
import { tokens } from "../tokens";

type Props = {
  statusOk: boolean;
  status: Pick<StatusResponse, "chat_provider" | "chat_model" | "available_chat_models" | "ollama_base_url" | "ollama_endpoints" | "models_error" | "models_refreshing" | "models_last_refresh">;
  settings: AgentXSettings | null;
  onUseModel: (provider: string, model: string) => void;
  onRefreshModels: () => void;
  onSystemMessage: (message: string) => void;
};

type ModelCard = {
  id: string;
  provider: string;
  model: string;
  endpoint: string;
  baseUrl: string;
  reachable: boolean | null;
  gpuPin: string | null;
  role: string;
  installed: boolean;
};

function baseModelName(model: string): string {
  return model.split(":")[0]?.trim() || model;
}

function ollamaLibraryUrl(model: string): string {
  const base = baseModelName(model).replace(/^x\//, "");
  return `https://ollama.com/library/${encodeURIComponent(base)}`;
}

function modelRole(model: string, settings: AgentXSettings | null | undefined, endpoint: string): string {
  const lower = model.toLowerCase();
  if (settings?.ollamaFastModel === model) return "Fast / Draft";
  if (settings?.ollamaHeavyModel === model) return "Heavy / Review";
  if (/devstral|coder|code|deepseek-coder|qwen.*coder/.test(lower)) return "Coding";
  if (/vision|llava|moondream/.test(lower)) return "Vision";
  if (/llama|mistral|mixtral|qwen|glm|kimi/.test(lower)) return endpoint === "heavy" ? "Reasoning" : "Chat";
  return endpoint === "fast" ? "Fast chat" : endpoint === "heavy" ? "Heavy task" : "General";
}

function endpointLabel(endpoint: string): string {
  if (endpoint === "default") return "Default";
  if (endpoint === "fast") return "Fast";
  if (endpoint === "heavy") return "Heavy";
  if (endpoint === "cloud") return "Cloud";
  return endpoint;
}


function formatNumber(value: number | null | undefined, suffix = ""): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "n/a";
  return `${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}${suffix}`;
}

function modelRuntimeName(model: Record<string, unknown>): string {
  return String(model.name || model.model || "unknown");
}

function modelRuntimeLine(model: Record<string, unknown>): string {
  const processor = String(model.processor || "").trim();
  const context = model.context === null || model.context === undefined ? "" : `ctx ${model.context}`;
  const vram = typeof model.size_vram === "number" ? `${(model.size_vram / (1024 ** 3)).toFixed(1)} GB VRAM` : "";
  return [processor, context, vram].filter(Boolean).join(" · ") || "loaded";
}

function sameModelName(a: string, b: string): boolean {
  return a === b || a.split(":")[0] === b.split(":")[0];
}

function bestEndpointLine(compare: OllamaCompareResponse | null): string {
  if (!compare?.best_endpoint) return "No clear winner yet.";
  return `${endpointLabel(compare.best_endpoint)} is leading at ${formatNumber(compare.best_tokens_per_second, " tok/s")}.`;
}

function uniqueCards(cards: ModelCard[]): ModelCard[] {
  const seen = new Set<string>();
  const result: ModelCard[] = [];
  for (const card of cards) {
    const key = `${card.provider}:${card.endpoint}:${card.model}`;
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(card);
  }
  const order: Record<string, number> = { default: 0, fast: 1, heavy: 2, cloud: 3 };
  return result.sort((a, b) => (order[a.endpoint] ?? 9) - (order[b.endpoint] ?? 9) || a.model.localeCompare(b.model));
}

export function ModelsPage(props: Props) {
  const [filter, setFilter] = useState("");
  const [endpointFilter, setEndpointFilter] = useState("all");
  const [runtimeEndpoint, setRuntimeEndpoint] = useState("default");
  const [runtimePs, setRuntimePs] = useState<OllamaPsResponse | null>(null);
  const [runtimeLoading, setRuntimeLoading] = useState(false);
  const [runtimeError, setRuntimeError] = useState<string | null>(null);
  const [benchRunning, setBenchRunning] = useState<string | null>(null);
  const [benchResult, setBenchResult] = useState<OllamaBenchResponse | null>(null);
  const [benchError, setBenchError] = useState<string | null>(null);
  const [benchHistory, setBenchHistory] = useState<OllamaBenchHistoryResponse | null>(null);
  const [compareRunning, setCompareRunning] = useState<string | null>(null);
  const [compareResult, setCompareResult] = useState<OllamaCompareResponse | null>(null);
  const [budget, setBudget] = useState<ContextBudgetResponse | null>(null);

  const cards = useMemo(() => {
    const output: ModelCard[] = [];
    const endpoints = props.status.ollama_endpoints ?? {};

    for (const [endpoint, info] of Object.entries(endpoints)) {
      for (const model of info.models ?? []) {
        output.push({
          id: `ollama:${endpoint}:${model}`,
          provider: "ollama",
          model,
          endpoint,
          baseUrl: info.base_url || props.status.ollama_base_url || "",
          reachable: typeof info.reachable === "boolean" ? info.reachable : null,
          gpuPin: info.gpu_pin ?? null,
          role: modelRole(model, props.settings, endpoint),
          installed: true,
        });
      }
    }

    for (const [provider, models] of Object.entries(props.status.available_chat_models ?? {})) {
      for (const model of models ?? []) {
        output.push({
          id: `${provider}:available:${model}`,
          provider,
          model,
          endpoint: provider === "ollama" ? "default" : "cloud",
          baseUrl: provider === "ollama" ? props.status.ollama_base_url || "" : "cloud provider",
          reachable: null,
          gpuPin: null,
          role: modelRole(model, props.settings, provider === "ollama" ? "default" : "cloud"),
          installed: provider === "ollama",
        });
      }
    }

    return uniqueCards(output);
  }, [props.status.available_chat_models, props.status.ollama_base_url, props.status.ollama_endpoints, props.settings]);

  const filteredCards = useMemo(() => {
    const term = filter.trim().toLowerCase();
    return cards.filter((card) => {
      if (endpointFilter !== "all" && card.endpoint !== endpointFilter) return false;
      if (!term) return true;
      return [card.model, card.provider, card.endpoint, card.role, card.baseUrl].some((value) => value.toLowerCase().includes(term));
    });
  }, [cards, endpointFilter, filter]);

  const currentProvider = props.status.chat_provider || props.settings?.chatProvider || "ollama";
  const currentModel = props.status.chat_model || props.settings?.chatModel || "";
  const endpointNames = Array.from(new Set(cards.map((card) => card.endpoint))).sort();
  const loadedRuntimeModels = useMemo(() => new Set((runtimePs?.models ?? []).map((model) => modelRuntimeName(model))), [runtimePs]);

  const loadRuntime = async (endpoint = runtimeEndpoint) => {
    setRuntimeLoading(true);
    setRuntimeError(null);
    try {
      const res = await getOllamaPs(endpoint);
      setRuntimePs(res);
    } catch (err) {
      setRuntimeError(err instanceof Error ? err.message : String(err));
      setRuntimePs(null);
    } finally {
      setRuntimeLoading(false);
    }
  };

  useEffect(() => {
    if (!props.statusOk) return;
    void loadRuntime(runtimeEndpoint);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.statusOk, runtimeEndpoint]);

  const loadBenchHistory = async () => {
    try {
      setBenchHistory(await getOllamaBenchmarkHistory(12));
    } catch {
      setBenchHistory(null);
    }
  };

  useEffect(() => {
    if (!props.statusOk) return;
    void loadBenchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [props.statusOk]);

  useEffect(() => {
    if (!currentModel) return;
    let cancelled = false;
    void (async () => {
      try {
        const res = await estimateContextBudget({ model: currentModel, message: "", attachment_chars: 0 });
        if (!cancelled) setBudget(res);
      } catch {
        if (!cancelled) setBudget(null);
      }
    })();
    return () => { cancelled = true; };
  }, [currentModel]);

  const runBench = async (card: ModelCard) => {
    setBenchRunning(card.id);
    setBenchError(null);
    try {
      const res = await runOllamaBenchmark({ endpoint: card.endpoint, model: card.model, num_predict: 64, prompt: "Say READY and one short sentence about your role in AgentX." });
      setBenchResult(res);
      void loadBenchHistory();
      void loadRuntime(card.endpoint);
      props.onSystemMessage(`Benchmark complete for ${card.model}: ${formatNumber(res.tokens_per_second, " tok/s")}.`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setBenchError(message);
      props.onSystemMessage(`Benchmark failed for ${card.model}: ${message}`);
    } finally {
      setBenchRunning(null);
    }
  };

  const compareEndpoints = async (card: ModelCard) => {
    setCompareRunning(card.id);
    setBenchError(null);
    try {
      const res = await compareOllamaEndpoints({ model: card.model, endpoints: ["fast", "heavy"], num_predict: 64 });
      setCompareResult(res);
      if (res.results[0]) setBenchResult(res.results[0]);
      void loadBenchHistory();
      props.onSystemMessage(`Endpoint compare complete for ${card.model}. ${bestEndpointLine(res)}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setBenchError(message);
      props.onSystemMessage(`Endpoint compare failed for ${card.model}: ${message}`);
    } finally {
      setCompareRunning(null);
    }
  };

  return (
    <div className="agentx-model-deck flex min-h-0 flex-1 flex-col gap-3">
      <div className="agentx-model-deck-hero">
        <div>
          <div className={tokens.smallLabel}>Model Deck</div>
          <h2>Local model command center</h2>
          <p>See every model AgentX can route to, which endpoint owns it, and what role it should play.</p>
        </div>
        <div className="agentx-model-deck-hero__actions">
          <button className={tokens.buttonSecondary} type="button" onClick={props.onRefreshModels} disabled={!props.statusOk || Boolean(props.status.models_refreshing)}>
            {props.status.models_refreshing ? "Refreshing..." : "Refresh Models"}
          </button>
          <span className="agentx-model-deck-pill">Current: {currentProvider}:{currentModel || "none"}</span>
        </div>
      </div>

      {props.status.models_error ? (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-500/10 px-3 py-2 text-sm text-amber-100">{props.status.models_error}</div>
      ) : null}

      <div className="grid min-h-0 gap-3 lg:grid-cols-[minmax(0,1fr)_320px]">
        <Panel className="min-h-0 p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className={tokens.smallLabel}>Installed / Available Models</div>
              <div className={tokens.helperText}>{filteredCards.length} shown of {cards.length} discovered models.</div>
            </div>
            <div className="flex flex-wrap gap-2">
              <input className={tokens.inputCompact} value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="Search models..." />
              <select className={tokens.inputCompact} value={endpointFilter} onChange={(event) => setEndpointFilter(event.target.value)}>
                <option value="all">All endpoints</option>
                {endpointNames.map((endpoint) => <option key={endpoint} value={endpoint}>{endpointLabel(endpoint)}</option>)}
              </select>
            </div>
          </div>

          <ScrollArea className="mt-3 max-h-[68vh] pr-1">
            <div className="agentx-model-card-grid">
              {filteredCards.map((card) => {
                const selected = card.provider === currentProvider && card.model === currentModel;
                const loadedHere = card.provider === "ollama" && runtimeEndpoint === card.endpoint && Array.from(loadedRuntimeModels).some((loaded) => sameModelName(loaded, card.model));
                return (
                  <article key={card.id} className={["agentx-model-card", selected ? "agentx-model-card--selected" : ""].join(" ")}>
                    <div className="agentx-model-card__top">
                      <div className="min-w-0">
                        <h3 title={card.model}>{card.model}</h3>
                        <p>{card.provider} · {endpointLabel(card.endpoint)}{card.gpuPin ? ` · GPU ${card.gpuPin}` : ""}</p>
                      </div>
                      <span className={card.reachable === false ? "agentx-model-status agentx-model-status--bad" : "agentx-model-status agentx-model-status--ok"}>
                        {card.reachable === false ? "offline" : loadedHere ? "loaded" : card.installed ? "available" : "listed"}
                      </span>
                    </div>
                    <div className="agentx-model-card__meta">
                      <span>Role: <strong>{card.role}</strong></span>
                      <span>Endpoint: <strong>{endpointLabel(card.endpoint)}</strong></span>
                      <span>Base: <strong>{card.baseUrl || "unknown"}</strong></span>
                    </div>
                    <div className="agentx-model-card__actions">
                      <button className={tokens.button} type="button" disabled={!props.statusOk || selected} onClick={() => props.onUseModel(card.provider, card.model)}>
                        {selected ? "Using for Chat" : "Use for Chat"}
                      </button>
                      {card.provider === "ollama" ? <button className={tokens.buttonSecondary} type="button" disabled={!props.statusOk || benchRunning === card.id} onClick={() => void runBench(card)}>{benchRunning === card.id ? "Benchmarking..." : "Bench"}</button> : null}
                      {card.provider === "ollama" ? <button className={tokens.buttonSecondary} type="button" disabled={!props.statusOk || compareRunning === card.id} onClick={() => void compareEndpoints(card)}>{compareRunning === card.id ? "Comparing..." : "Compare F/H"}</button> : null}
                      {card.provider === "ollama" ? <a className={tokens.buttonSecondary} href={ollamaLibraryUrl(card.model)} target="_blank" rel="noreferrer">Open Ollama</a> : null}
                    </div>
                  </article>
                );
              })}
              {filteredCards.length === 0 ? <div className={tokens.helperText}>No models match your current filter.</div> : null}
            </div>
          </ScrollArea>
        </Panel>

        <div className="grid content-start gap-3">
          <Panel className="p-3">
            <div className={tokens.smallLabel}>Routing</div>
            <div className="mt-2 grid gap-2 text-sm text-slate-200">
              <div>Default: <strong>{props.settings?.ollamaBaseUrl || props.status.ollama_base_url || "not set"}</strong></div>
              <div>Fast model: <strong>{props.settings?.ollamaFastModel || "not set"}</strong></div>
              <div>Heavy model: <strong>{props.settings?.ollamaHeavyModel || "not set"}</strong></div>
              <div>Draft route: <strong>{props.settings?.ollamaDraftEndpoint || "default"}</strong></div>
              <div>Review route: <strong>{props.settings?.ollamaReviewEndpoint || "default"}</strong></div>
              <div>Repair route: <strong>{props.settings?.ollamaRepairEndpoint || "default"}</strong></div>
            </div>
          </Panel>

          <Panel className="p-3">
            <div className="flex items-center justify-between gap-2">
              <div className={tokens.smallLabel}>Runtime / Ollama ps</div>
              <button className={tokens.buttonSecondary} type="button" disabled={!props.statusOk || runtimeLoading} onClick={() => void loadRuntime()}>
                {runtimeLoading ? "Checking..." : "Refresh"}
              </button>
            </div>
            <select className={[tokens.inputCompact, "mt-2 w-full"].join(" ")} value={runtimeEndpoint} onChange={(event) => setRuntimeEndpoint(event.target.value)}>
              {Array.from(new Set(["default", "fast", "heavy", ...endpointNames.filter((name) => name !== "cloud")])).map((endpoint) => (
                <option key={endpoint} value={endpoint}>{endpointLabel(endpoint)}</option>
              ))}
            </select>
            {runtimeError ? <div className="mt-2 rounded-xl border border-rose-400/25 bg-rose-500/10 p-2 text-xs text-rose-100">{runtimeError}</div> : null}
            <div className="mt-2 grid gap-2 text-xs text-slate-300">
              <div>Base: <strong>{runtimePs?.base_url || props.status.ollama_base_url || "unknown"}</strong></div>
              {(runtimePs?.models ?? []).length ? (runtimePs?.models ?? []).map((model, index) => (
                <div key={`${modelRuntimeName(model)}-${index}`} className="rounded-xl border border-slate-700/60 bg-slate-950/45 p-2">
                  <div className="font-semibold text-slate-100">{modelRuntimeName(model)}</div>
                  <div className="text-slate-400">{modelRuntimeLine(model)}</div>
                </div>
              )) : <div className="text-slate-500">No loaded models reported yet. Run a chat or benchmark first.</div>}
            </div>
          </Panel>

          <Panel className="p-3">
            <div className={tokens.smallLabel}>Latest Benchmark</div>
            {benchError ? <div className="mt-2 rounded-xl border border-rose-400/25 bg-rose-500/10 p-2 text-xs text-rose-100">{benchError}</div> : null}
            {benchResult ? (
              <div className="mt-2 grid gap-2 text-sm text-slate-300">
                <div>Model: <strong>{benchResult.model}</strong></div>
                <div>Endpoint: <strong>{endpointLabel(benchResult.endpoint)}</strong></div>
                <div>TPS: <strong>{formatNumber(benchResult.tokens_per_second, " tok/s")}</strong></div>
                <div>Total: <strong>{formatNumber(benchResult.total_ms, " ms")}</strong></div>
                <div>Load: <strong>{formatNumber(benchResult.load_ms, " ms")}</strong></div>
                <div>Output tokens: <strong>{formatNumber(benchResult.output_tokens)}</strong></div>
              </div>
            ) : <div className="mt-2 text-sm text-slate-500">Click Bench on any Ollama model to measure this endpoint.</div>}
          </Panel>

          <Panel className="p-3">
            <div className={tokens.smallLabel}>Endpoint Compare</div>
            {compareResult ? (
              <div className="mt-2 grid gap-2 text-sm text-slate-300">
                <div>{bestEndpointLine(compareResult)}</div>
                {compareResult.results.map((result) => (
                  <div key={`${result.endpoint}-${result.model}-${result.total_ms}`} className="rounded-xl border border-slate-700/60 bg-slate-950/45 p-2 text-xs">
                    <div><strong>{endpointLabel(result.endpoint)}</strong> · {formatNumber(result.tokens_per_second, " tok/s")}</div>
                    <div className="text-slate-400">Total {formatNumber(result.total_ms, " ms")} · Load {formatNumber(result.load_ms, " ms")}</div>
                  </div>
                ))}
                {compareResult.errors.map((err) => <div key={err.endpoint} className="text-xs text-rose-200">{endpointLabel(err.endpoint)}: {err.error}</div>)}
              </div>
            ) : <div className="mt-2 text-sm text-slate-500">Click Compare F/H on a model to test fast vs heavy routing.</div>}
          </Panel>

          <Panel className="p-3">
            <div className={tokens.smallLabel}>Context Budget</div>
            {budget ? (
              <div className="mt-2 grid gap-2 text-sm text-slate-300">
                <div>Target: <strong>{formatNumber(budget.target_context_tokens)} tokens</strong></div>
                <div>Harness estimate: <strong>{formatNumber(budget.estimated_used_tokens)} used</strong></div>
                <div>Remaining: <strong>{formatNumber(budget.estimated_remaining_tokens)} tokens</strong></div>
                <div>Risk: <strong className={budget.risk === "high" || budget.risk === "critical" ? "text-amber-200" : "text-emerald-200"}>{budget.risk}</strong></div>
                {budget.profile ? <div className="text-xs text-slate-400">Profile: {budget.profile.context_tier} · {budget.profile.role_hint}. {budget.profile.advice}</div> : null}
              </div>
            ) : <div className="mt-2 text-sm text-slate-500">Select an Ollama model to estimate safe context headroom.</div>}
          </Panel>

          <Panel className="p-3">
            <div className={tokens.smallLabel}>Benchmark History</div>
            {(benchHistory?.history ?? []).length ? (
              <div className="mt-2 grid gap-2 text-xs text-slate-300">
                {(benchHistory?.history ?? []).slice(0, 6).map((item, index) => (
                  <div key={`${item.model}-${item.endpoint}-${item.total_ms}-${index}`} className="rounded-xl border border-slate-700/60 bg-slate-950/45 p-2">
                    <div className="font-semibold text-slate-100">{item.model}</div>
                    <div>{endpointLabel(item.endpoint)} · {formatNumber(item.tokens_per_second, " tok/s")} · {formatNumber(item.total_ms, " ms")}</div>
                  </div>
                ))}
              </div>
            ) : <div className="mt-2 text-sm text-slate-500">Benchmark results will be saved here after each run.</div>}
          </Panel>

          <Panel className="p-3">
            <div className={tokens.smallLabel}>Recommendations</div>
            <div className="mt-2 grid gap-2 text-sm text-slate-300">
              <div><strong>Coding:</strong> devstral, qwen-coder, deepseek-coder, dolphincoder.</div>
              <div><strong>Drafts:</strong> smaller fast models with low latency.</div>
              <div><strong>Review:</strong> heavier models with stronger reasoning.</div>
              <div><strong>Vision:</strong> models with llava/vision tags when available.</div>
            </div>
          </Panel>
        </div>
      </div>
    </div>
  );
}
