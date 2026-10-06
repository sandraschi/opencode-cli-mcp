import { useEffect, useMemo, useState } from "react";
import { BookOpen, FileText, ExternalLink, Search, ChevronRight, Loader2 } from "lucide-react";
import { api } from "../services/api";

import type { DocEntry, DocContent } from "../services/api";

type HelpTab = "overview" | "wrappee" | "api" | "troubleshoot" | "faq" | "docs";

const TABS: { id: HelpTab; name: string; desc: string }[] = [
  { id: "overview", name: "Overview", desc: "What this app is" },
  { id: "wrappee", name: "opencode", desc: "The wrapped agent CLI" },
  { id: "api", name: "API & Ports", desc: "Endpoints, env, restart" },
  { id: "troubleshoot", name: "Troubleshoot", desc: "Symptom to fix" },
  { id: "faq", name: "FAQ", desc: "Asked questions" },
  { id: "docs", name: "Docs", desc: "Repo documentation" },
];

const PAGES: { route: string; name: string; purpose: string }[] = [
  { route: "/", name: "Dashboard", purpose: "Serve status, sessions, tools, fleet, depot KPIs" },
  { route: "/sessions", name: "Sessions", purpose: "Live sessions: transcript, steer, diff, export" },
  { route: "/depot", name: "History", purpose: "Offline depot: search, archive, rename, delete" },
  { route: "/projects", name: "Projects", purpose: "Run history with status badges" },
  { route: "/runs", name: "Runs", purpose: "Agent run queue (via Projects)" },
  { route: "/usage", name: "Usage", purpose: "Token and cost time series with CSV export" },
  { route: "/tools", name: "Tools Hub", purpose: "MCP tool registry with drill-down" },
  { route: "/oc-tools", name: "OC Tools", purpose: "Custom opencode tools: source + install" },
  { route: "/mcp-servers", name: "MCP Servers", purpose: "Configured MCP servers, add new" },
  { route: "/mcpb", name: "MCPB Install", purpose: "Bundle install with dry-run preview" },
  { route: "/plugins", name: "Plugins", purpose: "Plugin management" },
  { route: "/sidebar", name: "Sidebar", purpose: "Desktop companion status and help" },
  { route: "/apps", name: "Fleet Apps", purpose: "Fleet service discovery and launch" },
  { route: "/chat", name: "Chat", purpose: "Local LLM chat, four personas" },
  { route: "/settings", name: "Settings", purpose: "Providers, models, cloud keys, GPU prompt" },
  { route: "/status", name: "Status Audit", purpose: "CPU, GPU, memory, diagnostics" },
  { route: "/logs", name: "Logs", purpose: "Backend ring buffer with tail and export" },
  { route: "/api-docs", name: "API Docs", purpose: "Swagger UI and ReDoc" },
  { route: "/help", name: "Help", purpose: "This page" },
];

const PORTS: { port: string; owner: string; notes: string }[] = [
  { port: "10950", owner: "Vite frontend", notes: "Dashboard dev server; /api/* proxied to :10951" },
  { port: "10951", owner: "Unified backend", notes: "REST /api/* + MCP /mcp (api.main:app)" },
  { port: "4097", owner: "opencode serve", notes: "Backend-owned headless serve, autostarted" },
];

const ENVS: { name: string; effect: string }[] = [
  { name: "OPENCODE_SERVE_URL", effect: "Serve to talk to (default http://127.0.0.1:4097)" },
  { name: "OPENCODE_BINARY", effect: "Pinned to the scoop shim in fleet-start.config.ps1; shutil.which fallback" },
  { name: "OPENCODE_DB_PATH", effect: "Depot location override (default ~/.local/share/opencode/opencode.db)" },
  { name: "OPENCODE_CLI_MCP_RAG_ENABLED", effect: "0 disables RAG endpoints (default 1)" },
  { name: "OPENCODE_CLI_MCP_BACKUP_INTERVAL_HOURS", effect: "Autobackup cadence, 0 disables (default 24)" },
  { name: "OPENCODE_SERVER_PASSWORD", effect: "Set ONLY for a password-protected (desktop :4096) serve" },
];

