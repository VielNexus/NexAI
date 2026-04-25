import { API_BASE } from "./api/client";

export type AgentXSettings = {
  showInspector: boolean;
  inspectorWindow: boolean;
  theme: "win11-light";
  chatProvider: "stub" | "openai" | "ollama";
  chatModel: string;
};

export const DEFAULT_SETTINGS: AgentXSettings = {
  showInspector: false,
  inspectorWindow: false,
  theme: "win11-light",
  chatProvider: "stub",
  chatModel: "stub",
};

export const THREAD_TITLE_DEFAULT = "New thread";
export const THREAD_TITLE_MAX = 64;
export const THREAD_TITLE_WORD_LIMIT = 8;

const STORAGE_KEY = "agentx.ui.settings";

function readLocalSettings(): AgentXSettings {
  if (typeof window === "undefined") return DEFAULT_SETTINGS;
  try {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return DEFAULT_SETTINGS;
    const parsed = JSON.parse(stored);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function writeLocalSettings(settings: AgentXSettings) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch {
    // ignore
  }
}

export async function loadSettings(): Promise<AgentXSettings> {
  try {
    const res = await fetch(`${API_BASE}/v1/settings`);
    if (!res.ok) {
      throw new Error("Failed to load backend settings");
    }
    const data = await res.json();
    const normalized: AgentXSettings = { ...DEFAULT_SETTINGS, ...data };
    writeLocalSettings(normalized);
    return normalized;
  } catch {
    return readLocalSettings();
  }
}

export async function saveSettings(settings: AgentXSettings): Promise<void> {
  const normalized: AgentXSettings = { ...DEFAULT_SETTINGS, ...settings };
  writeLocalSettings(normalized);
  try {
    await fetch(`${API_BASE}/v1/settings`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(normalized),
    });
  } catch {
    // fallback already in local storage
  }
}
