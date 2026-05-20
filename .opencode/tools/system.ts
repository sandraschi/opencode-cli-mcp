import { tool } from "@opencode-ai/plugin"

const API = "http://127.0.0.1:10951/api"

export default tool({
  description: "Get system resource information: CPU usage, memory, GPU name, platform",
  args: {},
  async execute() {
    const resp = await fetch(`${API}/system`)
    const { data } = await resp.json() as { success: boolean; data: { cpu: number; memory: { total: number; used: number; percent: number }; platform: string; gpu: string } }

    function formatBytes(bytes: number) {
      if (bytes > 1073741824) return `${(bytes / 1073741824).toFixed(1)} GB`
      return `${(bytes / 1048576).toFixed(0)} MB`
    }

    return [
      `Platform: ${data.platform}`,
      `CPU: ${data.cpu}%`,
      `Memory: ${formatBytes(data.memory.used)} / ${formatBytes(data.memory.total)} (${data.memory.percent}%)`,
      `GPU: ${data.gpu}`,
    ].join("\n")
  },
})
