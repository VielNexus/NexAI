import React from "react";

export function StatusPill(props: { ok: boolean; label: string; compact?: boolean }) {
  return (
    <div
      className={[
        "agentx-status-pill inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em]",
        props.ok ? "agentx-status-pill--ok" : "agentx-status-pill--warn",
        props.compact ? "agentx-status-pill--compact" : "",
      ].join(" ")}
    >
      <span className="agentx-status-pill__signal" aria-hidden="true">
        <span className={["agentx-status-pill__dot h-2 w-2 rounded-full", props.ok ? "bg-emerald-300" : "bg-rose-300"].join(" ")} />
      </span>
      <span>{props.label}</span>
    </div>
  );
}
