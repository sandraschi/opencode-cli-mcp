import type { ReactNode } from "react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Terminal,
  LayoutDashboard,
  ListTree,
  FolderKanban,
  PanelRightOpen,
  PanelRightClose,
  AppWindow,
  Box,
  MessageSquareText,
  BookOpen,
  Settings2,
  Activity,
  Code2,
  Puzzle,
  ScrollText,
  Sun,
  Moon,
  Plug,
  Network,
  Archive,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "./store";
import { useZoom } from "./lib/use-zoom";
import { BackendStatus } from "./components/BackendStatus";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/sessions", label: "Sessions", icon: ListTree },
  { path: "/depot", label: "Depot", icon: Archive },
  { path: "/projects", label: "Projects", icon: FolderKanban },
  { path: "/tools", label: "Tools", icon: Terminal },
  { path: "/oc-tools", label: "OC Tools", icon: Puzzle },
  { path: "/apps", label: "Apps Hub", icon: AppWindow },
  { path: "/mcpb", label: "MCPB Install", icon: Box },
  { path: "/mcp-servers", label: "MCP Servers", icon: Network },
  { path: "/plugins", label: "Plugins", icon: Plug },
  { path: "/chat", label: "Chat", icon: MessageSquareText },
  { path: "/help", label: "Help", icon: BookOpen },
  { path: "/settings", label: "Settings", icon: Settings2 },
  { path: "/status", label: "Status", icon: Activity },
  { path: "/api-docs", label: "API Docs", icon: Code2 },
  { path: "/logs", label: "Logs", icon: ScrollText },
];

// EXPERIMENTAL light mode (invert hack). Not fleet standard — see index.css.
// Toggling `.dark` off the root flips the invert filter; persisted so the
// choice survives reloads. Delete this + the CSS block to revert.
const THEME_KEY = "ocmcp-light-mode";

function useExperimentalTheme() {
  const [light, setLight] = useState(() => {
    try {
      return localStorage.getItem(THEME_KEY) === "1";
    } catch {
      return false;
    }
  });

  useEffect(() => {
    document.documentElement.classList.toggle("dark", !light);
    try {
      localStorage.setItem(THEME_KEY, light ? "1" : "0");
    } catch {
      // ignore storage errors
    }
  }, [light]);

  return { light, toggle: () => setLight((v) => !v) };
}

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const sidebarOpen = useStore((s) => s.sidebarOpen);
  const toggleSidebar = useStore((s) => s.toggleSidebar);
  const { zoom } = useZoom();
  const { light, toggle } = useExperimentalTheme();

  return (
    <div className="flex h-screen overflow-hidden">
      <AnimatePresence mode="wait">
        {sidebarOpen && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 240, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="flex-shrink-0 bg-surface-light border-r border-surface-border overflow-hidden"
          >
            <div className="flex flex-col h-full p-4">
              <div className="flex items-center gap-2 mb-6 flex-shrink-0">
                <Terminal className="w-6 h-6 text-accent" />
                <span className="font-semibold text-sm">opencode-cli-mcp</span>
              </div>
              <nav className="flex flex-col gap-0.5 flex-1 overflow-y-auto min-h-0 pr-1">
                {navItems.map((item) => {
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                        active ? "bg-accent/10 text-accent" : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
                      }`}
                      title={item.label}
                    >
                      <item.icon className="w-4 h-4" />
                      {item.label}
                    </Link>
                  );
                })}
              </nav>
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-12 flex-shrink-0 border-b border-surface-border flex items-center px-4 gap-3 bg-surface-light/50 backdrop-blur-sm">
          <button
            type="button"
            onClick={toggleSidebar}
            className="text-zinc-400 hover:text-zinc-200 transition-colors"
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
          </button>
          <span className="text-sm text-zinc-500">opencode-cli-mcp</span>
          <div className="flex-1" />
          <button
            type="button"
            onClick={toggle}
            className="text-zinc-400 hover:text-zinc-200 transition-colors"
            title={light ? "Switch to dark (experimental light mode)" : "Switch to light (experimental, ugly)"}
            aria-label="Toggle light mode (experimental)"
          >
            {light ? <Moon className="w-4 h-4" /> : <Sun className="w-4 h-4" />}
          </button>
          <BackendStatus />
          <span className="text-xs text-zinc-600 ml-2" title={`Zoom ${Math.round(zoom * 100)}%`}>
            {Math.round(zoom * 100)}%
          </span>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
