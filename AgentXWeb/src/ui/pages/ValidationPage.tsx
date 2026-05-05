import React, { useEffect, useMemo, useState } from "react";

import {
  getPatchCandidateHistory,
  getValidationHistory,
  getValidationPresets,
  getValidationWorkspaces,
  runValidation,
  validatePatchCandidate,
  type PatchCandidateHistoryItem,
  type PatchCandidateResult,
  type ValidationPreset,
  type ValidationRunResult,
  type ValidationWorkspace,
} from "../../api/client";
import { Panel } from "../components/Panel";
import { ScrollArea } from "../components/ScrollArea";
import { tokens } from "../tokens";

type Props = {
  statusOk: boolean;
  onSystemMessage?: (message: string) => void;
};

function formatMs(value: number | null | undefined): string {
  if (!Number.isFinite(Number(value))) return "-";
  const n = Number(value);
  if (n < 1000) return `${Math.round(n)} ms`;
  return `${(n / 1000).toFixed(2)} s`;
}

function formatDate(ts: number | null | undefined): string {
  if (!Number.isFinite(Number(ts))) return "Unknown";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(Number(ts) * 1000));
}

function statusClass(ok: boolean): string {
  return ok
    ? "border-emerald-400/25 bg-emerald-500/10 text-emerald-100"
    : "border-rose-400/25 bg-rose-500/10 text-rose-100";
}

function summarizeRun(run: ValidationRunResult): string {
  const lines: string[] = [];
  lines.push(`AgentX validation ${run.ok ? "PASS" : "FAIL"}: ${run.run_id}`);
  lines.push(`preset: ${run.preset}`);
  lines.push(`workspace: ${run.workspace_path}`);
  lines.push(`duration: ${formatMs(run.duration_ms)}`);
  lines.push(`steps: ${String(run.summary?.passed ?? 0)} passed / ${String(run.summary?.failed ?? 0)} failed`);
  lines.push("");
  for (const step of run.results) {
    lines.push(`## ${step.name} - ${step.ok ? "PASS" : "FAIL"}`);
    lines.push(`cwd: ${step.cwd}`);
    lines.push(`command: ${step.command}`);
    lines.push(`exit: ${step.exit_code ?? "-"}`);
    lines.push(`duration: ${formatMs(step.duration_ms)}`);
    if (step.error) lines.push(`error: ${step.error}`);
    if (step.stderr) lines.push(`stderr:\n${step.stderr}`);
    if (step.stdout) lines.push(`stdout:\n${step.stdout}`);
    lines.push("");
  }
  return lines.join("\n");
}

function summarizePatchCandidate(candidate: PatchCandidateResult): string {
  const lines: string[] = [];
  lines.push(`AgentX patch candidate ${candidate.ok ? "PASS" : "FAIL"}: ${candidate.candidate_id}`);
  lines.push(`preset: ${candidate.preset}`);
  lines.push(`source workspace: ${candidate.source_workspace_path}`);
  lines.push(`temp workspace: ${candidate.temp_workspace_path || "discarded"}`);
  lines.push(`duration: ${formatMs(candidate.duration_ms)}`);
  lines.push("");
  lines.push(`## ${candidate.apply_result.name} - ${candidate.apply_result.ok ? "PASS" : "FAIL"}`);
  lines.push(`command: ${candidate.apply_result.command}`);
  if (candidate.apply_result.error) lines.push(`error: ${candidate.apply_result.error}`);
  if (candidate.apply_result.stderr) lines.push(`stderr:\n${candidate.apply_result.stderr}`);
  if (candidate.apply_result.stdout) lines.push(`stdout:\n${candidate.apply_result.stdout}`);
  if (candidate.validation_result) {
    lines.push("");
    lines.push(summarizeRun(candidate.validation_result));
  }
  if (candidate.repair_packet) {
    lines.push("");
    lines.push("## Repair packet");
    lines.push(candidate.repair_packet.summary || "");
    lines.push("");
    lines.push(candidate.repair_packet.prompt || "");
  }
  return lines.join("\n");
}

