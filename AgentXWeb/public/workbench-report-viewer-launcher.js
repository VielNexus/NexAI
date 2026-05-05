(function () {
  "use strict";

  if (window.__AGENTX_V12_REPORT_VIEWER_LAUNCHER__) return;
  window.__AGENTX_V12_REPORT_VIEWER_LAUNCHER__ = true;

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn, { once: true });
    } else {
      fn();
    }
  }

  function addStyles() {
    if (document.getElementById("agentx-v12-report-viewer-launcher-css")) return;
    const style = document.createElement("style");
    style.id = "agentx-v12-report-viewer-launcher-css";
    style.textContent = `
      .agentx-v12-report-viewer-launcher {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 9999;
        display: flex;
        align-items: center;
        gap: 10px;
        border: 1px solid rgba(34, 211, 238, 0.42);
        border-radius: 999px;
        padding: 10px 13px;
        color: #e0fbff;
        background: rgba(2, 6, 23, 0.88);
        box-shadow: 0 20px 60px rgba(0, 0, 0, 0.45), 0 0 35px rgba(34, 211, 238, 0.14);
        text-decoration: none;
        font: 800 12px/1.1 ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;
        backdrop-filter: blur(10px);
      }
      .agentx-v12-report-viewer-launcher:hover {
        border-color: rgba(34, 211, 238, 0.85);
        background: rgba(8, 47, 73, 0.92);
      }
      .agentx-v12-report-viewer-launcher__icon {
        display: grid;
        place-items: center;
        width: 25px;
        height: 25px;
        border-radius: 999px;
        color: #03131d;
        background: linear-gradient(135deg, #22d3ee, #a78bfa);
      }
      .agentx-v12-report-viewer-launcher__text {
        display: grid;
        gap: 2px;
      }
      .agentx-v12-report-viewer-launcher__text small {
        color: #8fa3bd;
        font-size: 10px;
        font-weight: 700;
      }
      @media (max-width: 720px) {
        .agentx-v12-report-viewer-launcher {
          left: 12px;
          right: 12px;
          justify-content: center;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function addLauncher() {
    if (document.querySelector(".agentx-v12-report-viewer-launcher")) return;
    addStyles();
    const link = document.createElement("a");
    link.className = "agentx-v12-report-viewer-launcher";
    link.href = "/workbench-report-viewer.html";
    link.title = "Open the V12 Workbench Report Viewer";
    link.innerHTML = `
      <span class="agentx-v12-report-viewer-launcher__icon">↗</span>
      <span class="agentx-v12-report-viewer-launcher__text">
        <span>Report Viewer</span>
        <small>V12 workspace reports</small>
      </span>
    `;
    document.body.appendChild(link);
  }

  ready(addLauncher);
})();
