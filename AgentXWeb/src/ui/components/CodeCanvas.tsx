import React, { useEffect, useMemo, useRef, useState } from "react";
import { tokens } from "../tokens";
import type { CodeCanvasLanguage, CodeCanvasState } from "../codeCanvas";
import { languageAccentClass, languageLabel } from "../codeCanvas";

type Props = {
  canvas: CodeCanvasState;
  onUpdate: (update: Partial<CodeCanvasState>) => void;
  onClose: () => void;
  onSendSelection: (payload: { scope: "selection" | "document"; content: string; language: CodeCanvasLanguage }) => void;
};

export function CodeCanvas({ canvas, onUpdate, onClose, onSendSelection }: Props) {
  const editorRef = useRef<HTMLTextAreaElement | null>(null);
  const [selection, setSelection] = useState({ start: 0, end: 0 });
  const [copied, setCopied] = useState(false);
  const selectedText = useMemo(() => {
    if (selection.end <= selection.start) return "";
    return canvas.content.slice(selection.start, selection.end);
  }, [canvas.content, selection.end, selection.start]);

  useEffect(() => {
    if (!copied) return;
    const id = window.setTimeout(() => setCopied(false), 1400);
    return () => window.clearTimeout(id);
  }, [copied]);

  const syncSelection = () => {
    const node = editorRef.current;
    if (!node) return;
    setSelection({ start: node.selectionStart, end: node.selectionEnd });
  };

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(selectedText || canvas.content);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  return (
    <aside
      className={[
        "agentx-code-canvas",
        languageAccentClass(canvas.language),
        canvas.viewMode === "fullscreen" ? "agentx-code-canvas--fullscreen" : "agentx-code-canvas--docked",
      ].join(" ")}
    >
      <div className="agentx-code-canvas__header">
        <div className="agentx-code-canvas__identity">
          <div>
            <div className="agentx-code-canvas__eyebrow">Code Canvas</div>
            <div className="agentx-code-canvas__title">{canvas.title}</div>
          </div>
          <span className="agentx-code-canvas__language">{languageLabel(canvas.language)}</span>
        </div>
        <div className="agentx-code-canvas__header-actions">
          <button className={tokens.buttonUtility} onClick={() => void copyCode()}>
            {copied ? "Copied" : "Copy"}
          </button>
          <button
            className={tokens.buttonUtility}
            onClick={() => onSendSelection({ scope: selectedText ? "selection" : "document", content: selectedText || canvas.content, language: canvas.language })}
            disabled={!canvas.content.trim()}
          >
            Send to chat
          </button>
          <button
            className={tokens.buttonUtility}
            onClick={() => onUpdate({ viewMode: canvas.viewMode === "fullscreen" ? "docked" : "fullscreen" })}
          >
            {canvas.viewMode === "fullscreen" ? "Dock" : "Expand"}
          </button>
          <button className={tokens.buttonUtility} onClick={onClose}>
            Close
          </button>
        </div>
      </div>

      <div className="agentx-code-canvas__meta">
        <span>{canvas.isDirty ? "Edited locally" : "Synced from assistant output"}</span>
        <span>{selectedText ? `${selectedText.split("\n").length} lines selected` : `${canvas.content.split("\n").length} lines`}</span>
      </div>

      <div className="agentx-code-canvas__editor-wrap">
        <textarea
          ref={editorRef}
          className={[tokens.textarea, "agentx-code-canvas__editor"].join(" ")}
          value={canvas.content}
          onChange={(event) => onUpdate({ content: event.target.value, isDirty: true })}
          onSelect={syncSelection}
          onKeyUp={syncSelection}
          onMouseUp={syncSelection}
          spellCheck={false}
          placeholder="Code output will appear here"
        />
      </div>
    </aside>
  );
}
