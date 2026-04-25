import React, { useEffect, useId, useMemo, useRef, useState } from "react";

export type AgentXDropdownOption = {
  label: string;
  value: string;
  disabled?: boolean;
};

type Props = {
  label?: string;
  value: string;
  options: AgentXDropdownOption[];
  onChange: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  fitToOptions?: boolean;
};

export function AgentXDropdown({
  label,
  value,
  options,
  onChange,
  disabled = false,
  placeholder = "Select",
  className = "",
  fitToOptions = false,
}: Props) {
  const [open, setOpen] = useState(false);
  const [highlightedIndex, setHighlightedIndex] = useState(-1);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<HTMLDivElement | null>(null);
  const buttonRef = useRef<HTMLButtonElement | null>(null);
  const listboxId = useId();
  const enabledOptions = useMemo(() => options.filter((option) => !option.disabled), [options]);
  const selectedOption = options.find((option) => option.value === value);
  const fitWidthCh = useMemo(() => {
    const longestOption = options.reduce((longest, option) => Math.max(longest, option.label.length), 0);
    const longestText = Math.max(longestOption, placeholder.length, selectedOption?.label.length ?? 0);
    return Math.min(Math.max(longestText + 5, 18), 44);
  }, [options, placeholder, selectedOption?.label]);

  useEffect(() => {
    if (!open) return;
    const onPointerDown = (event: MouseEvent) => {
      if (!rootRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onPointerDown);
    return () => document.removeEventListener("mousedown", onPointerDown);
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const selectedEnabledIndex = enabledOptions.findIndex((option) => option.value === value);
    setHighlightedIndex(selectedEnabledIndex >= 0 ? selectedEnabledIndex : 0);
  }, [enabledOptions, open, value]);

  useEffect(() => {
    if (!open) return;
    const node = listRef.current?.querySelector<HTMLElement>(`[data-dropdown-index="${highlightedIndex}"]`);
    node?.scrollIntoView({ block: "nearest" });
  }, [highlightedIndex, open]);

  const commit = (nextValue: string) => {
    onChange(nextValue);
    setOpen(false);
    buttonRef.current?.focus();
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) return;
    if (!open && (event.key === "ArrowDown" || event.key === "ArrowUp" || event.key === "Enter" || event.key === " ")) {
      event.preventDefault();
      setOpen(true);
      return;
    }
    if (!open) return;
    if (event.key === "Escape") {
      event.preventDefault();
      setOpen(false);
      buttonRef.current?.focus();
      return;
    }
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setHighlightedIndex((current) => {
        if (enabledOptions.length === 0) return -1;
        return current < enabledOptions.length - 1 ? current + 1 : 0;
      });
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      setHighlightedIndex((current) => {
        if (enabledOptions.length === 0) return -1;
        return current > 0 ? current - 1 : enabledOptions.length - 1;
      });
      return;
    }
    if (event.key === "Enter") {
      event.preventDefault();
      const option = enabledOptions[highlightedIndex];
      if (option) commit(option.value);
    }
  };

  return (
    <div
      ref={rootRef}
      className={[
        "agentx-dropdown",
        className,
        open ? "agentx-dropdown--open" : "",
        disabled ? "agentx-dropdown--disabled" : "",
        fitToOptions ? "agentx-dropdown--fit" : "",
      ].join(" ").trim()}
      style={fitToOptions ? ({ ["--agentx-dropdown-fit-ch" as string]: `${fitWidthCh}ch` } as React.CSSProperties) : undefined}
    >
      {label ? <div className="agentx-dropdown__label">{label}</div> : null}
      <button
        ref={buttonRef}
        type="button"
        className="agentx-dropdown__trigger"
        onClick={() => {
          if (!disabled) setOpen((current) => !current);
        }}
        onKeyDown={onKeyDown}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listboxId}
        disabled={disabled}
      >
        <span className={selectedOption ? "agentx-dropdown__value" : "agentx-dropdown__placeholder"}>
          {selectedOption?.label ?? placeholder}
        </span>
        <span className="agentx-dropdown__chevron" aria-hidden="true">
          <svg viewBox="0 0 20 20" fill="none" className="h-4 w-4">
            <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </span>
      </button>
      {open ? (
        <div ref={listRef} id={listboxId} className="agentx-dropdown__menu" role="listbox" aria-label={label ?? placeholder}>
          {options.map((option) => {
            const enabledIndex = enabledOptions.findIndex((item) => item.value === option.value);
            const isSelected = option.value === value;
            const isHighlighted = enabledIndex >= 0 && enabledIndex === highlightedIndex;
            return (
              <button
                key={option.value}
                type="button"
                role="option"
                aria-selected={isSelected}
                data-dropdown-index={enabledIndex >= 0 ? enabledIndex : undefined}
                disabled={option.disabled}
                className={[
                  "agentx-dropdown__option",
                  isSelected ? "agentx-dropdown__option--selected" : "",
                  isHighlighted ? "agentx-dropdown__option--highlighted" : "",
                  option.disabled ? "agentx-dropdown__option--disabled" : "",
                ].join(" ").trim()}
                onMouseEnter={() => {
                  if (!option.disabled && enabledIndex >= 0) setHighlightedIndex(enabledIndex);
                }}
                onClick={() => {
                  if (!option.disabled) commit(option.value);
                }}
              >
                <span>{option.label}</span>
                {isSelected ? <span className="agentx-dropdown__check">•</span> : null}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}
