import { tool } from "@opencode-ai/plugin"

const API = "http://127.0.0.1:10951/api"

export default tool({
  description: "List configured LLM providers and check opencode server health",
  args: {},
  async execute() {
    const resp = await fetch(`${API}/opencode/status`)
    if (!resp.ok) return "opencode serve is not running."
    const { data: statusData } = await resp.json() as { success: boolean; data: { health?: { status: string }; sessions?: number; config?: { providers?: Record<string, unknown> } } }

    const parts: string[] = []
    if (statusData.health) parts.push(`Server: ${statusData.health.status}`)
    if (statusData.sessions !== undefined) parts.push(`Active sessions: ${statusData.sessions}`)
    if (statusData.config?.providers) {
      const provs = Object.keys(statusData.config.providers as Record<string, unknown>)
      if (provs.length) parts.push(`Providers: ${provs.join(", ")}`)
    }
    return parts.join("\n") || "Server reachable but no details available."
  },
})
