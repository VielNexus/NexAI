import { type LayoutSettings, normalizeLayoutSettings, type AgentXSettings } from "../api/client";

const PENDING_LAYOUT_KEY = "agentxweb.pendingLayout.v1";
const PENDING_LAYOUT_EVENT = "agentxweb:pending-layout-changed";

export type PendingLayoutSave = {
  layout: Required<LayoutSettings>;
  updatedAt: number;
};

export function loadPendingLayoutSave(): PendingLayoutSave | null {
  try {
    const raw = localStorage.getItem(PENDING_LAYOUT_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<PendingLayoutSave> | null;
    if (!parsed || typeof parsed !== "object") return null;
    return {
      layout: normalizeLayoutSettings(parsed.layout),
      updatedAt: typeof parsed.updatedAt === "number" ? parsed.updatedAt : Date.now(),
    };
  } catch {
    return null;
  }
}

export function savePendingLayoutSave(layout: LayoutSettings): PendingLayoutSave {
  const pending: PendingLayoutSave = {
    layout: normalizeLayoutSettings(layout),
    updatedAt: Date.now(),
  };
  localStorage.setItem(PENDING_LAYOUT_KEY, JSON.stringify(pending));
  window.dispatchEvent(new Event(PENDING_LAYOUT_EVENT));
  return pending;
}

export function clearPendingLayoutSave(): void {
  localStorage.removeItem(PENDING_LAYOUT_KEY);
  window.dispatchEvent(new Event(PENDING_LAYOUT_EVENT));
}

export function applyPendingLayoutToSettings(settings: AgentXSettings, pending: PendingLayoutSave | null): AgentXSettings {
  if (!pending) return settings;
  return {
    ...settings,
    layout: pending.layout,
  };
}

export function pendingLayoutChangedEventName(): string {
  return PENDING_LAYOUT_EVENT;
}
