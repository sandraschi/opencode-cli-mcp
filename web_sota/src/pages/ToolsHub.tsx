import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Terminal, ChevronDown, ChevronRight } from "lucide-react";
import { api } from "../services/api";

interface ToolInfo {
  name: string;
  description: string;
}

export function ToolsHub() {
  const [tools, setTools] = useState<ToolInfo[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);

  useEffect(() => {
    api.getCapabilities().then((caps) => {
      const names = caps.tool_surface.atomic_tools || [];
      const descriptions: Record<string, string> = {
        opencode_run_agent: "Run an opencode agent non-interactively with a prompt",
        opencode_list_sessions: "List all active and recent opencode sessions",
        opencode_get_session: "Get detailed information about a specific session",
        opencode_export_session: "Export a session as JSON for archiving",
        opencode_send_message: "Send a message to an existing session",
        opencode_get_messages: "Retrieve message history from a session",
        opencode_server_status: "Check the health and status of the opencode server",
        opencode_list_providers: "List configured LLM providers",
        opencode_get_project: "Get the current project context",
      };
      setTools(names.map((n) => ({ name: n, description: descriptions[n] || "MCP tool" })));
    }).catch(console.error);
  }, []);

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Tools Hub</h1>
      <p className="text-sm text-zinc-500 mb-6">
        MCP tools exposed by opencode-cli-mcp. These wrap the opencode serve HTTP API.
      </p>

      <div className="space-y-2">
        {tools.map((tool) => (
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
              <div>
                <div className="font-mono text-sm">{tool.name}</div>
                <div className="text-xs text-zinc-500 mt-0.5">{tool.description}</div>
              </div>
            </button>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
