import { useState } from "react";
import { ExternalLink, Code2, BookOpen } from "lucide-react";

const BACKEND = "http://127.0.0.1:10951";

export function ApiDocs() {
  const [view, setView] = useState<"swagger" | "redoc">("swagger");

  const src =
    view === "swagger"
      ? `${BACKEND}/docs?transport=rest`
      : `${BACKEND}/redoc`;

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold">API Docs</h1>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setView("swagger")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              view === "swagger"
                ? "border-accent bg-accent/10 text-accent"
                : "border-surface-border text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <Code2 className="w-3.5 h-3.5" />
            Swagger UI
          </button>
          <button
            onClick={() => setView("redoc")}
            className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border transition-colors ${
              view === "redoc"
                ? "border-accent bg-accent/10 text-accent"
                : "border-surface-border text-zinc-400 hover:text-zinc-200"
            }`}
          >
            <BookOpen className="w-3.5 h-3.5" />
            ReDoc
          </button>
          <a
            href={`${BACKEND}/docs`}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 px-3 py-1.5 text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Open in browser
          </a>
        </div>
      </div>

      <div className="flex-1 bg-surface-light border border-surface-border rounded-xl overflow-hidden">
        <div className="flex gap-2 px-4 py-2 border-b border-surface-border overflow-x-auto">
          {["GET /api/capabilities", "GET /api/health", "GET /api/opencode/status", "GET /api/fleet", "GET /api/tools", "GET /api/settings", "PUT /api/settings"].map((ep) => (
            <span
              key={ep}
              className="text-xs font-mono text-zinc-500 bg-zinc-800 px-2 py-1 rounded whitespace-nowrap"
            >
              {ep}
            </span>
          ))}
        </div>
        <div className="w-full h-full min-h-[500px]">
          <iframe
            src={src}
            className="w-full h-full border-0"
            title="API Documentation"
            sandbox="allow-scripts allow-same-origin"
          />
        </div>
      </div>
    </div>
  );
}
