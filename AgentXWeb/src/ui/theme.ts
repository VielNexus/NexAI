export const theme = {
  radius: {
    panel: "rounded-[1.35rem]",
    control: "rounded-xl",
    pill: "rounded-full",
  },
  shell: {
    app: "agentx-shell relative h-full w-full",
    mainPanel: "agentx-main-panel flex min-h-0 min-w-0 flex-col p-4",
    topBar: "agentx-topbar flex items-center justify-between gap-3 border-b pb-4",
    feed: "agentx-feed min-h-0 flex-1 overflow-auto rounded-[1.45rem] border p-4",
    composer: "agentx-composer mt-4 flex flex-none flex-col gap-3 rounded-[1.45rem] border p-4",
  },
  controls: {
    button: "agentx-button agentx-button--primary",
    secondaryButton: "agentx-button agentx-button--secondary",
    utilityButton: "agentx-button agentx-button--utility",
    dangerButton: "agentx-button agentx-button--danger",
    toggle: "agentx-toggle",
    input: "agentx-input",
    inputCompact: "agentx-input agentx-input--compact",
    inputNumber: "agentx-input agentx-input--compact agentx-input--number",
    select: "agentx-input agentx-input--compact",
    textarea: "agentx-textarea",
  },
  copy: {
    eyebrow: "text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-100/55",
    title: "text-sm font-semibold text-slate-50",
    muted: "text-xs text-slate-500",
    fieldLabel: "agentx-field-label",
    helper: "agentx-helper-text",
    warning: "agentx-helper-text agentx-helper-text--warning",
  },
} as const;
