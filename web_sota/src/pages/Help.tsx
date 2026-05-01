import { useEffect, useState } from "react";
import { BookOpen, FileText, ExternalLink, ChevronRight } from "lucide-react";

const DOCS = [
  { path: "README.md", label: "Project Overview" },
  { path: "docs/integration-guide.md", label: "Integration Guide" },
  { path: "CLAUDE.md", label: "CLAUDE.md" },
];

export function Help() {
  const [selected, setSelected] = useState(DOCS[0].path);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    const path = selected === "README.md" ? "/README.md" : `/${selected}`;
    fetch(path)
      .then((r) => r.text())
      .then((text) => {
        setContent(text);
        setLoading(false);
      })
      .catch(() => {
        setContent("Failed to load document.");
        setLoading(false);
      });
  }, [selected]);

  return (
    <div className="flex gap-6 h-full">
      <div className="w-56 flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <BookOpen className="w-4 h-4" />
          Documents
        </h2>
        <div className="space-y-1">
          {DOCS.map((doc) => (
            <button
              key={doc.path}
              onClick={() => setSelected(doc.path)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                selected === doc.path
                  ? "bg-accent/10 text-accent"
                  : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
              }`}
            >
              <ChevronRight className={`w-3 h-3 flex-shrink-0 ${selected === doc.path ? "text-accent" : "text-transparent"}`} />
              <FileText className="w-4 h-4 flex-shrink-0" />
              <span className="truncate">{doc.label}</span>
            </button>
          ))}
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
        <div className="p-4 border-b border-surface-border">
          <h3 className="font-semibold text-sm">{DOCS.find((d) => d.path === selected)?.label}</h3>
        </div>
        <div className="p-4 overflow-auto max-h-[calc(100vh-12rem)]">
          {loading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-4 bg-zinc-800 rounded animate-pulse" style={{ width: `${60 + i * 10}%` }} />
              ))}
            </div>
          ) : (
            <pre className="text-sm text-zinc-300 font-mono whitespace-pre-wrap">{content}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
