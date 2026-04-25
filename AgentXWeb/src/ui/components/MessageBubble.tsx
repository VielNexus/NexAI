import React from "react";

type Props = React.PropsWithChildren<{
  role: "user" | "assistant" | "system";
  compactTop?: boolean;
  compactBottom?: boolean;
}>;

export function MessageBubble({ role, compactTop = false, compactBottom = false, children }: Props) {
  return (
    <div
      className={[
        "agentx-message-bubble",
        role === "assistant"
          ? "agentx-message-bubble--assistant"
          : role === "user"
            ? "agentx-message-bubble--user"
            : "agentx-message-bubble--system",
        compactTop ? "agentx-message-bubble--compact" : "",
        compactBottom ? "agentx-message-bubble--compact-bottom" : "",
      ].join(" ")}
    >
      {children}
    </div>
  );
}
