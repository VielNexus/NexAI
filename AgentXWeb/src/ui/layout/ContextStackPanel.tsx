import React from "react";

type ContextItem = {
  label: string;
  value: React.ReactNode;
  tone?: "ok" | "warn" | "bad" | "idle";
};

type Props = {
  threadTitle?: string | null;
  projectName?: string | null;
  provider?: string | null;
  model?: string | null;
  apiOk: boolean;
  endpointStatus?: string | null;
  memoryEnabled?: boolean;
  draftOpen?: boolean;
  attachedCount?: number;
  retrievedCount?: number;
  gitStatus?: "clean" | "changed" | "unknown";
};

function toneClass(tone: ContextItem["tone"] = "idle") {
  if (tone === "ok") return "agentx-context-stack-dot--ok";
  if (tone === "warn") return "agentx-context-stack-dot--warn";
  if (tone === "bad") return "agentx-context-stack-dot--bad";
  return "agentx-context-stack-dot--idle";
}

export function ContextStackPanel(props: Props) {
  const items: ContextItem[] = [
    { label: "Active thread", value: props.threadTitle || "No chat selected", tone: props.threadTitle ? "ok" : "idle" },
    { label: "Project", value: props.projectName || "All chats", tone: props.projectName ? "ok" : "idle" },
    { label: "Model route", value: `${props.provider || "unknown"}${props.model ? `:${props.model}` : ""}`, tone: props.apiOk ? "ok" : "bad" },
    { label: "Endpoint", value: props.endpointStatus || (props.apiOk ? "reachable" : "offline"), tone: props.apiOk ? "ok" : "bad" },
    { label: "Project memory", value: props.memoryEnabled ? "ready" : "local", tone: props.memoryEnabled ? "ok" : "idle" },
    { label: "Draft workspace", value: props.draftOpen ? "open" : "standby", tone: props.draftOpen ? "warn" : "idle" },
    { label: "Attachments", value: String(props.attachedCount || 0), tone: (props.attachedCount || 0) > 0 ? "warn" : "idle" },
    { label: "Retrieved context", value: String(props.retrievedCount || 0), tone: (props.retrievedCount || 0) > 0 ? "ok" : "idle" },
  ];

  return (
    <aside className="agentx-context-stack" aria-label="Context stack">
      <div className="agentx-context-stack-header">
        <div>
          <div className="agentx-context-stack-eyebrow">Context Stack</div>
          <div className="agentx-context-stack-title">What AgentX is carrying</div>
        </div>
      </div>
      <div className="agentx-context-stack-list">
        {items.map((item) => (
          <div key={item.label} className="agentx-context-stack-item">
            <span className={["agentx-context-stack-dot", toneClass(item.tone)].join(" ")} aria-hidden="true" />
            <div className="min-w-0">
              <div className="agentx-context-stack-label">{item.label}</div>
              <div className="agentx-context-stack-value">{item.value}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="agentx-context-stack-note">
        Phase 2 shell is live. The next pass wires this panel into scoped project memory and task reflection.
      </div>
    </aside>
  );
}