const ENDPOINTS: { method: string; path: string; notes: string }[] = [
  { method: "GET", path: "/api/health", notes: "Backend liveness (excluded from Logs ring)" },
  { method: "GET", path: "/api/v1/health", notes: "Canonical fleet probe (start.ps1 readiness gate)" },
  { method: "GET", path: "/api/v1/diagnostics", notes: "Backend, system, tools, errors" },
  { method: "GET", path: "/api/capabilities", notes: "Tool surface + versions" },
  { method: "GET", path: "/api/opencode/status", notes: "Serve health (autostarts serve if down)" },
  { method: "GET", path: "/api/fleet", notes: "Fleet server discovery" },
  { method: "GET", path: "/api/system", notes: "CPU, memory, GPU, platform" },
  { method: "GET", path: "/api/depot/stats", notes: "Depot aggregates (~20-30s on multi-GB DB)" },
  { method: "GET", path: "/api/logs", notes: "Ring-buffer request log + export" },
  { method: "GET", path: "/api/docs", notes: "Repo documentation index for this page" },
];

const FIXES: { symptom: string; cause: string; fix: string }[] = [
  {
    symptom: '"opencode serve is unreachable" red banner, Offline / unknown',
    cause:
      "Backend answered but serve is down: autostart failed (binary off PATH) or a stale password-locked serve squats :4097. Seen 2026-10-05/06.",
    fix: "Restart the backend: .\\start.ps1 -BackendOnly -NoBrowser. If it persists, kill the :4097 holder (Get-NetTCPConnection -LocalPort 4097) and let the backend respawn it.",
  },
  {
    symptom: '"Backend unreachable" amber banner, every card ? / 0',
    cause:
      "Backend down, or (fixed 2026-10-06) its event loop wedged by inline depot sqlite on a multi-GB opencode.db.",
    fix: "Check the :10951 listener; restart with .\\start.ps1. Current code runs all depot calls in worker threads, so a recurrence is a new bug - report it.",
  },
  {
    symptom: 'Dashboard showed Offline for a healthy serve ("finish setup" banner)',
    cause: "Fixed 2026-10-06: serve returns {healthy:true} with no status key, which the old check could never match.",
    fix: "None needed - pull current main and reload. The banner now only appears when serve is truly unreachable.",
  },
  {
    symptom: "Terminal / Logs page flooded with GET /api/health",
    cause: "Fixed 2026-10-06: the status dot polled every 1s per tab.",
    fix: "None needed - steady-state heartbeat is 30s and health probes skip the ring buffer. Reload the page.",
  },
  {
    symptom: "DB / cost cards show ... for ~30s on first load",
    cause:
      "Normal: the depot scan aggregates a multi-GB opencode.db (11 GB takes ~20-30s) and runs lazily since 2026-10-06.",
    fix: "Wait; everything else renders first. A failure shows an inline Retry, not a page error.",
  },
  {
    symptom: "EADDRINUSE / port conflict on start",
    cause: "A previous backend or serve still holds :10951 / :4097.",
    fix: "start.ps1 clears holders automatically. Manual: Get-NetTCPConnection -LocalPort <port> then Stop-Process on the owner.",
  },
  {
    symptom: "Serve on :4096 returns 401",
    cause: "That is the desktop app's password-protected serve, not ours.",
    fix: "The backend uses its own serve on :4097. To talk to the desktop's instead, set OPENCODE_SERVER_PASSWORD (+ optional OPENCODE_SERVER_USERNAME).",
  },
  {
    symptom: "RAG endpoints 503 / RAGUnavailableError",
    cause: "fastembed / lancedb / pyarrow missing or RAG disabled.",
    fix: "uv sync --extra rag. First index downloads the embedding model (slow once).",
  },
];

