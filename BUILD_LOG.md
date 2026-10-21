# Build Log - opencode-cli-mcp

Running record of release builds, the problems hit, and the fixes. Newest first.
Kept in-repo (not in mcd) because the useful detail is repo-specific.

---

## 0.2.10 - 2026-10-21 (release prep)

**Artifacts**

| Artifact | Size | Built from |
|----------|------|------------|
| `dist/opencode-cli-mcp-0.2.10.mcpb` | 106.3 KB (33 files, 314.9 KB unpacked) | `mcpb/pack.ps1` @ `1fdd796` |
| `dist/opencode-cli-mcp-0.2.10-setup.exe` | 12.93 MB | `native/build.ps1` (cargo release, 2m46s) |

Both built from a clean tree; versions agree across `pyproject.toml`,
`native/tauri.conf.json`, `mcpb/manifest.json` (0.2.10).

**Problems found and fixed**

1. **`mcpb/pack.ps1` names its output with a `v` prefix** (`opencode-cli-mcp-v0.2.10.mcpb`),
   which `check-release-gate.ps1` rejects (contract: `{repo}-{version}.mcpb`, version without
   `v`). Renamed in `dist/` after packing. The pack script itself is a fleet-standard file -
   not edited here; if this bites again, the naming belongs in the shared template.
2. **Stale artifact present:** `dist/` held a `v0.2.10.mcpb` built before the 2026-10-19
   changes (starring/tags/export/memops). Rebuilt from the current tree before renaming.
3. **README failed three release-gate checks** (build/clone steps present, no Releases link,
   no `setup.exe` mention). Quick Start rewritten as installer-first; dev setup now only
   points at `docs/DEVELOPMENT.md`.
4. **`scripts/cua-smoke.py` was v13**, below the gate's required `CUA_SMOKE_VERSION >= 15`.
   A perfect run would still have been rejected. Replaced with the v15 template from
   `mcp-central-docs/templates/tauri-native/scripts/` (adds `cua-result.json` output and
   sidebar-discovered nav pages).
5. **`just cua-nsis-test` did not exist** although the release docs reference it. Added the
   recipe + `scripts/just/cua-nsis-test.ps1` from the same template.

**Gates**

- `ruff` / `ruff format` / `biome` / `tsc` / `vite build`: clean.
- `pytest`: 192 passed, coverage 61.7% (gate 30%).
- `check-release-gate.ps1 -Local`: all checks pass except CUA (needs an interactive run).
- `pyright`: 41 errors, all pre-existing in `mcpb/verify_pack.py`, `scripts/cua-*.py`,
  `sidebar/sidebar_client.py`, `tests/test_rag.py`, `tests/test_share.py`; none in `src/`
  or `api/`. Not fixed in this build (separate cleanup).
- CUA-NSIS: **not yet run at the time of writing** - must pass on this exact installer
  before the GitHub release is created.

**Notes**

- The installer is unsigned. README states the SmartScreen "More info -> Run anyway" step.
- 0.2.10 deliberately keeps the 15 legacy atomic tool aliases; their removal is 0.3.0.
