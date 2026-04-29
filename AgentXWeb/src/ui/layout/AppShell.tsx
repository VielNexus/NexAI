import React from "react";

type Props = {
  top?: React.ReactNode;
  rail?: React.ReactNode;
  sidebar?: React.ReactNode;
  main: React.ReactNode;
  context?: React.ReactNode;
};

export function AppShell({ top, rail, sidebar, main, context }: Props) {
  return (
    <div className="agentx-app-shell">
      {top ? <div className="agentx-app-shell__top">{top}</div> : null}
      <div className="agentx-app-shell__body">
        {rail ? <div className="agentx-app-shell__rail">{rail}</div> : null}
        {sidebar ? <div className="agentx-app-shell__sidebar">{sidebar}</div> : null}
        <main className="agentx-app-shell__main">{main}</main>
        {context ? <div className="agentx-app-shell__context">{context}</div> : null}
      </div>
    </div>
  );
}
