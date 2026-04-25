import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CodeBlock } from "./CodeBlock";

type Props = {
  content: string;
};

export function MessageContent({ content }: Props) {
  return (
    <div className="agentx-message-prose">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a(props) {
            return <a {...props} className="agentx-message-prose__link" target="_blank" rel="noreferrer" />;
          },
          code({ className, children, ...props }) {
            const text = String(children).replace(/\n$/, "");
            const match = /language-([\w-]+)/.exec(className || "");
            const isBlock = Boolean(match) || text.includes("\n");
            if (!isBlock) {
              return (
                <code {...props} className="agentx-message-prose__inline-code">
                  {children}
                </code>
              );
            }
            return <CodeBlock code={text} language={match?.[1]} />;
          },
          pre({ children }) {
            return <>{children}</>;
          },
          blockquote(props) {
            return <blockquote {...props} className="agentx-message-prose__blockquote" />;
          },
          ul(props) {
            return <ul {...props} className="agentx-message-prose__list agentx-message-prose__list--unordered" />;
          },
          ol(props) {
            return <ol {...props} className="agentx-message-prose__list agentx-message-prose__list--ordered" />;
          },
          table(props) {
            return (
              <div className="agentx-message-prose__table-wrap">
                <table {...props} className="agentx-message-prose__table" />
              </div>
            );
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
