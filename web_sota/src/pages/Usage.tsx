import { useCallback, useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Download, Loader2, RefreshCw } from "lucide-react";
import { api, type UsageSeries } from "../services/api";

const DAY_OPTIONS = [7, 30, 90, 365];

function fmtCompact(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(Math.round(n));
}

interface SeriesDef {
  key: keyof UsageSeries["buckets"][number];
  label: string;
  color: string;
}

function TimeChart({
  buckets,
  series,
  height = 220,
  stacked = false,
}: {
  buckets: UsageSeries["buckets"];
  series: SeriesDef[];
  height?: number;
  stacked?: boolean;
}) {
  const width = 900;
  const padL = 44;
  const padR = 12;
  const padT = 12;
  const padB = 24;
  const n = buckets.length;

  const { maxVal, lines } = useMemo(() => {
    const rawMax = Math.max(...buckets.flatMap((b) => series.map((s) => Number(b[s.key]) || 0)), 1);
    const step = rawMax > 1000 ? 1000 : rawMax > 100 ? 100 : rawMax > 10 ? 10 : 1;
    const maxVal = Math.ceil(rawMax / step) * step;

    const stackTotals = buckets.map((b) => series.reduce((acc, s) => acc + (Number(b[s.key]) || 0), 0));
    const overallMax = stacked ? Math.max(...stackTotals, 1) : maxVal;

    const toX = (i: number) => padL + (n <= 1 ? 0 : (i / (n - 1)) * (width - padL - padR));
    const toY = (v: number) => padT + (1 - v / overallMax) * (height - padT - padB);

    const lines = series.map((s) => {
      const points = buckets.map((b, i) => ({ x: toX(i), y: toY(Number(b[s.key]) || 0) }));
      return { def: s, points };
    });
    return { maxVal: overallMax, lines };
  }, [buckets, series, stacked, height, n]);

  const gridLines = useMemo(() => {
    const ticks = 4;
    return Array.from({ length: ticks + 1 }, (_, i) => {
      const v = (maxVal / ticks) * i;
      const y = padT + (1 - i / ticks) * (height - padT - padB);
      return { v, y };
    });
  }, [maxVal, height]);

  const pathOf = (points: Array<{ x: number; y: number }>) =>
    points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");

  const areaPath = (points: Array<{ x: number; y: number }>) => {
    if (points.length === 0) return "";
    const last = points[points.length - 1];
    const first = points[0];
    return `${pathOf(points)}L${last.x.toFixed(1)},${(height - padB).toFixed(1)}L${first.x.toFixed(1)},${(height - padB).toFixed(1)}Z`;
  };

  // x labels: ~6 evenly spaced day labels
  const xLabels = useMemo(() => {
    if (n === 0) return [];
    const count = Math.min(6, n);
    const step = Math.max(1, Math.floor((n - 1) / (count - 1)));
    return Array.from({ length: count }, (_, i) => {
      const idx = Math.min(n - 1, i * step);
      return { label: buckets[idx].day.slice(5), x: padL + (idx / (n - 1)) * (width - padL - padR) };
    });
  }, [buckets, n]);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full"
      role="img"
      aria-label={series.map((s) => s.label).join(", ")}
    >
      <title>{series.map((s) => s.label).join(" · ")}</title>
      {gridLines.map((g) => (
        <g key={g.v}>
          <line x1={padL} x2={width - padR} y1={g.y} y2={g.y} stroke="#27272a" strokeWidth={1} />
          <text x={padL - 6} y={g.y + 3} textAnchor="end" className="fill-zinc-600 text-[10px] font-mono">
            {fmtCompact(g.v)}
          </text>
        </g>
      ))}
      {xLabels.map((l) => (
        <text key={l.label} x={l.x} y={height - 6} textAnchor="middle" className="fill-zinc-600 text-[10px] font-mono">
          {l.label}
        </text>
      ))}
      {lines.map(({ def, points }) => (
        <g key={def.key}>
          <path d={areaPath(points)} fill={def.color} opacity={0.18} stroke="none" />
          <path d={pathOf(points)} fill="none" stroke={def.color} strokeWidth={1.8} strokeLinejoin="round" />
        </g>
      ))}
    </svg>
  );
}

