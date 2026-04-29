import React from "react";

export type DeckStatusState = "ok" | "warn" | "bad" | "idle";

export type DeckStatusItem = {
  label: string;
  value?: string | null;
  state?: DeckStatusState;
  title?: string;
};

type Props = {
  title?: string;
  subtitle?: string;
  items: DeckStatusItem[];
  rightSlot?: React.ReactNode;
};

function stateClass(state: DeckStatusState = "idle") {
  if (state === "ok") return "agentx-deck-dot--ok";
  if (state === "warn") return "agentx-deck-dot--warn";
  if (state === "bad") return "agentx-deck-dot--bad";
  return "agentx-deck-dot--idle";
}

export function TopStatusBar({ title = "AgentX Command Deck", subtitle = "Local-first AI workspace", items, rightSlot }: Props) {
  return (
    <header className="agentx-command-deck-topbar">
      <div className="agentx-command-deck-brand">
        <div className="agentx-command-deck-mark">AX</div>
        <div className="min-w-0">
          <div className="agentx-command-deck-title">{title}</div>
          <div className="agentx-command-deck-subtitle">{subtitle}</div>
        </div>
      </div>
      <div className="agentx-command-deck-statuses" aria-label="AgentX system status">
        {items.map((item) => (
          <div key={item.label} className="agentx-command-deck-status" title={item.title || `${item.label}: ${item.value || "unknown"}`}>
            <span className={["agentx-deck-dot", stateClass(item.state)].join(" ")} aria-hidden="true" />
            <span className="agentx-command-deck-status-label">{item.label}</span>
            {item.value ? <span className="agentx-command-deck-status-value">{item.value}</span> : null}
          </div>
        ))}
      </div>
      {rightSlot ? <div className="agentx-command-deck-right">{rightSlot}</div> : null}
    </header>
  );
}
