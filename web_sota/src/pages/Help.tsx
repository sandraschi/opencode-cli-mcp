import { useEffect, useState, useMemo } from "react";
import {
  BookOpen,
  FileText,
  ExternalLink,
  Search,
  ChevronRight,
  Loader2,
} from "lucide-react";
import { api } from "../services/api";

import type { DocEntry, DocContent } from "../services/api";

function renderMarkdown(md: string): string {
  let html = md
    .split("\n")
    .map((line) => {
      if (line.startsWith("### ")) return `<h3 class="text-base font-semibold text-zinc-200 mt-5 mb-2">${line.slice(4)}</h3>`;
      if (line.startsWith("## ")) return `<h2 class="text-lg font-semibold text-zinc-100 mt-6 mb-3 border-b border-zinc-800 pb-1">${line.slice(3)}</h2>`;
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
    const headers = headerRow.split("|").map((h: string) => h.trim()).filter(Boolean);
    const rows = bodyRows.trim().split("\n").map((r: string) =>
      r.split("|").map((c: string) => c.trim()).filter(Boolean),
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
    const escaped = code
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
    return `<pre class="bg-zinc-900 border border-zinc-800 rounded-lg p-4 my-3 overflow-x-auto"><code class="text-xs text-zinc-300 font-mono leading-relaxed">${escaped}</code></pre>`;
  });

  return html;
}

export function Help() {
  const [docs, setDocs] = useState<DocEntry[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [docContent, setDocContent] = useState<DocContent | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadingDoc, setLoadingDoc] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

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
  }, []);

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

  const filteredDocs = useMemo(
    () =>
      docs.filter(
        (d) =>
          d.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          d.id.toLowerCase().includes(searchQuery.toLowerCase()),
      ),
    [docs, searchQuery],
  );

  const renderedHtml = useMemo(
    () => (docContent ? renderMarkdown(docContent.content) : ""),
    [docContent],
  );

  return (
    <div className="flex gap-6 h-full">
      <div className="w-64 flex-shrink-0">
        <h2 className="text-sm font-semibold text-zinc-400 uppercase tracking-wider mb-3 flex items-center gap-2">
          <BookOpen className="w-4 h-4" />
          Documents
          <span className="text-xs text-zinc-600 font-normal">({docs.length})</span>
        </h2>
        <div className="relative mb-3">
          <Search className="absolute left-2.5 top-2.5 w-3.5 h-3.5 text-zinc-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search docs..."
            className="w-full bg-zinc-800 border border-zinc-700 rounded-lg pl-8 pr-3 py-2 text-xs focus:outline-none focus:border-accent/50"
          />
        </div>
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
                key={doc.id}
                onClick={() => setSelected(doc.id)}
                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-left transition-colors ${
                  selected === doc.id
                    ? "bg-accent/10 text-accent"
                    : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50"
                }`}
              >
                <ChevronRight
                  className={`w-3 h-3 flex-shrink-0 ${
                    selected === doc.id ? "text-accent" : "text-transparent"
                  }`}
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
          {docContent && (
            <span className="text-xs text-zinc-600">{docContent.id}</span>
          )}
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
            <div
              className="prose-custom text-sm leading-relaxed"
              dangerouslySetInnerHTML={{ __html: renderedHtml }}
            />
          ) : (
            <p className="text-sm text-zinc-500">Select a document from the sidebar.</p>
          )}
        </div>
      </div>
    </div>
  );
}
