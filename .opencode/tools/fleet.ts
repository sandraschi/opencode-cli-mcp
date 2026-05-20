import { tool } from "@opencode-ai/plugin"

const API = "http://127.0.0.1:10951/api"

export const status = tool({
  description: "Check which MCP fleet servers are currently running on localhost",
  args: {
    filter: tool.schema.string().describe("Optional substring filter for app names").optional(),
    aliveOnly: tool.schema.boolean().describe("Show only running servers (default true)").default(true),
  },
  async execute(args) {
    const resp = await fetch(`${API}/fleet`)
    const { data } = await resp.json() as { success: boolean; data: { apps: Array<{ port: number; name: string; alive: boolean; label: string }> } }
    let apps = data.apps
    if (args.aliveOnly) apps = apps.filter(a => a.alive)
    if (args.filter) apps = apps.filter(a => a.name.toLowerCase().includes(args.filter!.toLowerCase()))
    if (apps.length === 0) return "No matching fleet apps found."
    return apps.map(a => `${a.alive ? "✔" : "✗"} ${a.name} :${a.port}${a.label ? ` (${a.label})` : ""}`).join("\n")
  },
})

export const launch = tool({
  description: "Launch a fleet application by port number",
  args: {
    port: tool.schema.number().describe("Port number of the fleet app to launch"),
  },
  async execute(args) {
    const resp = await fetch(`${API}/fleet`)
    const { data } = await resp.json() as { success: boolean; data: { apps: Array<{ port: number; name: string; alive: boolean; label: string }> } }
    const app = data.apps.find(a => a.port === args.port)
    if (!app) return `No app found on port ${args.port}`
    if (app.alive) return `${app.name} is already running on port ${args.port}`
    return `${app.name} on port ${args.port} is offline. Launch it from the fleet dashboard or start script.`
  },
})
