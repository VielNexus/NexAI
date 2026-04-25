import React from "react";

type Props = {
  compact?: boolean;
};

export function BrandBadge({ compact = false }: Props) {
  return (
    <div className={["agentx-badge", compact ? "agentx-badge--compact" : ""].join(" ").trim()}>
      <span className="agentx-badge__dot" />
      <div className="min-w-0">
        <div className="agentx-badge__title">AgentX</div>
        {!compact ? <div className="agentx-badge__subtitle">Local AI control surface</div> : null}
      </div>
    </div>
  );
}
