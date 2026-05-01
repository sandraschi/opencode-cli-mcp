import type { ReactNode } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  Terminal,
  LayoutDashboard,
  ListTree,
  PanelRightOpen,
  PanelRightClose,
  AppWindow,
  MessageSquareText,
  BookOpen,
  Settings2,
  Activity,
  Code2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { useStore } from "./store";

const navItems = [
  { path: "/", label: "Dashboard", icon: LayoutDashboard },
  { path: "/sessions", label: "Sessions", icon: ListTree },
  { path: "/tools", label: "Tools", icon: Terminal },
  { path: "/apps", label: "Apps Hub", icon: AppWindow },
  { path: "/chat", label: "Chat", icon: MessageSquareText },
  { path: "/help", label: "Help", icon: BookOpen },
  { path: "/settings", label: "Settings", icon: Settings2 },
  { path: "/status", label: "Status", icon: Activity },
  { path: "/api-docs", label: "API Docs", icon: Code2 },
];

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation();
  const sidebarOpen = useStore((s) => s.sidebarOpen);
  const toggleSidebar = useStore((s) => s.toggleSidebar);

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
              <div className="flex items-center gap-2 mb-6">
                <Terminal className="w-6 h-6 text-accent" />
                <span className="font-semibold text-sm">opencode-cli-mcp</span>
              </div>
              <nav className="flex flex-col gap-0.5">
                {navItems.map((item) => {
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                        active
                          ? "bg-accent/10 text-accent"
                          : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
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
            onClick={toggleSidebar}
            className="text-zinc-400 hover:text-zinc-200 transition-colors"
            title={sidebarOpen ? "Close sidebar" : "Open sidebar"}
            aria-label={sidebarOpen ? "Close sidebar" : "Open sidebar"}
          >
            {sidebarOpen ? <PanelRightClose className="w-4 h-4" /> : <PanelRightOpen className="w-4 h-4" />}
          </button>
          <span className="text-sm text-zinc-500">opencode-cli-mcp</span>
          <div className="flex-1" />
          <span className="text-xs text-zinc-600">v0.1.0</span>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