const FAQS: { q: string; a: string }[] = [
  {
    q: "Where is my data?",
    a: "Sessions live in the opencode depot (~/.local/share/opencode/opencode.db, OPENCODE_DB_PATH override). Agent runs persist in the SQLite job store (%LOCALAPPDATA%\\opencode-cli-mcp\\jobs.db). Settings live in %LOCALAPPDATA%\\opencode-cli-mcp\\settings.json - never in the repo.",
  },
  {
    q: "The serve shows Offline - what setup am I missing?",
    a: "None: the backend autospawns its own serve on :4097, so Offline means autostart failed or the serve died. Restart the backend (.\\start.ps1); the Troubleshoot tab lists the known causes.",
  },
  {
    q: "How do MCP clients connect?",
    a: "Stdio for Claude Desktop / Cursor / Windsurf: uv run python -m opencode_cli_mcp.server. HTTP (Streamable) for shared setups: http://127.0.0.1:10951/mcp with the backend running.",
  },
  {
    q: "Which service restarts after a code change?",
    a: "Backend (api/ or src/ changes): restart it with .\\start.ps1 -BackendOnly -NoBrowser. Frontend (web_sota/) changes hot-reload via Vite; the installed desktop app needs a frontend rebuild (bun run build).",
  },
  {
    q: "How do I rebuild or resync search?",
    a: 'Keyword search needs nothing (direct LIKE over the DB). Semantic recall needs an index: Depot page index actions, or opencode_depot(action="rag_index"). Re-index after bulk imports.',
  },
  {
    q: "Where are the logs?",
    a: "In-app: the Logs page (/logs) with tail mode and export, backed by GET /api/logs. Desktop shell: %LOCALAPPDATA%\\opencode-cli-mcp\\logs\\backend-spawn.log.",
  },
  {
    q: "How do I add or select a project?",
    a: 'Agent runs take a project parameter (opencode_runs start with project="D:/..."). The Projects page lists known project directories from run history.',
  },
];

function DocHtml({ html }: { html: string }) {
  // biome-ignore lint/security/noDangerouslySetInnerHtml: first-party repo docs served by this backend; renderMarkdown escapes code blocks
  return <div className="prose-custom text-sm leading-relaxed" dangerouslySetInnerHTML={{ __html: html }} />;
}

