import React from "react";
import { tokens } from "../tokens";

export function Panel(props: React.PropsWithChildren<{ className?: string }>) {
  return <section className={["agentx-panel", tokens.panel, props.className].filter(Boolean).join(" ")}>{props.children}</section>;
}
