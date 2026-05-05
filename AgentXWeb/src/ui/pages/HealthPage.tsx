import React, { useEffect, useMemo, useState } from "react";

import { getHealthFull, type FullHealthResponse, type HealthCheckStatus, type HealthPathStatus } from "../../api/client";
import { Panel } from "../components/Panel";
import { ScrollArea } from "../components/ScrollArea";
import { tokens } from "../tokens";

type Props = {
  statusOk: boolean;
  onSystemMessage?: (message: string) => void;
};

function stateClass(ok: boolean): string {
  return ok
    ? "border-emerald-400/25 bg-emerald-500/10 text-emerald-100"
    : "border-rose-400/25 bg-rose-500/10 text-rose-100";
}

function StatusBadge({ ok, label }: { ok: boolean; label?: string }) {
  return (
    <span className={["rounded-full border px-2 py-0.5 text-xs font-semibold", stateClass(ok)].join(" ")}>
      {label || (ok ? "online" : "offline")}
    </span>
  );
}

function formatLatency(value: number | null | undefined): string {
  if (!Number.isFinite(Number(value))) return "-";
  return `${Number(value).toFixed(1)} ms`;
}

function HealthRow({ label, value, ok }: { label: string; value: React.ReactNode; ok?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-800/70 py-2 last:border-b-0">
      <div className="text-sm text-slate-400">{label}</div>
      <div className="flex items-center gap-2 text-right text-sm font-medium text-slate-100">
        {ok !== undefined ? <StatusBadge ok={ok} /> : null}
        <span className="break-all">{value}</span>
      </div>
    </div>
  );
}

