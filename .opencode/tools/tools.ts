import { tool } from "@opencode-ai/plugin"

const API = "http://127.0.0.1:10951/api"

export default tool({
  description: "List all MCP tools available in the opencode-cli-mcp server. Use this to discover what capabilities the MCP server exposes.",
  args: {
    search: tool.schema.string().describe("Optional substring filter to find specific tools by name or description").optional(),
  },
  async execute(args) {
    const resp = await fetch(`${API}/tools`)
    const { data } = await resp.json() as { success: boolean; data: { tools: Array<{ name: string; description: string }> } }
    let tools = data.tools
    if (args.search) tools = tools.filter(t => t.name.includes(args.search!) || t.description.includes(args.search!))
    return tools.map(t => `- \`${t.name}\` — ${t.description}`).join("\n")
  },
})
