#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_workspaces() -> None:
    path = ROOT / "AgentXWeb/public/workspaces.html"
    text = path.read_text()

    css_marker = "  .historyActions button { width: auto !important; }\n"
    css_add = css_marker + """
  .capPanel {
    border: 1px solid rgba(34, 211, 238, 0.18);
    background: rgba(2, 6, 23, 0.58);
    border-radius: 16px;
    padding: 10px;
    margin: 10px 0;
  }
  .capHeader { display:flex; align-items:center; justify-content:space-between; gap:10px; margin-bottom:8px; }
  .capTitle { color:#e2e8f0; font-weight:800; font-size:13px; }
  .capGrid { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:8px; }
  .capItem { border:1px solid rgba(148,163,184,.16); background:rgba(15,23,42,.62); border-radius:12px; padding:8px; min-width:0; }
  .capItem strong { display:block; color:#f8fafc; font-size:13px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .capItem span { display:block; color:#8fa3bd; font-size:11px; margin-top:3px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
  .capItem.ok { border-color:rgba(16,185,129,.35); background:rgba(6,78,59,.16); }
  .capItem.warn { border-color:rgba(245,158,11,.35); background:rgba(120,53,15,.16); }
  .capItem.bad { border-color:rgba(244,63,94,.35); background:rgba(127,29,29,.16); }
  .capActions { display:flex; gap:8px; flex-wrap:wrap; }
  .capActions button { width:auto !important; }
  @media(max-width:1200px){ .capGrid { grid-template-columns:repeat(3,minmax(0,1fr)); } }
  @media(max-width:760px){ .capGrid { grid-template-columns:1fr; } }
"""
    if ".capPanel" not in text:
        text = text.replace(css_marker, css_add, 1)

    html_marker = """        <div class="tabs">
          <button class="tab active" data-tab="view">View</button>
          <button class="tab" data-tab="patch">Patch Preview</button>
          <button class="tab" data-tab="compare">Compare Source</button>
          <button class="tab" data-tab="report">Report</button>
          <button class="tab" data-tab="history">History</button>
        </div>
      </div>

      <div style="min-height:0; overflow:hidden;">
"""
    html_add = """        <div class="tabs">
          <button class="tab active" data-tab="view">View</button>
          <button class="tab" data-tab="patch">Patch Preview</button>
          <button class="tab" data-tab="compare">Compare Source</button>
          <button class="tab" data-tab="report">Report</button>
          <button class="tab" data-tab="history">History</button>
        </div>
      </div>

      <div id="playgroundStatusPanel" class="capPanel">
        <div class="capHeader">
          <div>
            <div class="capTitle">Playground Status</div>
            <div class="sub">Workspace readiness, patch state, validation, and history at a glance.</div>
          </div>
          <div class="capActions">
            <button id="refreshPlaygroundStatusBtn" type="button">Refresh status</button>
            <button id="openReportViewerBtn" type="button">Report viewer</button>
          </div>
        </div>
        <div class="capGrid">
          <div id="capWorkspace" class="capItem warn"><strong>No workspace</strong><span>Select an upload</span></div>
          <div id="capTree" class="capItem warn"><strong>Tree idle</strong><span>No files loaded</span></div>
          <div id="capFile" class="capItem warn"><strong>No file</strong><span>Open a source file</span></div>
          <div id="capProposal" class="capItem warn"><strong>No proposal</strong><span>Patch preview empty</span></div>
          <div id="capValidation" class="capItem warn"><strong>Not validated</strong><span>No validation run yet</span></div>
          <div id="capHistory" class="capItem warn"><strong>No history</strong><span>No patch history loaded</span></div>
        </div>
      </div>

      <div style="min-height:0; overflow:hidden;">
"""
    if 'id="playgroundStatusPanel"' not in text:
        if html_marker not in text:
            raise SystemExit("Could not find tabs/content marker in workspaces.html")
        text = text.replace(html_marker, html_add, 1)

    state_marker = "const state = { uploads: [], selected: null, tree: [], file: null, report: '', currentTab: 'view' };\n"
    state_add = state_marker + "window.agentxWorkspaceState = () => state;\n"
    if "window.agentxWorkspaceState" not in text:
        if state_marker not in text:
            raise SystemExit("Could not find state marker in workspaces.html")
        text = text.replace(state_marker, state_add, 1)

    status_script = r"""
<script id="agentx-playground-status-panel">
(function () {
  function byId(id) { return document.getElementById(id); }
  function getState() {
    try {
      if (typeof window.agentxWorkspaceState === "function") return window.agentxWorkspaceState();
      return state;
    } catch {
      return {};
    }
  }
  function setCap(id, title, subtitle, kind) {
    const el = byId(id);
    if (!el) return;
    el.className = "capItem " + (kind || "warn");
    el.innerHTML = `<strong>${escapeLocal(title)}</strong><span>${escapeLocal(subtitle)}</span>`;
  }
  function escapeLocal(value) {
    const s = String(value ?? "");
    if (typeof esc === "function") return esc(s);
    return s.replace(/[&<>]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[c]));
  }
  function proposalStats(st) {
    const proposal = byId("proposedContent");
    const value = proposal ? proposal.value : "";
    const current = st.file ? String(st.file.content || "") : "";
    if (!value.trim()) return { title: "No proposal", sub: "Patch preview empty", kind: "warn" };
    const proposalLines = value.split("\n").length;
    const currentLines = current.split("\n").length;
    const changed = Math.abs(proposalLines - currentLines);
    const same = st.file && value === current;
    return {
      title: same ? "Proposal matches" : `${proposalLines} lines`,
      sub: same ? "No content changes yet" : `${changed} net line change(s)`,
      kind: same ? "warn" : "ok",
    };
  }
  function validationStats() {
    const box = byId("validationBox");
    if (!box) return { title: "Validation unknown", sub: "Validation box missing", kind: "warn" };
    const text = (box.textContent || "").trim();
    if (box.classList.contains("ok")) return { title: "Validation pass", sub: text.split("\n")[0] || "Passed", kind: "ok" };
    if (box.classList.contains("bad")) return { title: "Validation fail", sub: text.split("\n")[0] || "Failed", kind: "bad" };
    return { title: "Not validated", sub: text.split("\n")[0] || "No validation run yet", kind: "warn" };
  }
  function historyStats() {
    const root = byId("patchHistory");
    if (!root) return { title: "History unknown", sub: "History panel missing", kind: "warn" };
    const count = root.querySelectorAll(".historyCard").length;
    if (count > 0) return { title: `${count} patch(es)`, sub: "Patch history loaded", kind: "ok" };
    return { title: "No history", sub: "No patch history loaded", kind: "warn" };
  }
  function update() {
    const st = getState();
    const selected = st.selected || null;
    const selectedId = selected ? (selected.project_id || selected.id || "workspace") : "";
    setCap("capWorkspace", selected ? selectedId : "No workspace", selected ? (selected.thread_id ? "thread linked" : "upload workspace") : "Select an upload", selected ? "ok" : "warn");

    const treeCount = Array.isArray(st.tree) ? st.tree.length : 0;
    setCap("capTree", treeCount ? `${treeCount} entries` : "Tree idle", treeCount ? "File tree loaded" : "No files loaded", treeCount ? "ok" : "warn");

    const file = st.file || null;
    setCap("capFile", file?.path || "No file", file ? `${file.size ?? 0} bytes${file.truncated ? " - truncated" : ""}` : "Open a source file", file ? "ok" : "warn");

    const proposal = proposalStats(st);
    setCap("capProposal", proposal.title, proposal.sub, proposal.kind);

    const validation = validationStats();
    setCap("capValidation", validation.title, validation.sub, validation.kind);

    const history = historyStats();
    setCap("capHistory", history.title, history.sub, history.kind);
  }

  function wire() {
    byId("refreshPlaygroundStatusBtn")?.addEventListener("click", update);
    byId("openReportViewerBtn")?.addEventListener("click", () => { window.location.href = "/workbench-report-viewer.html"; });
    byId("proposedContent")?.addEventListener("input", update);
    byId("treeFilter")?.addEventListener("input", update);
  }

  window.agentxUpdatePlaygroundStatus = update;
  wire();
  update();
  setInterval(update, 1000);
})();
</script>

"""
    if 'id="agentx-playground-status-panel"' not in text:
        text = text.replace("</body>", status_script + "</body>", 1)

    path.write_text(text)


def write_doc() -> None:
    path = ROOT / "readme/README_V15_CODING_PLAYGROUND.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = """# AgentX V15 - Coding Playground Completion

V15 focuses on finishing and polishing the existing Workspaces coding playground instead of rebuilding it.

## Existing Foundation

AgentX already has:

- workspace upload/import UI
- file tree loading
- file inspector
- patch preview
- sandbox-only apply flow
- validation box
- patch history
- report viewer launcher
- AgentX patch import hooks

## V15 Slice 1

Adds a Playground Status panel to `AgentXWeb/public/workspaces.html`.

The panel summarizes:

- selected workspace
- loaded tree entries
- current file
- proposal/patch state
- validation status
- patch history count
- report viewer access

## Validation

```bash
python3 -m compileall AgentX/agentx apps/api/agentx_api apps/api/tests
./scripts/smoke-test-v10.sh
```

Then open Workspaces and verify the Playground Status panel updates as you select a workspace, open a file, edit the proposal, validate, and view history.
"""
    path.write_text(text)


def main() -> None:
    patch_workspaces()
    write_doc()
    print("Applied AgentX V15 playground status panel.")


if __name__ == "__main__":
    main()
