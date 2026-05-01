import { create } from "zustand";
import type { CapabilitiesResponse, OpencodeStatus, Session } from "./services/api";

interface AppState {
  capabilities: CapabilitiesResponse | null;
  opencodeStatus: OpencodeStatus | null;
  sessions: Session[];
  sidebarOpen: boolean;
  setCapabilities: (c: CapabilitiesResponse) => void;
  setOpencodeStatus: (s: OpencodeStatus) => void;
  setSessions: (s: Session[]) => void;
  toggleSidebar: () => void;
}

export const useStore = create<AppState>((set) => ({
  capabilities: null,
  opencodeStatus: null,
  sessions: [],
  sidebarOpen: true,
  setCapabilities: (c) => set({ capabilities: c }),
  setOpencodeStatus: (s) => set({ opencodeStatus: s }),
  setSessions: (s) => set({ sessions: s }),
  toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
}));
