import { tool } from "@opencode-ai/plugin"

const API = "http://127.0.0.1:10951/api"

export const list = tool({
  description: "List recent agent runs dispatched by the MCP server",
  args: {
    limit: tool.schema.number().describe("Max runs to return (default 10)").default(10),
  },
  async execute(args) {
    const resp = await fetch(`${API}/runs`)
    const { data } = await resp.json() as { success: boolean; data: { runs: Array<{ job_id: string; prompt: string; status: string; exit_code: number | null; created_at: number }> } }
    if (!data?.runs?.length) return "No agent runs found."
    const limited = data.runs.slice(0, args.limit)
    return limited.map(r => {
      const ts = new Date(r.created_at * 1000).toISOString().slice(0, 19)
      return `[${r.status}] ${r.job_id} - "${r.prompt.slice(0, 60)}" ${r.exit_code !== null ? `(exit ${r.exit_code})` : ""} ${ts}`
    }).join("\n")
  },
})

export const status = tool({
  description: "Get status of a specific agent run by job ID",
  args: {
    jobId: tool.schema.string().describe("The job ID to check"),
  },
  async execute(args) {
    const resp = await fetch(`${API}/runs/${args.jobId}`)
    if (!resp.ok) return `Run '${args.jobId}' not found.`
    const { data } = await resp.json() as { success: boolean; data: { run: { job_id: string; prompt: string; status: string; stdout: string; stderr: string; exit_code: number | null; created_at: number; completed_at: number | null } } }
    const r = data.run
    const ts = new Date(r.created_at * 1000).toISOString().slice(0, 19)
    let out = `Run ${r.job_id}: ${r.status}\nPrompt: "${r.prompt}"\nStarted: ${ts}`
    if (r.completed_at) out += `\nCompleted: ${new Date(r.completed_at * 1000).toISOString().slice(0, 19)}`
    if (r.exit_code !== null) out += `\nExit code: ${r.exit_code}`
    if (r.stdout) out += `\n\nOutput:\n${r.stdout.slice(0, 2000)}`
    if (r.stderr) out += `\n\nStderr:\n${r.stderr.slice(0, 1000)}`
    return out
  },
})
