# opencode-cli-mcp - Improvement Plan

**Date:** 2026-08-02
**Status:** Active development (0.2.x line)

Living document. Dated superseded plans are deleted, not kept alongside (the
Help page auto-lists every `docs/*.md`, so stale docs pollute it).

---

## Recent wins (0.2.4 - 0.2.6, for context)

- Live session rename/delete via the serve API (opencode's own UI only offers
  Open/Archive), offline depot variants, webapp buttons.
- Eternal Session Memory: FTS5 wayback find, semantic RAG, code index
  (patch paths + edit tool inputs), backups (db + config, rotation, disk
  guard, autobackup 24h), `docs/ETERNAL_MEMORY.md`.
- RAG delete-then-add fix (re-index no longer duplicates chunks).

## Improvement backlog (current)

### RAG / code index

1. **Code index migration** (done 2026-08-02): `code_index` rebuilds the
   code table from all sessions without re-embedding text chunks
   (`reindex_code_all`, delete-then-add per session). Next: surface rebuild
   progress on the Depot page (combined index pass already shows it).
2. **Code-capable embedder for the code table**: bge-small-en-v1.5 is
   prose-tuned; evaluate bge-m3 / Qwen3-Embedding / jina code task for the
   `session_code` table (text table can keep the cheap model).
3. **Git/changelog hybrid index** ("superclever" idea): RAG over `git log`
   diffs + commit messages for fuzzy recall of committed work; live exact
   queries stay with git-github-mcp (`git log -S`). Covers the committed
   half of history; the depot covers the never-committed half.
4. **Single-watermark waste**: a session whose only change is code re-walks
   its text chunks too (delete-then-add). Split watermarks per table.
5. **Code result UX**: pagination, dedupe by session, "open transcript"
   linking; per-path aggregation ("all sessions that touched X").
6. **Part-type stats tool**: report tool/reasoning/patch volume per session
   to inform filter tuning (current text-only filter keeps ~9% of parts).

### Backups

7. **Backup size reality**: the depot is 5.6 GB; a full SQLite online-backup
   snapshot takes minutes. Add a size warning, run in background with
   progress, and evaluate throttled `VACUUM INTO` or schedule-based backups.
8. **Settings UI for backup knobs** (interval, retention, min free) instead
   of env-only; restore dry-run preview.
9. **Guard against backup/index concurrency** (both hammer disk + CPU).

### opencode upstream gaps we compensate for

10. opencode UI: no session rename/delete, no unarchive, no backup. Track
    upstream (sst/opencode) - if they land these, our depot/backups stay as
    the offline/fleet layer.

### Webapp

11. Sessions page detail is raw JSON - add a readable transcript viewer with
    inline search + export button.
12. Playwright e2e for the Backups page and the Depot code tab.
13. Verify new pages inside the Tauri/NSIS build (embedded backend).

### Fleet integration

14. Depot stats alert: 5.6 GB DB and growing - surface size/watermark
    warnings on the Dashboard and in `opencode_system(status)`.
15. advanced-memory interop: push "what did we work on" digests from the
    depot into advanced-memory-mcp notes automatically.

---

## How to keep this current

- Delete the dated file when it ages out; rewrite as `docs/IMPROVEMENTS.md`
  (undated living doc) so the README/Help link never breaks.
- Check off items in the same commit that implements them.
