# Build Log - opencode-cli-mcp

Running record of release builds, the problems hit, and the fixes. Newest first.
Kept in-repo (not in mcd) because the useful detail is repo-specific.

---

## 0.2.11 - 2026-10-21

**Purpose:** close the one vacuous gate check. 0.2.10's CUA run reported
`backend_receipt_proof: true` because the repo had no request-log endpoint -
the phase skips on 404 and still marks itself passed. That is exactly the
false-positive class the phase exists to prevent, so it got a real endpoint.

**Change:** `GET /api/v1/request-log` -> `{count, requests[]}` fed by an ASGI
middleware (method, path, status, duration; newest 500; process-lifetime).
The endpoint exempts itself so polling cannot be its own evidence.

**Result:** CUA 12/12 on the exact installer, and the receipt phase now reports
**48 requests logged during the 17-page nav walk** - real webview traffic, not a
skip. That also independently confirms the 0.2.10 Tauri API-base fix.

**Artifacts:** `opencode-cli-mcp-0.2.11-setup.exe` 116.8 MB,
`opencode-cli-mcp-0.2.11.mcpb` 109.1 KB.

**Build incident worth remembering:** the first 0.2.11 installer embedded a
backend built before the endpoint existed (source was right; the frozen exe was
stale), so CUA legitimately got 404 and the dashboard showed "Backend
unreachable". Lesson: after touching backend routes, verify the *embedded*
binary answers the new route - not just that the source tests pass. The rebuild
at 20:11 was checked with a direct HTTP call to
`native/resources/opencode-cli-mcp-backend.exe` before installing.

**Also in this build:** CUA sidebar enumeration retries once after 4s; the first
paint after install occasionally had no links yet and failed the nav walk.

**Follow-up (same day, no app change):** the three items previously listed as
"known, not fixed" are closed:
- `pyright` is clean repo-wide (was 41 errors). Fixes were type-only: `cfg()`
  returns `Any`, `fatal`/`phase_fail` are `NoReturn`, `pywinauto` is an `Any`
  sentinel, a `mod.__file__` guard, `_utf8_stdout()` via `getattr`, and
  `assert table is not None` in the RAG/share tests.
- Uninstaller check polls registry + install dir for up to 25s instead of one
  2s sample, because NSIS returns before deletion finishes. It now reports
  "registry + install dir gone" on a clean uninstall.
- `mcpb/pack.ps1` emits `{repo}-{version}.mcpb` (no `v`) per the release
  contract; the manual rename after every pack is gone. Same fix applied to
  `mcp-central-docs/templates/mcpb-pack.ps1` so new repos inherit it.

---

## 0.2.10 - 2026-10-21

**Artifacts**

| Artifact | Size | Source |
|----------|------|--------|
| `dist/opencode-cli-mcp-0.2.10.mcpb` | 108.0 KB | `mcpb/pack.ps1`, packed last |
| `dist/opencode-cli-mcp-0.2.10-setup.exe` | 116.8 MB | `native/build.ps1` (cargo 1m08s, PyInstaller ~90s) |

Installer SHA256: `6649e3bbcee68e3a93bb11c25f84bc55fe93fcba3d01c06b456bf8ecc546796`
(that is the exact file CUA tested). Versions agree across `pyproject.toml`,
`native/tauri.conf.json` and `mcpb/manifest.json` (0.2.10).

**Blockers found and fixed**

1. **PyInstaller was not a project dependency.** `uv run pyinstaller` therefore
   ran a standalone copy whose interpreter could not see `.venv`, so Analysis
   reported `missing module named fastapi/uvicorn` and produced a 10.7 MB
   bundle that died at the first import. Fixed by declaring `pyinstaller` in
   the dev group and building with `.venv\Scripts\python.exe -m PyInstaller`
   in `native/build.ps1`. The working backend is 114 MB.
2. **The spec stripped every `.dist-info`.** Libraries that read their own
   metadata at import then crashed one after another: `pydantic` probing
   `email_validator`, then `opentelemetry` entry points. Both surfaced as
   opaque `StopIteration` tracebacks. Fixed by keeping metadata (the few MB
   is cheaper than whack-a-mole) and adding real `uvicorn` hiddenimports.
3. **`services/api.ts` hardcoded `/api`.** In the Tauri asset protocol a
   relative request returns `index.html`, so every depot/backup/usage page
   failed with `Unexpected token '<'`. It now imports the Tauri-aware root
   from `lib/api.ts` and rejects non-JSON responses explicitly.
4. **CUA tooling was missing from the venv** (`pytesseract`), so every page
   OCR'd empty and a good build failed. Declared `pywinauto`, `pytesseract`
   and `pillow` in the dev group.
5. **The CUA fail-keyword list matched bare `404`.** A backup filename
   (`opencode-db-20261019-111404-...sqlite3`) tripped it. Now matches
   `404 not found` / `404 error`.
6. **`scripts/cua-smoke.py` was v13**, below the gate's `>= 15` floor; synced
   to the template and added the missing `just cua-nsis-test` recipe.
7. **README failed three gate checks** (build steps, no Releases link, no
   `setup.exe`); rewritten installer-first.

**Tool surface in this build**

`opencode_runs start` gained `model`, `agent`, `variant`, `thinking`, `auto`,
`session_id` / `continue_session` / `fork` and `files` - without them every run
used the default model and unattended runs stalled on permission prompts.

**CUA-NSIS**

12/12 phases, `all_passed: true`, `pywinauto: true`, 17/17 sidebar pages
navigated, backend up, uninstall exit 0. One caveat: backend-receipt proof
reports `true` but is skipped - this repo has no request-log endpoint yet, so
it is a vacuous pass, not evidence. Everything else is real.

**Known, not fixed at 0.2.10:** pyright (41 errors), the uninstaller's
"may still be registered" warning, and the `v`-prefixed mcpb filename.
All three were fixed the same day - see the 0.2.11 follow-up note above.


**Provenance note:** both artifacts were built from a clean tree at
`1ec6c50`. The only commits after that are this log and the `.gitignore`
entry, neither of which enters the bundles.