function OllamaCard({ title, check }: { title: string; check?: HealthCheckStatus | null }) {
  if (!check) {
    return (
      <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="font-semibold text-slate-100">{title}</h3>
          <StatusBadge ok={false} label="not configured" />
        </div>
        <p className="text-sm text-slate-500">No endpoint configured for this slot.</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-100">{title}</h3>
        <StatusBadge ok={check.ok} />
      </div>
      <div className="space-y-1">
        <HealthRow label="URL" value={check.url || "-"} />
        <HealthRow label="Host" value={check.host || "-"} />
        <HealthRow label="Port" value={check.port ?? "-"} />
        <HealthRow label="Latency" value={formatLatency(check.latency_ms)} />
        {check.error ? <HealthRow label="Error" value={check.error} ok={false} /> : null}
      </div>
    </div>
  );
}

function PathCard({ title, path }: { title: string; path: HealthPathStatus }) {
  return (
    <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h3 className="font-semibold text-slate-100">{title}</h3>
        <StatusBadge ok={path.exists && path.writable} label={path.exists && path.writable ? "ready" : "check"} />
      </div>
      <div className="space-y-1">
        <HealthRow label="Path" value={path.path} />
        <HealthRow label="Exists" value={path.exists ? "yes" : "no"} ok={path.exists} />
        <HealthRow label="Writable" value={path.writable ? "yes" : "no"} ok={path.writable} />
      </div>
    </div>
  );
}

function buildSummary(data: FullHealthResponse): string {
  const warnings = data.diagnostics?.warnings || [];
  const errors = data.diagnostics?.errors || [];
  return [
    `AgentX Health: ${data.ok ? "OK" : "CHECK"}`,
    `version: ${data.version}`,
    `branch: ${data.git?.branch || "-"}`,
    `commit: ${data.git?.commit || "-"}`,
    `api: ${data.api.host}:${data.api.port}`,
    `ollama default: ${data.ollama.default?.ok ? "online" : "offline"}`,
    `workspace: ${data.workspace.exists && data.workspace.writable ? "ready" : "check"}`,
    `validation: ${data.validation.available ? "available" : "unavailable"}`,
    `warnings: ${warnings.length}`,
    `errors: ${errors.length}`,
  ].join("\\n");
}

export function HealthPage({ statusOk, onSystemMessage }: Props) {
  const [health, setHealth] = useState<FullHealthResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const warnings = useMemo(() => health?.diagnostics?.warnings || [], [health]);
  const errors = useMemo(() => health?.diagnostics?.errors || [], [health]);

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const next = await getHealthFull();
      setHealth(next);
      onSystemMessage?.(`Health refresh: ${next.ok ? "OK" : "needs attention"}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      onSystemMessage?.(`Health refresh failed: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const copySummary = async () => {
    if (!health) return;
    await navigator.clipboard.writeText(buildSummary(health));
    onSystemMessage?.("Copied health summary to clipboard.");
  };

  return (
    <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,0.95fr)_minmax(0,1.05fr)]">
      <Panel>
        <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
          <div>
            <h2 className="text-lg font-semibold text-slate-100">System Health</h2>
            <p className="text-sm text-slate-400">V10 live runtime, Ollama, workspace, and validation status.</p>
          </div>
          <div className="flex gap-2">
            <button className={tokens.buttonSecondary} type="button" onClick={copySummary} disabled={!health}>
              Copy Summary
            </button>
            <button className={tokens.button} type="button" onClick={() => void refresh()} disabled={loading}>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>
        </div>
        <ScrollArea className="h-full pr-2">
          {error ? (
            <div className="mb-3 rounded-2xl border border-rose-400/25 bg-rose-500/10 p-3 text-sm text-rose-100">
              {error}
            </div>
          ) : null}

          {!health ? (
            <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">
              {loading ? "Loading health snapshot..." : "No health snapshot loaded yet."}
            </div>
          ) : (
            <div className="space-y-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-slate-100">AgentX Runtime</h3>
                    <p className="text-xs text-slate-500">Current API-reported V10 health snapshot.</p>
                  </div>
                  <StatusBadge ok={health.ok && statusOk} label={health.ok && statusOk ? "healthy" : "check"} />
                </div>
                <div className="space-y-1">
                  <HealthRow label="Version" value={health.version} />
                  <HealthRow label="Service" value={health.service} />
                  <HealthRow label="API" value={`${health.api.host}:${health.api.port}`} ok={statusOk} />
                  <HealthRow label="Auth" value={health.api.auth_enabled ? "enabled" : "disabled"} ok={health.api.auth_enabled} />
                  <HealthRow label="Rate limit" value={health.api.rate_limit_enabled ? "enabled" : "disabled"} />
                  <HealthRow label="Git branch" value={health.git?.branch || "-"} />
                  <HealthRow label="Git commit" value={health.git?.commit || "-"} />
                  <HealthRow label="Python" value={health.system.python} />
                </div>
              </div>

              <div className="grid gap-3 xl:grid-cols-3">
                <OllamaCard title="Default Ollama" check={health.ollama.default} />
                <OllamaCard title="Fast Ollama" check={health.ollama.fast} />
                <OllamaCard title="Heavy Ollama" check={health.ollama.heavy} />
              </div>

              <PathCard title="Workspace Root" path={health.workspace} />
            </div>
          )}
        </ScrollArea>
      </Panel>

      <Panel>
        <div className="mb-4">
          <h2 className="text-lg font-semibold text-slate-100">Diagnostics</h2>
          <p className="text-sm text-slate-400">Warnings, errors, and local data paths.</p>
        </div>
        <ScrollArea className="h-full pr-2">
          {health ? (
            <div className="space-y-3">
              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <h3 className="mb-3 font-semibold text-slate-100">Validation</h3>
                <HealthRow label="Runner" value={health.validation.available ? "available" : "unavailable"} ok={health.validation.available} />
              </div>

              <div className="grid gap-3">
                <PathCard title="Threads Directory" path={health.data.threads} />
                <PathCard title="Projects Directory" path={health.data.projects} />
                <PathCard title="Scripts Directory" path={health.data.scripts} />
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <h3 className="mb-3 font-semibold text-slate-100">Warnings</h3>
                {warnings.length ? (
                  <ul className="space-y-2 text-sm text-amber-100">
                    {warnings.map((item) => (
                      <li key={item} className="rounded-xl border border-amber-400/20 bg-amber-500/10 p-2">{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No warnings.</p>
                )}
              </div>

              <div className="rounded-2xl border border-slate-800 bg-slate-950/70 p-4">
                <h3 className="mb-3 font-semibold text-slate-100">Errors</h3>
                {errors.length ? (
                  <ul className="space-y-2 text-sm text-rose-100">
                    {errors.map((item) => (
                      <li key={item} className="rounded-xl border border-rose-400/20 bg-rose-500/10 p-2">{item}</li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-sm text-slate-500">No errors.</p>
                )}
              </div>
            </div>
          ) : (
            <p className="text-sm text-slate-500">Diagnostics will appear after the first refresh.</p>
          )}
        </ScrollArea>
      </Panel>
    </div>
  );
}
