import { create } from "zustand";
import type { CapabilitiesResponse, OpencodeStatus, Session } from "./services/api";

interface AppState {
  capabilities: CapabilitiesResponse | null;
  opencodeStatus: OpencodeStatus | null;
  sessions: Session[];
  sidebarOpen: boolean;
  // LLM provider/model selection, shared across Settings and Chat so a
  // change in one is visible in the other without a page reload. Settings
  // remains the owner of provider detection/probing; this just holds the
  // currently-selected values. Sourced from localStorage on load (see
  // Settings.tsx LS_PROVIDER/LS_MODEL) so a reload doesn't reset it.
  llmProvider: string;
  llmModel: string;
  setCapabilities: (c: CapabilitiesResponse) => void;
  setOpencodeStatus: (s: OpencodeStatus) => void;
  setSessions: (s: Session[]) => void;
  toggleSidebar: () => void;
  setLlmProvider: (p: string) => void;
  setLlmModel: (m: string) => void;
}

export const useStore = create<AppState>((set) => ({
  capabilities: null,
  opencodeStatus: null,
  sessions: [],
  sidebarOpen: true,
  llmProvider: typeof localStorage !== "undefined" ? (localStorage.getItem("llm_provider") ?? "") : "",
  llmModel: typeof localStorage !== "undefined" ? (localStorage.getItem("llm_model") ?? "") : "",
  setCapabilities: (c) => set({ capabilities: c }),
  setOpencodeStatus: (s) => set({ opencodeStatus: s }),
  setSessions: (s) => set({ sessions: s }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
  setLlmProvider: (p) => set({ llmProvider: p }),
  setLlmModel: (m) => set({ llmModel: m }),
}));