function renderMarkdown(md: string): string {
  let html = md
    .split("\n")
    .map((line) => {
      if (line.startsWith("### "))
        return `<h3 class="text-base font-semibold text-zinc-200 mt-5 mb-2">${line.slice(4)}</h3>`;
      if (line.startsWith("## "))
        return `<h2 class="text-lg font-semibold text-zinc-100 mt-6 mb-3 border-b border-zinc-800 pb-1">${line.slice(3)}</h2>`;
      if (line.startsWith("# ")) return `<h1 class="text-xl font-bold text-white mt-4 mb-4">${line.slice(2)}</h1>`;
      if (line.startsWith("- ")) return `<li class="text-sm text-zinc-300 ml-4 list-disc">${line.slice(2)}</li>`;
      if (line.startsWith("| ")) return line;
      if (line.startsWith("```")) return "";
      if (line.match(/^\d+\. /)) {
        const content = line.replace(/^\d+\.\s*/, "");
        return `<li class="text-sm text-zinc-300 ml-4 list-decimal">${content}</li>`;
      }
      if (line.trim() === "---") return `<hr class="my-4 border-zinc-800" />`;
      if (line.trim() === "") return "";
      return `<p class="text-sm text-zinc-300 mb-1">${line}</p>`;
    })
    .join("\n");

  html = html.replace(
    /`([^`]+)`/g,
    '<code class="bg-zinc-800 text-accent px-1.5 py-0.5 rounded text-xs font-mono">$1</code>',
  );
  html = html.replace(
    /\[([^\]]+)\]\(([^)]+)\)/g,
    '<a href="$2" class="text-accent hover:underline" target="_blank" rel="noopener noreferrer">$1</a>',
  );

  const tableRegex = /\|(.+)\|\n\|[-| ]+\|\n((?:\|.+\|\n?)*)/g;
  html = html.replace(tableRegex, (_match, headerRow, bodyRows) => {
    const headers = headerRow
      .split("|")
      .map((h: string) => h.trim())
      .filter(Boolean);
    const rows = bodyRows
      .trim()
      .split("\n")
      .map((r: string) =>
        r
          .split("|")
          .map((c: string) => c.trim())
          .filter(Boolean),
      );
    let table = '<div class="overflow-x-auto my-3"><table class="w-full text-xs text-zinc-300 border-collapse">';
    table += "<thead><tr>";
    for (const h of headers) {
      table += `<th class="text-left px-3 py-2 border-b border-zinc-700 font-semibold text-zinc-400">${h}</th>`;
    }
    table += "</tr></thead><tbody>";
    for (const row of rows) {
      table += "<tr>";
      for (const cell of row) {
        table += `<td class="px-3 py-2 border-b border-zinc-800">${cell}</td>`;
      }
      table += "</tr>";
    }
    table += "</tbody></table></div>";
    return table;
  });

  const codeBlockRegex = /```(\w*)\n([\s\S]*?)```/g;
  html = html.replace(codeBlockRegex, (_match, _lang, code) => {
    const escaped = code.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    return `<pre class="bg-zinc-900 border border-zinc-800 rounded-lg p-4 my-3 overflow-x-auto"><code class="text-xs text-zinc-300 font-mono leading-relaxed">${escaped}</code></pre>`;
  });

  return html;
}

export function Help() {
  const [tab, setTab] = useState<HelpTab>("overview");
  const [query, setQuery] = useState("");
  const [openFaq, setOpenFaq] = useState<number | null>(null);
  const [docs, setDocs] = useState<DocEntry[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [docContent, setDocContent] = useState<DocContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDoc, setLoadingDoc] = useState(false);

  useEffect(() => {
    setLoading(true);
    api
      .listDocs()
      .then((d) => {
        if (d.success) {
          setDocs(d.data.docs);
          if (d.data.docs.length > 0 && !selected) {
            setSelected(d.data.docs[0].id);
          }
        }
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [selected]);

  useEffect(() => {
    if (!selected) return;
    setLoadingDoc(true);
    api
      .getDoc(selected)
      .then((d) => {
        if (d.success) setDocContent(d.data);
        setLoadingDoc(false);
      })
      .catch(() => setLoadingDoc(false));
  }, [selected]);

  const q = query.trim().toLowerCase();
  const filteredFixes = useMemo(
    () => (q ? FIXES.filter((f) => `${f.symptom} ${f.cause} ${f.fix}`.toLowerCase().includes(q)) : FIXES),
    [q],
  );
  const filteredFaqs = useMemo(() => (q ? FAQS.filter((f) => `${f.q} ${f.a}`.toLowerCase().includes(q)) : FAQS), [q]);
  const filteredDocs = useMemo(
    () => docs.filter((d) => d.label.toLowerCase().includes(q) || d.id.toLowerCase().includes(q)),
    [docs, q],
  );

  const renderedHtml = useMemo(() => (docContent ? renderMarkdown(docContent.content) : ""), [docContent]);

  const openOnboarding = () => {
    setSelected("ONBOARDING");
    setTab("docs");
  };

  return (
    <div data-testid="help-page">
      <h1 className="text-xl font-bold text-white mb-1">Help</h1>
      <p className="text-sm text-zinc-500 mb-4">What this app is, the opencode it wraps, endpoints, fixes, and docs.</p>

      <div data-testid="help-tabs" className="flex gap-6 border-b border-zinc-800 mb-5 flex-wrap">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            data-testid={`help-tab-${t.id}`}
            onClick={() => setTab(t.id)}
            className={`pb-2 -mb-px border-b-2 text-sm transition-colors ${
              tab === t.id
                ? "border-accent text-accent font-medium"
                : "border-transparent text-zinc-500 hover:text-zinc-300"
            }`}
            title={t.desc}
          >
            {t.name}
          </button>
        ))}
      </div>

      {(tab === "troubleshoot" || tab === "faq" || tab === "docs") && (
        <div className="relative mb-4 max-w-md">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-zinc-500" />
          <input
            type="text"
            data-testid="help-search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={tab === "docs" ? "Search docs..." : "Filter by symptom, cause, or fix..."}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-8 pr-3 py-2 text-xs focus:outline-none focus:border-accent/50"
          />
        </div>
      )}

      {tab === "overview" && (
        <div className="max-w-3xl">
          <p className="text-sm text-zinc-300 leading-relaxed mb-4">
            opencode-cli-mcp delegates implementation work to{" "}
            <span className="text-zinc-100 font-medium">opencode</span> agents from any MCP client: launch runs,
            supervise them mid-task, and review the resulting sessions. A unified backend serves the REST API and the
            MCP endpoint on one port, and this dashboard mirrors the whole surface for humans.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
            <div className="bg-surface-light border border-surface-border rounded-xl p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">UI</div>
              <div className="text-sm text-zinc-200 font-mono">:10950</div>
              <div className="text-xs text-zinc-500 mt-1">Vite frontend, /api/* proxied to the backend</div>
            </div>
            <div className="bg-surface-light border border-surface-border rounded-xl p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">API + MCP</div>
              <div className="text-sm text-zinc-200 font-mono">:10951</div>
              <div className="text-xs text-zinc-500 mt-1">FastAPI REST under /api/*, MCP at /mcp</div>
            </div>
            <div className="bg-surface-light border border-surface-border rounded-xl p-4">
              <div className="text-xs text-zinc-500 uppercase tracking-wider mb-1">opencode serve</div>
              <div className="text-sm text-zinc-200 font-mono">:4097</div>
              <div className="text-xs text-zinc-500 mt-1">Backend-owned headless serve, autostarted</div>
            </div>
          </div>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Pages</h2>
          <div className="bg-surface-light border border-surface-border rounded-xl overflow-hidden">
            {PAGES.map((p) => (
              <div key={p.route} className="flex gap-4 px-4 py-2 border-b border-zinc-800/60 last:border-0 text-sm">
                <code className="text-accent font-mono text-xs w-24 flex-shrink-0 pt-0.5">{p.route}</code>
                <span className="text-zinc-200 w-28 flex-shrink-0">{p.name}</span>
                <span className="text-zinc-500 text-xs pt-0.5">{p.purpose}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === "wrappee" && (
        <div className="max-w-3xl text-sm leading-relaxed">
          <p className="text-zinc-300 mb-4">
            The wrapped thing is <span className="text-zinc-100 font-medium">opencode</span>
            (opencode.ai) - an AI coding-agent CLI. This server does not reimplement it: every live session, agent run,
            and provider call goes through opencode's own HTTP API (`opencode serve`). Tested with opencode 1.18.x.
          </p>
          <div className="bg-surface-light border border-surface-border rounded-xl overflow-hidden mb-4">
            <div className="px-4 py-2.5 border-b border-zinc-800/60 text-sm">
              <span className="text-zinc-500 block text-xs uppercase tracking-wider mb-0.5">Where it runs</span>
              <span className="text-zinc-200">
                Headless, spawned by the backend:{" "}
                <code className="font-mono text-xs bg-zinc-800 px-1.5 py-0.5 rounded">opencode serve --port 4097</code>{" "}
                from the scoop shim (this machine). Nothing to start by hand.
              </span>
            </div>
            <div className="px-4 py-2.5 border-b border-zinc-800/60 text-sm">
              <span className="text-zinc-500 block text-xs uppercase tracking-wider mb-0.5">Headless vs GUI</span>
              <span className="text-zinc-200">
                The backend uses the headless serve. The opencode desktop app runs its own password-locked serve on
                :4096, and the terminal UI (`opencode` TUI) is interactive - both are separate from this stack.
              </span>
            </div>
            <div className="px-4 py-2.5 border-b border-zinc-800/60 text-sm">
              <span className="text-zinc-500 block text-xs uppercase tracking-wider mb-0.5">Hands in / hands out</span>
              <span className="text-zinc-200">
                Hands in: drive agents from this dashboard (Runs, Sessions) or any MCP client. Hands out: use the
                desktop app or TUI directly - the depot keeps reading the same database either way, so nothing is lost.
              </span>
            </div>
            <div className="px-4 py-2.5 text-sm">
              <span className="text-zinc-500 block text-xs uppercase tracking-wider mb-0.5">
                How the UI verifies it
              </span>
              <span className="text-zinc-200">
                Dashboard KPI “opencode Server” (Online / Offline) backed by{" "}
                <code className="font-mono text-xs bg-zinc-800 px-1.5 py-0.5 rounded">GET /api/opencode/status</code>.
                First-run checklist lives in the onboarding doc:{" "}
              </span>
              <button type="button" onClick={openOnboarding} className="text-accent hover:underline font-medium">
                open docs/ONBOARDING.md
              </button>
            </div>
          </div>
        </div>
      )}

      {tab === "api" && (
        <div className="max-w-4xl">
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Ports</h2>
          <div className="bg-surface-light border border-surface-border rounded-xl overflow-hidden mb-6">
            {PORTS.map((p) => (
              <div key={p.port} className="flex gap-4 px-4 py-2 border-b border-zinc-800/60 last:border-0 text-sm">
                <code className="font-mono text-xs text-accent w-16 flex-shrink-0 pt-0.5">:{p.port}</code>
                <span className="text-zinc-200 w-36 flex-shrink-0">{p.owner}</span>
                <span className="text-zinc-500 text-xs pt-0.5">{p.notes}</span>
              </div>
            ))}
          </div>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Environment</h2>
          <div className="bg-surface-light border border-surface-border rounded-xl overflow-hidden mb-6">
            {ENVS.map((e) => (
              <div key={e.name} className="flex gap-4 px-4 py-2 border-b border-zinc-800/60 last:border-0 text-sm">
                <code className="font-mono text-xs text-accent w-64 flex-shrink-0 pt-0.5 break-all">{e.name}</code>
                <span className="text-zinc-500 text-xs pt-0.5">{e.effect}</span>
              </div>
            ))}
          </div>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Key endpoints</h2>
          <div className="bg-surface-light border border-surface-border rounded-xl overflow-hidden mb-6">
            {ENDPOINTS.map((e) => (
              <div key={e.path} className="flex gap-4 px-4 py-2 border-b border-zinc-800/60 last:border-0 text-sm">
                <span className="text-zinc-500 text-xs w-12 flex-shrink-0 pt-0.5">{e.method}</span>
                <code className="font-mono text-xs text-accent w-48 flex-shrink-0 pt-0.5 break-all">{e.path}</code>
                <span className="text-zinc-500 text-xs pt-0.5">{e.notes}</span>
              </div>
            ))}
          </div>
          <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3">Start / restart</h2>
          <div className="bg-surface-light border border-surface-border rounded-xl p-4 text-sm text-zinc-300">
            <p className="mb-2">
              Full stack: <code className="font-mono text-xs bg-zinc-800 px-1.5 py-0.5 rounded">.\start.ps1</code>{" "}
              (clears stale port holders, runs the readiness gate on /api/v1/health).
            </p>
            <p>
              Backend only (picks up api/ and src/ changes):{" "}
              <code className="font-mono text-xs bg-zinc-800 px-1.5 py-0.5 rounded">
                .\start.ps1 -BackendOnly -NoBrowser
              </code>{" "}
              - kill the :10951 holder first so the new process (and new env) actually starts. Frontend changes
              hot-reload.
            </p>
          </div>
        </div>
      )}

      {tab === "troubleshoot" && (
        <div
          data-testid="help-fixes"
          className="max-w-4xl bg-surface-light border border-surface-border rounded-xl overflow-hidden"
        >
          {filteredFixes.length === 0 && <p className="text-sm text-zinc-500 px-4 py-6">No entries match “{query}”.</p>}
          {filteredFixes.map((f) => (
            <div key={f.symptom} className="px-4 py-3 border-b border-zinc-800/60 last:border-0 text-sm">
              <div className="text-zinc-100 font-medium mb-1">{f.symptom}</div>
              <div className="text-zinc-500 text-xs mb-1">{f.cause}</div>
              <div className="text-zinc-300 text-xs">{f.fix}</div>
            </div>
          ))}
        </div>
      )}

      {tab === "faq" && (
        <div data-testid="help-faq" className="max-w-3xl space-y-2">
          {filteredFaqs.length === 0 && <p className="text-sm text-zinc-500 px-1 py-4">No entries match “{query}”.</p>}
          {filteredFaqs.map((f, i) => (
            <div
              key={f.q}
              data-testid="faq-item"
              className="bg-surface-light border border-surface-border rounded-xl overflow-hidden"
            >
              <button
                type="button"
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="w-full flex items-center gap-2 px-4 py-3 text-sm text-left text-zinc-200 hover:text-white transition-colors"
              >
                <ChevronRight
                  className={`w-3.5 h-3.5 flex-shrink-0 transition-transform ${openFaq === i ? "rotate-90 text-accent" : "text-zinc-600"}`}
                />
                {f.q}
              </button>
              {openFaq === i && <p className="px-4 pb-3 pl-9 text-xs text-zinc-400 leading-relaxed">{f.a}</p>}
            </div>
          ))}
        </div>
      )}

      {tab === "docs" && (
        <div className="flex gap-6 h-full">
          <div className="w-64 flex-shrink-0">
            <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
              <BookOpen className="w-4 h-4" />
              Documents
              <span className="text-xs text-zinc-600 font-normal">({docs.length})</span>
            </h2>
            <div className="space-y-1">
              {loading ? (
                <div className="flex items-center gap-2 text-xs text-zinc-500 px-3 py-4">
                  <Loader2 className="w-3 h-3 animate-spin" />
                  Loading...
                </div>
              ) : filteredDocs.length === 0 ? (
                <p className="text-xs text-zinc-600 px-3 py-2">No matching documents</p>
              ) : (
                filteredDocs.map((doc) => (
                  <button
                    type="button"
                    key={doc.id}
                    data-testid={`help-doc-${doc.id}`}
                    onClick={() => setSelected(doc.id)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                      selected === doc.id
                        ? "bg-accent/10 text-accent"
                        : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
                    }`}
                  >
                    <ChevronRight
                      className={`w-3 h-3 flex-shrink-0 ${selected === doc.id ? "text-accent" : "text-transparent"}`}
                    />
                    <FileText className="w-4 h-4 flex-shrink-0" />
                    <span className="truncate">{doc.label}</span>
                  </button>
                ))
              )}
            </div>
            <a
              href="http://localhost:10951/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-2 mt-6 px-3 py-2 text-sm text-zinc-500 hover:text-zinc-300 transition-colors"
            >
              <ExternalLink className="w-4 h-4" />
              API Docs (Swagger)
            </a>
          </div>

          <div className="flex-1 min-w-0 bg-surface-light border border-surface-border rounded-xl overflow-hidden">
            <div className="p-4 border-b border-surface-border flex items-center justify-between">
              <h3 className="font-semibold text-sm">{docContent?.label ?? "Select a document"}</h3>
              {docContent && <span className="text-xs text-zinc-600">{docContent.id}</span>}
            </div>
            <div className="p-6 overflow-auto max-h-[calc(100vh-12rem)]">
              {loadingDoc ? (
                <div className="space-y-3">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className="h-4 bg-zinc-800 rounded animate-pulse"
                      style={{ width: `${60 + i * 10}%` }}
                    />
                  ))}
                </div>
              ) : renderedHtml ? (
                <DocHtml html={renderedHtml} />
              ) : (
                <p className="text-sm text-zinc-500">Select a document from the sidebar.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
