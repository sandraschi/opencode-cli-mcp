# Eternal Session Memory

**The superpower nobody else has.** opencode records **every conversation and
every agent run** — since the day you installed it — into one SQLite database on
your machine. No other agentic IDE does this:

- ChatGPT / Claude.ai / Gemini chats are per-session web silos — gone when the tab closes.
- Cursor / VS Code Copilot keep history per project, usually truncated, rarely searchable.
- opencode keeps the **full transcript of everything** in
  `~/.local/share/opencode/opencode.db` — session metadata, every message, every
  tool call, file diffs, tokens, cost — 2,000+ sessions and 500k+ messages on a
  typical install.

With opencode-cli-mcp you can **ask that memory anything**:

> "What were we discussing last December about santiclaus-mcp?"

...and get the actual session, transcript, and file changes — not a blank stare.

## Why this works

| Other IDEs | opencode |
|------------|----------|
| Sessions are throwaway UI state | Sessions are a **database** (SQLite, `session` / `message` / `part` tables) |
| History truncates / paginates away | Full transcripts persist, FTS-indexed for search |
| No API to query past work | Local HTTP API (`opencode serve`) + direct DB access |
| Nothing you can do when it borks | Backups + restore (this app's `opencode_backups` tool) |

## How to use it (from any Claude/Cursor/opencode session)

### 1. Ask the memory — wayback find

```
opencode_depot(action="search", query="santiclaus")
```

Searches **all transcripts and titles** (SQLite FTS5) and returns matching
sessions with snippets and timestamps. The live counterpart over the API:

```
opencode_sessions(action="grep", query="santiclaus", limit=50)
```

### 1b. Semantic recall (RAG) — when you don't remember the words

```
opencode_depot(action="rag_index")                 # build the index once (embeddings)
opencode_depot(action="rag", query="the pricing discussion we had for the santa tool")
opencode_depot(action="rag_status")                # index state / availability
```

RAG searches **by meaning**, not keywords: describe the conversation in your own
words and get the sessions that are semantically closest, even when they never
contain any of your query's words. Requires `uv sync --extra rag` (LanceDB +
fastembed). The Depot webapp page has the same semantic search.

### 2. Open the conversation

```
opencode_depot(action="list", search="santiclaus")     # find the session id
opencode_sessions(action="get", session_id="ses_...")  # metadata
opencode_sessions(action="messages", session_id="ses_...", limit=100)  # the transcript
opencode_sessions(action="diff", session_id="ses_...") # files created/modified/deleted
```

### 3. Take it out — export

```
opencode_sessions(action="export", session_id="ses_...", format="markdown")
opencode_sessions(action="export", session_id="ses_...", format="html")
```

Every session can be rendered as a readable document, so "what did we decide in
December" becomes a file you can read, paste, or archive.

### 4. Maintain the memory — rename, archive, delete

```
opencode_sessions(action="rename", session_id="ses_...", title="santiclaus-mcp research")
opencode_depot(action="archive", session_id="ses_...")       # hide from active list
opencode_depot(action="unarchive", session_id="ses_...")
opencode_sessions(action="delete", session_id="ses_...", confirm=True)
```

### 5. Protect it — backups

The database is the accumulated memory of every session you ever ran. Don't lose
it to a bad plugin, a botched experiment, or a disk problem:

```
opencode_backups(action="status")
opencode_backups(action="create", kind="all")        # db + config snapshot
opencode_backups(action="list")
opencode_backups(action="restore", name="opencode-db-....sqlite3", confirm=True)
```

Autobackup runs on backend start and every 24h (configurable) with rotation
(10 kept per kind) and a disk-space guard. See the webapp **Backups** page
(`/backups`) for the visual overview.

## Where it lives

| Thing | Location |
|-------|----------|
| The memory | `~/.local/share/opencode/opencode.db` |
| The config | `~/.config/opencode/` |
| Backups | `~/.local/share/opencode-cli-mcp/backups/` |
| Webapp pages | Sessions (`/sessions`) · Depot (`/depot`) · Backups (`/backups`) |

## The workflow that makes it magic

```
"what were we talking about last december about santiclaus-mcp?"
   -> opencode_depot(action="search", query="santiclaus")        # keyword wayback find
   -> opencode_depot(action="rag", query="the santa claus mcp plan")  # semantic recall
   -> opencode_sessions(action="export", session_id=..., format="markdown")
   -> read the decision, continue where you left off
```

Cross-project, cross-week, cross-model — the memory is yours and it never forgets.