export function ValidationPage({ statusOk, onSystemMessage }: Props) {
  const [workspacePath, setWorkspacePath] = useState(() => localStorage.getItem("agentx.validation.workspace") || "");
  const [selectedPreset, setSelectedPreset] = useState(() => localStorage.getItem("agentx.validation.preset") || "agentx_full");
  const [presets, setPresets] = useState<ValidationPreset[]>([]);
  const [workspaces, setWorkspaces] = useState<ValidationWorkspace[]>([]);
  const [history, setHistory] = useState<ValidationRunResult[]>([]);
  const [patchHistory, setPatchHistory] = useState<PatchCandidateHistoryItem[]>([]);
  const [latest, setLatest] = useState<ValidationRunResult | null>(null);
  const [patchText, setPatchText] = useState("");
  const [keepPatchWorktree, setKeepPatchWorktree] = useState(false);
  const [repairOfCandidateId, setRepairOfCandidateId] = useState<string | null>(null);
  const [patchCandidate, setPatchCandidate] = useState<PatchCandidateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [patchRunning, setPatchRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const selectedPresetDetail = useMemo(() => presets.find((p) => p.name === selectedPreset) ?? null, [presets, selectedPreset]);

  const applyWorkspace = (workspace: ValidationWorkspace) => {
    setWorkspacePath(workspace.path);
    setSelectedPreset(workspace.preset);
    localStorage.setItem("agentx.validation.workspace", workspace.path);
    localStorage.setItem("agentx.validation.preset", workspace.preset);
    setNotice(`Selected ${workspace.label}.`);
  };

  const refresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const [presetRes, workspaceRes, historyRes, patchHistoryRes] = await Promise.all([
        getValidationPresets(),
        getValidationWorkspaces(),
        getValidationHistory(20),
        getPatchCandidateHistory(20),
      ]);
      const nextPresets = presetRes.presets || [];
      const nextWorkspaces = workspaceRes.workspaces || [];
      setPresets(nextPresets);
      setWorkspaces(nextWorkspaces);
      setHistory(historyRes.runs || []);
      setPatchHistory(patchHistoryRes.candidates || []);
      if (!selectedPreset && nextPresets[0]?.name) setSelectedPreset(nextPresets[0].name);
      if (!workspacePath.trim() && nextWorkspaces[0]) {
        setWorkspacePath(nextWorkspaces[0].path);
        if (nextWorkspaces[0].preset) setSelectedPreset(nextWorkspaces[0].preset);
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      onSystemMessage?.(`Validation load failed: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const run = async (override?: { workspace_path?: string; preset?: string }) => {
    const path = (override?.workspace_path ?? workspacePath).trim();
    const preset = override?.preset ?? selectedPreset;
    if (!path) {
      setError("Workspace path is required. Use an auto-detected workspace shortcut or paste the AgentX repo path.");
      return;
    }
    localStorage.setItem("agentx.validation.workspace", path);
    localStorage.setItem("agentx.validation.preset", preset);
    setRunning(true);
    setError(null);
    setNotice(null);
    try {
      const result = await runValidation({ workspace_path: path, preset });
      setWorkspacePath(result.workspace_path || path);
      setSelectedPreset(preset);
      setLatest(result);
      setHistory((items) => [result, ...items.filter((item) => item.run_id !== result.run_id)].slice(0, 20));
      onSystemMessage?.(`Validation ${result.ok ? "passed" : "failed"}: ${preset}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      onSystemMessage?.(`Validation failed to start: ${message}`);
    } finally {
      setRunning(false);
    }
  };

  const runPatchCandidate = async () => {
    const path = workspacePath.trim();
    if (!path) {
      setError("Workspace path is required before validating a patch candidate.");
      return;
    }
    if (!patchText.trim()) {
      setError("Paste a unified diff before running patch candidate validation.");
      return;
    }
    localStorage.setItem("agentx.validation.workspace", path);
    localStorage.setItem("agentx.validation.preset", selectedPreset);
    setPatchRunning(true);
    setError(null);
    setNotice(null);
    try {
      const result = await validatePatchCandidate({
        workspace_path: path,
        preset: selectedPreset,
        patch_text: patchText,
        keep_worktree: keepPatchWorktree,
        repair_of_candidate_id: repairOfCandidateId,
      });
      setPatchCandidate(result);
      setRepairOfCandidateId(null);
      try {
        const patchHistoryRes = await getPatchCandidateHistory(20);
        setPatchHistory(patchHistoryRes.candidates || []);
      } catch {
        // Candidate validation succeeded; history refresh is best-effort.
      }
      if (result.validation_result) {
        setLatest(result.validation_result);
        setHistory((items) => [result.validation_result as ValidationRunResult, ...items.filter((item) => item.run_id !== result.validation_result?.run_id)].slice(0, 20));
      }
      onSystemMessage?.(`Patch candidate ${result.ok ? "passed" : "failed"}: ${selectedPreset}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setError(message);
      onSystemMessage?.(`Patch candidate validation failed to start: ${message}`);
    } finally {
      setPatchRunning(false);
    }
  };

  const activeRun = latest || history[0] || null;

  const copyPatchCandidateLogs = async () => {
    if (!patchCandidate) return;
    try {
      await navigator.clipboard.writeText(summarizePatchCandidate(patchCandidate));
      setNotice("Patch candidate logs copied.");
    } catch {
      setError("Could not copy patch candidate logs. Select and copy the output manually.");
    }
  };

  const copyRepairPrompt = async () => {
    const prompt = patchCandidate?.repair_packet?.prompt;
    if (!prompt) return;
    try {
      await navigator.clipboard.writeText(prompt);
      setNotice("Repair prompt copied. Paste it into chat and ask for a corrected unified diff only.");
    } catch {
      setError("Could not copy repair prompt. Select and copy it manually.");
    }
  };

  const startRepairIteration = () => {
    if (!patchCandidate) return;
    setRepairOfCandidateId(patchCandidate.candidate_id);
    setPatchText("");
    setNotice(`Repair iteration started for ${patchCandidate.candidate_id}. Paste the repaired unified diff and validate again.`);
  };

  const usePatchHistoryItem = (item: PatchCandidateHistoryItem) => {
    setWorkspacePath(item.source_workspace_path);
    setSelectedPreset(item.preset);
    if (item.patch_excerpt) setPatchText(item.patch_excerpt);
    setRepairOfCandidateId(item.ok ? null : item.candidate_id);
    setNotice(item.ok ? `Loaded candidate ${item.candidate_id}.` : `Loaded failed candidate ${item.candidate_id}; next patch will be linked as its repair.`);
  };

  const copyLogs = async () => {
    if (!activeRun) return;
    const text = summarizeRun(activeRun);
    try {
      await navigator.clipboard.writeText(text);
      setNotice("Validation logs copied.");
    } catch {
      setError("Could not copy logs. Select and copy the output manually from the run panel.");
    }
  };

  return (
    <div className="mt-3 grid min-h-0 flex-1 gap-3 overflow-hidden xl:grid-cols-[minmax(0,1fr)_360px]">
      <div className="flex min-h-0 flex-col gap-3">
        <Panel className="rounded-[1.45rem] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className={tokens.smallLabel}>Execute → Validate foundation</div>
              <h2 className="mt-1 text-xl font-semibold text-slate-100">Validation Pipeline</h2>
              <p className="mt-1 max-w-3xl text-sm text-slate-400">
                Run safe validation presets against a workspace before patches become trusted. Use the detected shortcuts when possible; presets are smart enough to accept either the AgentX root or the matching component folder.
              </p>
            </div>
            <button className={tokens.buttonSecondary} type="button" onClick={() => void refresh()} disabled={loading || running || patchRunning || !statusOk}>
              {loading ? "Refreshing..." : "Refresh"}
            </button>
          </div>

          {workspaces.length > 0 ? (
            <div className="mt-4">
              <div className={tokens.smallLabel}>Detected workspaces</div>
              <div className="mt-2 flex flex-wrap gap-2">
                {workspaces.slice(0, 8).map((workspace) => (
                  <button
                    key={`${workspace.label}-${workspace.path}-${workspace.preset}`}
                    type="button"
                    className="rounded-full border border-slate-800 bg-slate-950/80 px-3 py-1.5 text-xs font-semibold text-slate-200 hover:border-cyan-400/50 hover:text-cyan-100"
                    onClick={() => applyWorkspace(workspace)}
                    title={`${workspace.path} · ${workspace.preset}`}
                    disabled={running || patchRunning}
                  >
                    {workspace.label}
                    <span className="ml-2 text-slate-500">{workspace.preset}</span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_240px_auto]">
            <label className="text-sm text-slate-300">
              <span className={tokens.smallLabel}>Workspace path</span>
              <input
                className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400/60"
                value={workspacePath}
                onChange={(event) => setWorkspacePath(event.target.value)}
                placeholder="/home/nexus/projects/AgentX"
              />
            </label>
            <label className="text-sm text-slate-300">
              <span className={tokens.smallLabel}>Preset</span>
              <select
                className="mt-1 w-full rounded-xl border border-slate-800 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400/60"
                value={selectedPreset}
                onChange={(event) => setSelectedPreset(event.target.value)}
              >
                {presets.length === 0 ? <option value={selectedPreset}>{selectedPreset}</option> : null}
                {presets.map((preset) => (
                  <option key={preset.name} value={preset.name}>{preset.name}</option>
                ))}
              </select>
            </label>
            <div className="flex items-end gap-2">
              <button className={tokens.button} type="button" onClick={() => void run()} disabled={!statusOk || running || patchRunning}>
                {running ? "Running..." : "Run validation"}
              </button>
            </div>
          </div>

          {notice ? <div className="mt-3 rounded-xl border border-cyan-400/25 bg-cyan-500/10 px-3 py-2 text-sm text-cyan-100">{notice}</div> : null}
          {error ? <div className="mt-3 rounded-xl border border-rose-400/25 bg-rose-500/10 px-3 py-2 text-sm text-rose-100">{error}</div> : null}
        </Panel>

        <Panel className="rounded-[1.45rem] p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <div className={tokens.smallLabel}>Patch candidate validation</div>
              <h3 className="mt-1 text-lg font-semibold text-slate-100">Validate a diff before it touches the live repo</h3>
              <p className="mt-1 max-w-3xl text-sm text-slate-400">
                Paste a unified diff. AgentX copies the selected workspace, applies the patch there, runs the selected preset, then discards the temp copy unless you choose to keep it.
              </p>
            </div>
            <button className={tokens.buttonSecondary} type="button" onClick={() => setPatchText("")} disabled={patchRunning || !patchText}>Clear patch</button>
          </div>
          <textarea
            className="mt-3 h-40 w-full rounded-2xl border border-slate-800 bg-slate-950 p-3 font-mono text-xs text-slate-100 outline-none focus:border-cyan-400/60"
            value={patchText}
            onChange={(event) => setPatchText(event.target.value)}
            placeholder={"Paste unified diff here, for example:\ndiff --git a/README.md b/README.md\n--- a/README.md\n+++ b/README.md"}
          />
          <div className="mt-3 flex flex-wrap items-center justify-between gap-3">
            <label className="flex items-center gap-2 text-xs text-slate-400">
              <input
                type="checkbox"
                checked={keepPatchWorktree}
                onChange={(event) => setKeepPatchWorktree(event.target.checked)}
              />
              Keep temp workspace for inspection
            </label>
            <div className="flex flex-wrap gap-2">
              {patchCandidate?.repair_packet ? <button className={tokens.buttonSecondary} type="button" onClick={() => void copyRepairPrompt()}>Copy repair prompt</button> : null}
              {patchCandidate ? <button className={tokens.buttonSecondary} type="button" onClick={() => void copyPatchCandidateLogs()}>Copy candidate logs</button> : null}
              <button className={tokens.button} type="button" onClick={() => void runPatchCandidate()} disabled={!statusOk || running || patchRunning || !patchText.trim()}>
                {patchRunning ? "Validating patch..." : "Validate patch candidate"}
              </button>
            </div>
          </div>
          {patchCandidate ? (
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <div className="font-mono text-sm text-slate-100">{patchCandidate.candidate_id}</div>
                  <div className="mt-1 text-xs text-slate-500">{patchCandidate.summary?.phase ? String(patchCandidate.summary.phase) : "patch candidate"} · {formatMs(patchCandidate.duration_ms)}</div>
                </div>
                <span className={["rounded-full border px-2 py-1 text-[11px] font-semibold", statusClass(patchCandidate.ok)].join(" ")}>{patchCandidate.ok ? "PASS" : "FAIL"}</span>
              </div>
              <div className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-2">
                <div className="rounded-xl border border-slate-800 bg-black/20 p-3"><div className={tokens.smallLabel}>Source</div><div className="mt-1 break-all text-slate-200">{patchCandidate.source_workspace_path}</div></div>
                <div className="rounded-xl border border-slate-800 bg-black/20 p-3"><div className={tokens.smallLabel}>Temp workspace</div><div className="mt-1 break-all text-slate-200">{patchCandidate.temp_workspace_path || "discarded"}</div></div>
              </div>
              <div className="mt-3 rounded-xl border border-slate-800 bg-black/20 p-3">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-semibold text-slate-100">{patchCandidate.apply_result.name}</div>
                  <span className={patchCandidate.apply_result.ok ? "text-xs font-semibold text-emerald-300" : "text-xs font-semibold text-rose-300"}>{patchCandidate.apply_result.ok ? "PASS" : "FAIL"}</span>
                </div>
                <div className="mt-1 break-all font-mono text-xs text-slate-500">{patchCandidate.apply_result.command}</div>
                {patchCandidate.apply_result.error ? <div className="mt-2 text-xs text-rose-200">{patchCandidate.apply_result.error}</div> : null}
                {patchCandidate.apply_result.stderr ? <pre className="mt-3 max-h-40 overflow-auto rounded-xl border border-slate-800 bg-black/40 p-3 text-xs text-rose-100 whitespace-pre-wrap">{patchCandidate.apply_result.stderr}</pre> : null}
                {patchCandidate.apply_result.stdout ? <pre className="mt-3 max-h-40 overflow-auto rounded-xl border border-slate-800 bg-black/40 p-3 text-xs text-slate-200 whitespace-pre-wrap">{patchCandidate.apply_result.stdout}</pre> : null}
              </div>
              {patchCandidate.validation_result ? (
                <div className="mt-3 text-xs text-slate-400">Validation run: <span className="font-mono text-slate-200">{patchCandidate.validation_result.run_id}</span> · {String(patchCandidate.validation_result.summary?.passed ?? 0)} passed / {String(patchCandidate.validation_result.summary?.failed ?? 0)} failed</div>
              ) : null}
              {patchCandidate.repair_packet ? (
                <div className="mt-4 rounded-2xl border border-amber-400/20 bg-amber-500/10 p-3">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div>
                      <div className={tokens.smallLabel}>Self-correct draft packet</div>
                      <h4 className="mt-1 text-sm font-semibold text-amber-100">{patchCandidate.repair_packet.title}</h4>
                    </div>
                    <button className={tokens.buttonSecondary} type="button" onClick={() => void copyRepairPrompt()}>Copy repair prompt</button>
                  </div>
                  <p className="mt-2 whitespace-pre-wrap text-xs text-amber-100/90">{patchCandidate.repair_packet.summary}</p>
                  {patchCandidate.repair_packet.recommended_next_steps?.length ? (
                    <ol className="mt-3 list-decimal space-y-1 pl-5 text-xs text-slate-300">
                      {patchCandidate.repair_packet.recommended_next_steps.map((step, index) => (
                        <li key={`${patchCandidate.candidate_id}-repair-step-${index}`}>{step}</li>
                      ))}
                    </ol>
                  ) : null}
                  <details className="mt-3">
                    <summary className="cursor-pointer text-xs font-semibold text-amber-100">Preview repair prompt</summary>
                    <pre className="mt-2 max-h-72 overflow-auto rounded-xl border border-slate-800 bg-black/40 p-3 text-xs text-slate-100 whitespace-pre-wrap">{patchCandidate.repair_packet.prompt}</pre>
                  </details>
                </div>
              ) : null}
            </div>
          ) : null}
        </Panel>

        <Panel className="min-h-0 flex-1 rounded-[1.45rem] p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className={tokens.smallLabel}>Latest run</div>
              <h3 className="mt-1 text-lg font-semibold text-slate-100">{activeRun ? activeRun.run_id : "No validation run yet"}</h3>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {activeRun ? (
                <>
                  <button className={tokens.buttonSecondary} type="button" onClick={() => void copyLogs()}>Copy logs</button>
                  <button
                    className={tokens.buttonSecondary}
                    type="button"
                    onClick={() => void run({ workspace_path: activeRun.workspace_path, preset: activeRun.preset })}
                    disabled={!statusOk || running || patchRunning}
                  >
                    Rerun
                  </button>
                  <span className={["rounded-full border px-3 py-1 text-xs font-semibold", statusClass(activeRun.ok)].join(" ")}>{activeRun.ok ? "PASS" : "FAIL"}</span>
                </>
              ) : null}
            </div>
          </div>

          {activeRun ? (
            <>
              <div className="mt-3 grid gap-2 text-xs text-slate-400 sm:grid-cols-5">
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"><div className={tokens.smallLabel}>Preset</div><div className="mt-1 text-slate-100">{activeRun.preset}</div></div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3 sm:col-span-2"><div className={tokens.smallLabel}>Workspace</div><div className="mt-1 break-all text-slate-100">{activeRun.workspace_path}</div></div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"><div className={tokens.smallLabel}>Duration</div><div className="mt-1 text-slate-100">{formatMs(activeRun.duration_ms)}</div></div>
                <div className="rounded-xl border border-slate-800 bg-slate-950/70 p-3"><div className={tokens.smallLabel}>Steps</div><div className="mt-1 text-slate-100">{String(activeRun.summary?.passed ?? 0)} passed / {String(activeRun.summary?.failed ?? 0)} failed</div></div>
              </div>
              <ScrollArea className="mt-4 max-h-[52vh] pr-2">
                <div className="space-y-3">
                  {activeRun.results.map((step) => (
                    <div key={`${activeRun.run_id}-${step.name}`} className="rounded-2xl border border-slate-800 bg-slate-950/70 p-3">
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div className="min-w-0">
                          <div className="font-semibold text-slate-100">{step.name}</div>
                          <div className="mt-1 break-all font-mono text-xs text-slate-500">{step.cwd ? `${step.cwd}$ ` : ""}{step.command}</div>
                        </div>
                        <span className={["rounded-full border px-2 py-1 text-[11px] font-semibold", statusClass(step.ok)].join(" ")}>{step.ok ? "PASS" : "FAIL"}</span>
                      </div>
                      <div className="mt-2 text-xs text-slate-400">exit={step.exit_code ?? "-"} · {formatMs(step.duration_ms)}{step.timeout ? " · timeout" : ""}{step.error ? ` · ${step.error}` : ""}</div>
                      {step.stderr ? <pre className="mt-3 max-h-48 overflow-auto rounded-xl border border-slate-800 bg-black/40 p-3 text-xs text-rose-100 whitespace-pre-wrap">{step.stderr}</pre> : null}
                      {step.stdout ? <pre className="mt-3 max-h-48 overflow-auto rounded-xl border border-slate-800 bg-black/40 p-3 text-xs text-slate-200 whitespace-pre-wrap">{step.stdout}</pre> : null}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </>
          ) : (
            <div className="mt-4 rounded-2xl border border-slate-800 bg-slate-950/70 p-4 text-sm text-slate-400">
              Pick a workspace and run a preset. v1 stops at the first required failure to keep the signal clean.
            </div>
          )}
        </Panel>
      </div>

      <div className="flex min-h-0 flex-col gap-3">
        <Panel className="rounded-[1.45rem] p-4">
          <div className={tokens.smallLabel}>Selected preset</div>
          <h3 className="mt-1 text-lg font-semibold text-slate-100">{selectedPresetDetail?.name || selectedPreset}</h3>
          <div className="mt-3 space-y-2">
            {(selectedPresetDetail?.commands || []).map((command) => (
              <div key={`${command.name}-${command.cwd}`} className="rounded-xl border border-slate-800 bg-slate-950/70 p-3">
                <div className="text-sm font-semibold text-slate-100">{command.name}</div>
                <div className="mt-1 break-all font-mono text-xs text-slate-500">{command.cwd}$ {command.command}</div>
                <div className="mt-1 text-[11px] text-slate-500">timeout {command.timeout_s}s · {command.required ? "required" : "optional"}</div>
              </div>
            ))}
            {!selectedPresetDetail ? <div className="text-sm text-slate-500">Preset details unavailable.</div> : null}
          </div>
        </Panel>

        <Panel className="min-h-0 flex-1 rounded-[1.45rem] p-4">
          <div className={tokens.smallLabel}>History</div>
          <ScrollArea className="mt-3 max-h-[42vh] pr-2">
            <div className="space-y-2">
              {history.map((runItem) => (
                <button
                  key={runItem.run_id}
                  type="button"
                  className="w-full rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-left hover:border-cyan-400/40"
                  onClick={() => setLatest(runItem)}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-xs text-slate-300">{runItem.run_id}</span>
                    <span className={runItem.ok ? "text-xs font-semibold text-emerald-300" : "text-xs font-semibold text-rose-300"}>{runItem.ok ? "PASS" : "FAIL"}</span>
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{runItem.preset} · {formatMs(runItem.duration_ms)} · {formatDate(runItem.started_at)}</div>
                  <div className="mt-1 truncate text-[11px] text-slate-600">{runItem.workspace_path}</div>
                </button>
              ))}
              {history.length === 0 ? <div className="text-sm text-slate-500">No runs saved yet.</div> : null}
            </div>
          </ScrollArea>
        </Panel>
      </div>
    </div>
  );
}
