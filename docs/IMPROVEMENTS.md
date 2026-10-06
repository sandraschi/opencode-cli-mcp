# opencode-cli-mcp - Improvement Plan

**Date:** 2026-08-02
**Status:** Active development (0.2.x line)

Living document. Dated superseded plans are deleted, not kept alongside (the
Help page auto-lists every `docs/*.md`, so stale docs pollute it).

---

## Recent wins (0.2.4 - 0.2.6, for context)

- Live session rename/delete via the serve API (opencode's own UI only offers
  Open/Archive), offline depot variants, webapp buttons.
- Eternal Session Memory: LIKE-based wayback find, semantic RAG, code index
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
6. **Part-type stats tool** (done 2026-10-06): `depot_stats` returns
   `part_types` (top 8 by volume) and the Dashboard shows the part mix.

### Backups

7. **Backup size reality**: the depot is ~11 GB (5.6 GB in Aug 2026, still
   growing); a full SQLite online-backup snapshot takes minutes. Add a size warning, run in background with
   progress, and evaluate throttled `VACUUM INTO` or schedule-based backups.
8. **Settings UI for backup knobs** (interval, retention, min free) instead
   of env-only; restore dry-run preview.
9. **Guard against backup/index concurrency** (both hammer disk + CPU).

### Indexing robustness

10. **Reindex wedge observed (2026-08-02)**: `rag_index`/`code_index` run as
    in-process background tasks; during a full code-table rebuild the backend
    event loop wedged (health polls timed out) until the process was killed.
    Move heavy index passes to a subprocess (or throttle + watchdog) so the
    API stays responsive; resume/checkpoint the walk so a killed pass can
    continue instead of restarting. (Partly addressed 2026-10-05/06: all
    depot sqlite now runs in worker threads and RAG index passes already run
    via `asyncio.to_thread` - a full rebuild can still saturate disk/CPU, so
    subprocess isolation + resume remain open.)

### opencode upstream gaps we compensate for

11. opencode UI: no session rename/delete, no unarchive, no backup. Track
    upstream (sst/opencode) - if they land these, our depot/backups stay as
    the offline/fleet layer.

### Webapp

12. **Sessions transcript viewer** (done 0.2.8): readable Overview /
    Transcript / Diff tabs with inline search + markdown export replaced the
    raw JSON dump.
13. Playwright e2e for the Backups page and the Depot code tab.
14. Verify new pages inside the Tauri/NSIS build (embedded backend).

### Fleet integration

15. Depot stats alert: ~11 GB DB and growing - size is surfaced on the
    Dashboard DB card since 2026-10-06; watermark/index-staleness warnings
    still open.
16. advanced-memory interop: push "what did we work on" digests from the
    depot into advanced-memory-mcp notes automatically.

---

## How to keep this current

- Delete the dated file when it ages out; rewrite as `docs/IMPROVEMENTS.md`
  (undated living doc) so the README/Help link never breaks.
- Check off items in the same commit that implements them.
