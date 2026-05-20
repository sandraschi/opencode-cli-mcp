import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Puzzle,
  ChevronDown,
  ChevronRight,
  Code2,
  Copy,
  Check,
  FolderTree,
  Terminal,
  ExternalLink,
  Layers,
} from "lucide-react";
import { api } from "../services/api";

import type { OpenCodeToolDef } from "../services/api";

const INSTALL_STEPS = [
  "Copy the tool files from this project's <code>.opencode/tools/</code> directory",
  "Paste them into your opencode project's <code>.opencode/tools/</code> directory",
  "Restart opencode — tools are auto-loaded on start",
  'Use the tool by name (e.g. "fleet_status", "system") in your opencode session',
];

export function OpenCodeTools() {
  const [tools, setTools] = useState<OpenCodeToolDef[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [showSource, setShowSource] = useState<Set<string>>(new Set());
  const [copied, setCopied] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    api
      .listOpenCodeTools()
      .then((d) => {
        if (d.success) setTools(d.data.tools);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const toggleExpanded = (name: string) => {
    setExpanded((prev) => (prev === name ? null : name));
  };

  const toggleSource = (name: string) => {
    setShowSource((prev) => {
      const next = new Set(prev);
      if (next.has(name)) next.delete(name);
      else next.add(name);
      return next;
    });
  };

  const handleCopy = async (name: string, source: string) => {
    try {
      await navigator.clipboard.writeText(source);
      setCopied(name);
      setTimeout(() => setCopied(null), 2000);
    } catch {
      // clipboard not available
    }
  };

  const categories = [...new Set(tools.map((t) => t.category))];

  return (
    <div className="max-w-3xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Puzzle className="w-6 h-6 text-accent" />
          OpenCode Custom Tools
        </h1>
        <p className="text-sm text-zinc-500 mt-1">
          6 custom tools that extend opencode with MCP fleet awareness, session management, and system diagnostics.
        </p>
      </div>

      <motion.section
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-surface-light border border-surface-border rounded-xl p-5 mb-6"
      >
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <FolderTree className="w-4 h-4" />
          Installation
        </h2>
        <p className="text-sm text-zinc-300 mb-3">
          OpenCode loads custom tools from <code className="bg-zinc-800 text-accent px-1.5 py-0.5 rounded text-xs font-mono">.opencode/tools/</code> at startup.
          Each <code className="bg-zinc-800 text-accent px-1.5 py-0.5 rounded text-xs font-mono">.ts</code> file becomes a tool the LLM can invoke.
        </p>
        <ol className="space-y-2">
          {INSTALL_STEPS.map((step, i) => (
            <li key={i} className="flex gap-2 text-sm text-zinc-400">
              <span className="text-accent font-mono flex-shrink-0">{i + 1}.</span>
              <span dangerouslySetInnerHTML={{ __html: step }} />
            </li>
          ))}
        </ol>
        <div className="mt-4 p-3 bg-zinc-900 border border-zinc-800 rounded-lg">
          <div className="flex items-center gap-2 text-xs text-zinc-400 mb-1">
            <Terminal className="w-3 h-3" />
            Quick copy — run in your opencode project root:
          </div>
          <code className="text-xs text-zinc-300 font-mono">
            cp -r path/to/opencode-cli-mcp/.opencode/tools/* .opencode/tools/
          </code>
        </div>
        <a
          href="https://opencode.ai/docs/custom-tools/"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 mt-3 text-xs text-accent hover:underline"
        >
          <ExternalLink className="w-3 h-3" />
          OpenCode custom tools documentation
        </a>
      </motion.section>

      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider flex items-center gap-2">
          <Layers className="w-4 h-4" />
          Available Tools ({tools.length})
        </h2>

        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-16 bg-surface-light rounded-xl animate-pulse" />
            ))}
          </div>
        ) : (
          categories.map((category) => {
            const categoryTools = tools.filter((t) => t.category === category);
            return (
              <div key={category}>
                <h3 className="text-xs text-zinc-600 font-semibold mb-2 ml-1">{category}</h3>
                <div className="space-y-2">
                  {categoryTools.map((tool) => {
                    const isExpanded = expanded === tool.name;
                    const hasSource = showSource.has(tool.name);
                    return (
                      <motion.div
                        key={tool.name}
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        className="bg-surface-light border border-surface-border rounded-xl overflow-hidden"
                      >
                        <button
                          onClick={() => toggleExpanded(tool.name)}
                          className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-zinc-800/30 transition-colors"
                        >
                          {isExpanded ? (
                            <ChevronDown className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                          ) : (
                            <ChevronRight className="w-4 h-4 text-zinc-500 flex-shrink-0" />
                          )}
                          <Code2 className="w-4 h-4 text-accent flex-shrink-0" />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-semibold">
                                {tool.name}
                              </span>
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-accent/10 text-accent font-mono">
                                .opencode/tools/{tool.name}.ts
                              </span>
                            </div>
                            <p className="text-xs text-zinc-500 truncate mt-0.5">
                              {tool.description}
                            </p>
                          </div>
                        </button>
                        <AnimatePresence>
                          {isExpanded && (
                            <motion.div
                              initial={{ height: 0, opacity: 0 }}
                              animate={{ height: "auto", opacity: 1 }}
                              exit={{ height: 0, opacity: 0 }}
                              transition={{ duration: 0.15 }}
                              className="overflow-hidden"
                            >
                              <div className="px-4 pb-4 border-t border-surface-border">
                                <div className="mt-3">
                                  <p className="text-sm text-zinc-300 mb-2">{tool.description}</p>
                                  <button
                                    onClick={() => toggleSource(tool.name)}
                                    className="flex items-center gap-1 text-xs text-accent hover:underline mb-2"
                                  >
                                    {hasSource ? "Hide source" : "View source"}
                                    <Code2 className="w-3 h-3" />
                                  </button>
                                  {hasSource && (
                                    <div className="relative">
                                      <button
                                        onClick={() => handleCopy(tool.name, tool.source)}
                                        className="absolute top-2 right-2 flex items-center gap-1 px-2 py-1 rounded text-xs bg-zinc-700 hover:bg-zinc-600 text-zinc-300 transition-colors"
                                      >
                                        {copied === tool.name ? (
                                          <>
                                            <Check className="w-3 h-3 text-green-400" />
                                            Copied
                                          </>
                                        ) : (
                                          <>
                                            <Copy className="w-3 h-3" />
                                            Copy
                                          </>
                                        )}
                                      </button>
                                      <pre className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 text-xs text-zinc-300 font-mono leading-relaxed overflow-x-auto max-h-96">
                                        {tool.source}
                                      </pre>
                                    </div>
                                  )}
                                </div>
                              </div>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </motion.div>
                    );
                  })}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
