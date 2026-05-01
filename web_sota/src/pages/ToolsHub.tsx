import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Terminal,
  ChevronDown,
  ChevronRight,
  Code2,
  BookOpen,
  Search,
  X,
} from "lucide-react";
import { api, type ToolDetail } from "../services/api";

export function ToolsHub() {
  const [tools, setTools] = useState<ToolDetail[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.listToolDetails()
      .then((r) => setTools(r.data.tools))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const filtered = tools.filter(
    (t) =>
      t.name.toLowerCase().includes(search.toLowerCase()) ||
      t.description.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Tools Hub</h1>
          <p className="text-sm text-zinc-500 mt-1">
            {tools.length} atomic MCP tools — click for details
          </p>
        </div>
        <div className="relative w-64">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search tools..."
            className="w-full bg-surface-light border border-surface-border rounded-lg pl-9 pr-3 py-2 text-sm focus:outline-none focus:border-accent/50"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300"
              title="Clear search"
              aria-label="Clear search"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {loading ? (
        <div className="space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-14 bg-zinc-800/50 animate-pulse rounded-lg" />
          ))}
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((tool) => (
            <motion.div
              key={tool.name}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-surface-light border border-surface-border rounded-lg overflow-hidden"
            >
              <button
                onClick={() => setExpanded(expanded === tool.name ? null : tool.name)}
                className="w-full flex items-center gap-3 p-3 text-left hover:bg-zinc-800/50 transition-colors"
                aria-expanded={expanded === tool.name ? "true" : "false"}
              >
                {expanded === tool.name ? (
                  <ChevronDown className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                ) : (
                  <ChevronRight className="w-4 h-4 text-zinc-400 flex-shrink-0" />
                )}
                <Terminal className="w-4 h-4 text-accent flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="font-mono text-sm">{tool.name}</div>
                  <div className="text-xs text-zinc-500 mt-0.5 truncate">
                    {tool.description}
                  </div>
                </div>
                <span className="text-xs text-zinc-600 bg-zinc-800 px-2 py-0.5 rounded">
                  atomic
                </span>
              </button>

              <AnimatePresence>
                {expanded === tool.name && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    className="border-t border-surface-border"
                  >
                    <div className="p-4 space-y-3">
                      <div>
                        <div className="flex items-center gap-1.5 text-xs text-zinc-400 uppercase tracking-wider mb-1.5">
                          <BookOpen className="w-3 h-3" />
                          Description
                        </div>
                        <p className="text-sm text-zinc-300">{tool.description}</p>
                      </div>

                      {tool.inputSchema && (
                        <div>
                          <div className="flex items-center gap-1.5 text-xs text-zinc-400 uppercase tracking-wider mb-1.5">
                            <Code2 className="w-3 h-3" />
                            Parameters
                          </div>
                          <div className="bg-zinc-800/50 rounded-lg p-3">
                            <pre className="text-xs font-mono text-zinc-400 whitespace-pre-wrap">
                              {JSON.stringify(tool.inputSchema, null, 2)}
                            </pre>
                          </div>
                        </div>
                      )}

                      <div>
                        <div className="flex items-center gap-1.5 text-xs text-zinc-400 uppercase tracking-wider mb-1.5">
                          <Terminal className="w-3 h-3" />
                          Example
                        </div>
                        <pre className="text-xs font-mono text-zinc-500 bg-zinc-800/30 rounded-lg p-3">
                          {`// Call via MCP client:
await mcpClient.callTool("${tool.name}", {
  // params...
});`}
                        </pre>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}

          {filtered.length === 0 && (
            <div className="text-center text-zinc-500 py-12">
              <Terminal className="w-8 h-8 mx-auto mb-2 opacity-30" />
              <p className="text-sm">No tools match "{search}"</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
