import { useCallback, useEffect, useState } from "react";
import { motion } from "framer-motion";
import { ArchiveRestore, DatabaseBackup, HardDrive, RefreshCw, Settings2, Trash2 } from "lucide-react";
import { api, type BackupEntry, type BackupStatus } from "../services/api";

function fmtBytes(n: number): string {
  if (!n) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < units.length - 1) {
    v /= 1024;
    i += 1;
  }
  return `${v.toFixed(1)} ${units[i]}`;
}

export function Backups() {
  const [status, setStatus] = useState<BackupStatus | null>(null);
  const [backups, setBackups] = useState<BackupEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ kind: "ok" | "err"; text: string } | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [s, l] = await Promise.all([api.backupsStatus(), api.backupsList()]);
      setStatus(s.data);
      setBackups(l.data.backups);
    } catch (e) {
      setNotice({ kind: "err", text: `Failed to load backup status: ${e instanceof Error ? e.message : String(e)}` });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const doAction = async (id: string, fn: () => Promise<unknown>, okText: string) => {
    setBusy(id);
    setNotice(null);
    try {
      await fn();
      setNotice({ kind: "ok", text: okText });
      await load();
    } catch (e) {
      setNotice({ kind: "err", text: `${e instanceof Error ? e.message : String(e)}` });
    } finally {
      setBusy(null);
    }
  };

  const createBackup = (kind: string, label: string) =>
    doAction(`create-${kind}`, () => api.backupsCreate(kind), `${label} backup created`);

  const restoreBackup = (b: BackupEntry) => {
    const what = b.kind === "db" ? "database" : "config";
    const extra =
      b.kind === "db"
        ? " The opencode app must be stopped (or force-restore, which the live server may overwrite)."
        : "";
    if (
      !window.confirm(`Restore ${what} from ${b.name}? Current ${what} is kept as a pre-restore backup first.${extra}`)
    )
      return;
    doAction(`restore-${b.name}`, () => api.backupsRestore(b.name), `Restored ${b.name}`);
  };

  const deleteBackup = (b: BackupEntry) => {
    if (!window.confirm(`Delete backup ${b.name} (${fmtBytes(b.size)})?`)) return;
    doAction(`del-${b.name}`, () => api.backupsDelete(b.name), `Deleted ${b.name}`);
  };

  const freePct =
    status && status.free_bytes > 0
      ? Math.min(100, (status.free_bytes / (status.free_bytes + status.min_free_bytes)) * 100)
      : 0;

  return (
    <div data-testid="backups-page">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Backups</h1>
        <button
          type="button"
          data-testid="backups-refresh"
          onClick={load}
          className="flex items-center gap-2 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors"
          title="Refresh backup status"
          aria-label="Refresh backup status"
        >
          <RefreshCw className="w-4 h-4" />
          Refresh
        </button>
      </div>

      {notice && (
        <div
          data-testid="backups-notice"
          className={`mb-4 px-3 py-2 text-sm rounded-lg border ${
            notice.kind === "ok"
              ? "border-emerald-700 bg-emerald-950 text-emerald-300"
              : "border-red-800 bg-red-950 text-red-300"
          }`}
        >
          {notice.text}
        </div>
      )}

      {loading && !status ? (
        <div className="text-zinc-500">Loading backup status...</div>
      ) : (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            <div className="rounded-xl border border-surface-border bg-surface-light p-4" data-testid="backups-stat-db">
              <div className="flex items-center gap-2 text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                <DatabaseBackup className="w-4 h-4" />
                Database
              </div>
              <div className="mt-2 font-mono text-xs text-zinc-400 break-all">{status?.db_path}</div>
              <div className="mt-1 text-sm">
                <span className={status?.db_exists ? "text-emerald-400" : "text-red-400"}>
                  {status?.db_exists ? fmtBytes(status.db_size) : "missing"}
                </span>
                <span className="text-zinc-500"> · {status?.counts.db ?? 0} backups</span>
              </div>
            </div>
            <div
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="backups-stat-config"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                <Settings2 className="w-4 h-4" />
                Config
              </div>
              <div className="mt-2 font-mono text-xs text-zinc-400 break-all">{status?.config_dir}</div>
              <div className="mt-1 text-sm">
                <span className={status?.config_exists ? "text-emerald-400" : "text-red-400"}>
                  {status?.config_exists ? "present" : "missing"}
                </span>
                <span className="text-zinc-500"> · {status?.counts.config ?? 0} backups</span>
              </div>
            </div>
            <div
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="backups-stat-space"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                <HardDrive className="w-4 h-4" />
                Storage
              </div>
              <div className="mt-2 text-sm">
                <span className="text-zinc-200">{fmtBytes(status?.free_bytes ?? 0)} free</span>
                <span className="text-zinc-500"> · min {fmtBytes(status?.min_free_bytes ?? 0)}</span>
              </div>
              <div className="mt-2 h-1.5 rounded-full bg-zinc-800 overflow-hidden">
                <div
                  className={`h-full rounded-full ${freePct < 30 ? "bg-red-500" : freePct < 60 ? "bg-amber-500" : "bg-emerald-500"}`}
                  style={{ width: `${freePct}%` }}
                />
              </div>
            </div>
            <div
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="backups-stat-last"
            >
              <div className="flex items-center gap-2 text-sm font-semibold text-zinc-400 uppercase tracking-wider">
                <ArchiveRestore className="w-4 h-4" />
                Latest
              </div>
              <div className="mt-2 font-mono text-xs text-zinc-400 break-all">
                {status?.last_backup ? status.last_backup.name : "no backups yet"}
              </div>
              <div className="mt-1 text-xs text-zinc-500">
                {status?.last_backup?.created ? new Date(status.last_backup.created).toLocaleString() : "run one below"}
              </div>
              {status?.last_autobackup && (
                <div className="mt-1 text-xs text-zinc-500" data-testid="backups-autobackup">
                  autobackup{" "}
                  {status.autobackup_interval_hours > 0 ? `every ${status.autobackup_interval_hours}h` : "disabled"} ·{" "}
                  {status.last_autobackup.results?.some((r) => !r.ok)
                    ? "last run had errors"
                    : `last run ${status.last_autobackup.timestamp ? new Date(status.last_autobackup.timestamp).toLocaleString() : ""}`}
                </div>
              )}
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 mb-6">
            <button
              type="button"
              data-testid="backups-create-db"
              onClick={() => createBackup("db", "Database")}
              disabled={busy !== null}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-amber-600 hover:bg-amber-500 disabled:opacity-50 rounded-lg transition-colors"
            >
              <DatabaseBackup className="w-4 h-4" />
              {busy === "create-db" ? "Backing up..." : "Backup DB now"}
            </button>
            <button
              type="button"
              data-testid="backups-create-config"
              onClick={() => createBackup("config", "Config")}
              disabled={busy !== null}
              className="flex items-center gap-2 px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 disabled:opacity-50 rounded-lg transition-colors"
            >
              <Settings2 className="w-4 h-4" />
              {busy === "create-config" ? "Backing up..." : "Backup Config now"}
            </button>
            <button
              type="button"
              data-testid="backups-prune"
              onClick={() => {
                if (!window.confirm(`Prune backups beyond retention (${status?.retention ?? 10} per kind)?`)) return;
                doAction("prune", () => api.backupsPrune(), "Old backups pruned");
              }}
              disabled={busy !== null}
              className="px-4 py-2 text-sm bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 rounded-lg transition-colors"
            >
              Prune old
            </button>
            <span className="text-xs text-zinc-500">
              retention: {status?.retention ?? 10} per kind · autobackup interval:{" "}
              {status?.autobackup_interval_hours ?? 24}h
            </span>
          </div>

          <div className="rounded-xl border border-surface-border bg-surface-light overflow-hidden">
            <div className="px-4 py-3 text-sm font-semibold text-zinc-400 uppercase tracking-wider border-b border-surface-border">
              Backups ({backups.length})
            </div>
            {backups.length === 0 ? (
              <div className="px-4 py-8 text-center text-zinc-500" data-testid="backups-empty">
                No backups yet. Create one to protect the opencode database and config against corruption or failed
                experiments.
              </div>
            ) : (
              <div className="divide-y divide-surface-border">
                {backups.map((b) => (
                  <motion.div
                    key={b.name}
                    data-testid={`backup-item-${b.name}`}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex items-center justify-between gap-3 px-4 py-3"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span
                          className={`px-1.5 py-0.5 text-[10px] font-bold uppercase rounded ${
                            b.kind === "db" ? "bg-amber-900/60 text-amber-300" : "bg-zinc-800 text-zinc-300"
                          }`}
                        >
                          {b.kind}
                        </span>
                        <span className="font-mono text-xs text-zinc-300 truncate">{b.name}</span>
                      </div>
                      <div className="mt-0.5 text-xs text-zinc-500">
                        {fmtBytes(b.size)}
                        {b.created ? ` · ${new Date(b.created).toLocaleString()}` : ""}
                      </div>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        data-testid={`backup-restore-${b.name}`}
                        onClick={() => restoreBackup(b)}
                        disabled={busy !== null}
                        className="p-1.5 rounded-md text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 transition-colors"
                        title={`Restore ${b.kind} from this backup`}
                        aria-label={`Restore ${b.name}`}
                      >
                        <ArchiveRestore className="w-4 h-4" />
                      </button>
                      <button
                        type="button"
                        data-testid={`backup-delete-${b.name}`}
                        onClick={() => deleteBackup(b)}
                        disabled={busy !== null}
                        className="p-1.5 rounded-md text-zinc-400 hover:text-red-400 hover:bg-zinc-800 transition-colors"
                        title="Delete backup file"
                        aria-label={`Delete ${b.name}`}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
