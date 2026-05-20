import { tool } from "@opencode-ai/plugin"

const API = "http://127.0.0.1:10951/api"

export const list = tool({
  description: "List all active and recent opencode sessions",
  args: {},
  async execute() {
    const resp = await fetch(`${API}/opencode/sessions`)
    const { data } = await resp.json() as { success: boolean; data: { sessions: Array<{ id: string; title?: string; created_at?: string }> } }
    if (!data?.sessions?.length) return "No sessions found."
    return data.sessions.map(s => `- ${s.id} ${s.title ? `"${s.title}"` : ""}`).join("\n")
  },
})

export const diff = tool({
  description: "Show files created, modified, and deleted in an opencode session",
  args: {
    sessionId: tool.schema.string().describe("The session ID to diff"),
  },
  async execute(args) {
    const resp = await fetch(`${API}/opencode/sessions/${args.sessionId}/diff`)
    if (!resp.ok) return `Session ${args.sessionId} not found.`
    const { data } = await resp.json() as { success: boolean; data: { diff: Record<string, string[]> } }
    const d = data.diff
    const parts: string[] = []
    if (d.created?.length) parts.push("Created:\n" + d.created.map(f => `  + ${f}`).join("\n"))
    if (d.modified?.length) parts.push("Modified:\n" + d.modified.map(f => `  ~ ${f}`).join("\n"))
    if (d.deleted?.length) parts.push("Deleted:\n" + d.deleted.map(f => `  - ${f}`).join("\n"))
    return parts.join("\n\n") || "No file changes in this session."
  },
})

export const files = tool({
  description: "List all files touched (read, created, modified) in an opencode session",
  args: {
    sessionId: tool.schema.string().describe("The session ID to inspect"),
  },
  async execute(args) {
    const resp = await fetch(`${API}/opencode/sessions/${args.sessionId}/files`)
    if (!resp.ok) return `Session ${args.sessionId} not found.`
    const { data } = await resp.json() as { success: boolean; data: { files: Array<{ path: string; change_type?: string }> } }
    if (!data.files?.length) return "No files touched in this session."
    return data.files.map(f => `  ${f.change_type ?? "?"} ${f.path}`).join("\n")
  },
})