export function Usage() {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<UsageSeries | null>(null);
  const [loading, setLoading] = useState(true);
  const [showCache, setShowCache] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async (d: number) => {
    setLoading(true);
    setError("");
    try {
      const r = await api.depotUsage(d);
      setData(r.data);
    } catch (e) {
      setError(`Failed to load usage: ${e instanceof Error ? e.message : "unknown"}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load(days);
  }, [days, load]);

  const exportCsv = useCallback(() => {
    if (!data) return;
    const header = [
      "day",
      "messages",
      "tokens_input",
      "tokens_output",
      "tokens_reasoning",
      "tokens_cache_read",
      "tokens_cache_write",
      "cost_stored_usd",
      "cost_est_usd",
    ];
    const rows = data.buckets.map((b) =>
      [
        b.day,
        b.messages,
        b.tokens_input,
        b.tokens_output,
        b.tokens_reasoning,
        b.tokens_cache_read,
        b.tokens_cache_write,
        b.cost_stored.toFixed(4),
        b.cost_est.toFixed(4),
      ].join(","),
    );
    const csv = [header.join(","), ...rows].join("\n");
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `opencode-usage-${data.buckets[0]?.day ?? "all"}-to-${data.buckets[data.buckets.length - 1]?.day ?? "now"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [data]);

  const tokenSeries: SeriesDef[] = [
    { key: "tokens_input", label: "input", color: "#3b82f6" },
    { key: "tokens_output", label: "output", color: "#22c55e" },
    { key: "tokens_reasoning", label: "reasoning", color: "#a855f7" },
    ...(showCache ? [{ key: "tokens_cache_read", label: "cache read", color: "#f59e0b" } as SeriesDef] : []),
  ];

  const costSeries: SeriesDef[] = [
    { key: "cost_est", label: "est (base rates)", color: "#3b82f6" },
    { key: "cost_stored", label: "stored (variant)", color: "#f59e0b" },
  ];

  const cumCost = useMemo(() => {
    if (!data) return [];
    let acc = 0;
    return data.buckets.map((b) => {
      acc += b.cost_est;
      return acc;
    });
  }, [data]);

  const maxCum = Math.max(...cumCost, 0.01);

  return (
    <div data-testid="usage-page">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Usage</h1>
        <div className="flex items-center gap-2">
          <div className="flex rounded-lg border border-surface-border overflow-hidden">
            {DAY_OPTIONS.map((d) => (
              <button
                key={d}
                type="button"
                data-testid={`usage-days-${d}`}
                onClick={() => setDays(d)}
                className={`px-3 py-1.5 text-xs transition-colors ${
                  days === d ? "bg-accent/20 text-accent" : "bg-surface-light text-zinc-500 hover:text-zinc-300"
                }`}
              >
                {d}d
              </button>
            ))}
          </div>
          <button
            type="button"
            data-testid="usage-refresh"
            onClick={() => load(days)}
            className="p-2 rounded-lg bg-zinc-800 hover:bg-zinc-700 transition-colors"
            title="Refresh"
            aria-label="Refresh usage"
          >
            <RefreshCw className="w-4 h-4" />
          </button>
          <button
            type="button"
            data-testid="usage-export"
            onClick={exportCsv}
            disabled={!data}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm bg-zinc-800 hover:bg-zinc-700 rounded-lg disabled:opacity-40 transition-colors"
            title="Export daily series as CSV"
          >
            <Download className="w-4 h-4" />
            CSV
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 px-3 py-2 text-sm rounded-lg border border-red-800 bg-red-950 text-red-300">{error}</div>
      )}

      {loading && !data ? (
        <div className="flex justify-center py-16 text-zinc-500">
          <Loader2 className="w-6 h-6 animate-spin" />
        </div>
      ) : data ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="usage-stat-tokens"
            >
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Tokens ({days}d)</div>
              <div className="text-xl font-semibold mt-0.5">
                {fmtCompact(data.totals.tokens_input + data.totals.tokens_output + data.totals.tokens_reasoning)}
              </div>
              <div className="text-xs text-zinc-500">
                in/out/reason · {fmtCompact(data.totals.tokens_cache_read)} cache reads
              </div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.05 }}
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="usage-stat-cost"
            >
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Cost ({days}d)</div>
              <div className="text-xl font-semibold mt-0.5 text-amber-400">${data.totals.cost_est.toFixed(2)}</div>
              <div className="text-xs text-zinc-500">stored ${data.totals.cost_stored.toFixed(2)}</div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.1 }}
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="usage-stat-msgs"
            >
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Messages</div>
              <div className="text-xl font-semibold mt-0.5">{fmtCompact(data.totals.messages)}</div>
              <div className="text-xs text-zinc-500">assistant completions</div>
            </motion.div>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.15 }}
              className="rounded-xl border border-surface-border bg-surface-light p-4"
              data-testid="usage-stat-cum"
            >
              <div className="text-xs text-zinc-500 uppercase tracking-wider">Cumulative est.</div>
              <div className="text-xl font-semibold mt-0.5">${cumCost[cumCost.length - 1].toFixed(2)}</div>
              <div className="text-xs text-zinc-500">over the period</div>
            </motion.div>
          </div>

          <div
            className="rounded-xl border border-surface-border bg-surface-light p-4 mb-6"
            data-testid="usage-token-chart"
          >
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-sm font-semibold text-zinc-300">Tokens per day</h2>
              <label className="flex items-center gap-1.5 text-xs text-zinc-500 cursor-pointer">
                <input
                  type="checkbox"
                  checked={showCache}
                  onChange={(e) => setShowCache(e.target.checked)}
                  className="accent-amber-500"
                  data-testid="usage-cache-toggle"
                />
                include cache reads
              </label>
            </div>
            <TimeChart buckets={data.buckets} series={tokenSeries} stacked />
            <div className="flex gap-4 mt-2 text-xs text-zinc-500">
              {tokenSeries.map((s) => (
                <span key={s.key} className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.color }} />
                  {s.label}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-surface-border bg-surface-light p-4" data-testid="usage-cost-chart">
            <h2 className="text-sm font-semibold text-zinc-300 mb-2">Cost per day (USD)</h2>
            <TimeChart buckets={data.buckets} series={costSeries} />
            <div className="flex gap-4 mt-2 text-xs text-zinc-500">
              {costSeries.map((s) => (
                <span key={s.key} className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-sm" style={{ background: s.color }} />
                  {s.label}
                </span>
              ))}
            </div>
          </div>

          <div
            className="rounded-xl border border-surface-border bg-surface-light p-4 mt-6"
            data-testid="usage-cumulative-chart"
          >
            <h2 className="text-sm font-semibold text-zinc-300 mb-2">Cumulative est. cost (USD)</h2>
            <svg viewBox="0 0 900 180" className="w-full" role="img" aria-label="Cumulative estimated cost">
              <title>Cumulative estimated cost</title>
              {[0.25, 0.5, 0.75, 1].map((f) => (
                <line
                  key={f}
                  x1={44}
                  x2={888}
                  y1={180 - 20 - f * (180 - 44)}
                  y2={180 - 20 - f * (180 - 44)}
                  stroke="#27272a"
                  strokeWidth={1}
                />
              ))}
              {data.buckets.map((b, i) => {
                const x = 44 + (i / Math.max(1, data.buckets.length - 1)) * 844;
                const y = 160 - (cumCost[i] / maxCum) * 136;
                return <circle key={b.day} cx={x} cy={y} r={1.6} fill="#3b82f6" />;
              })}
              <text x={44} y={170} className="fill-zinc-600 text-[10px] font-mono">
                ${maxCum.toFixed(2)} peak
              </text>
            </svg>
          </div>
        </>
      ) : null}
    </div>
  );
}
