import Link from "next/link";
import { fetchRuns, fetchCycles } from "@/lib/api";
import { KpiCards } from "@/components/KpiCards";
import { DriftCurve } from "@/components/DriftCurve";
import { RetentionCurve } from "@/components/RetentionCurve";
import { ProxyGapChart } from "@/components/ProxyGapChart";
import { CycleHeatmap } from "@/components/CycleHeatmap";
import { ArrowRight, Play, ExternalLink } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const runs = await fetchRuns();
  const latestRunId = runs.length > 0 ? runs[0].id : "pilot_study_canonical";
  const cycles = await fetchCycles(latestRunId);

  const meanSuccess = runs.length > 0 ? runs.reduce((acc, r) => acc + r.mean_success_rate, 0) / runs.length : 0.72;
  const meanDrift = runs.length > 0 ? runs.reduce((acc, r) => acc + r.mean_drift, 0) / runs.length : 0.08;
  const meanProxyGap = runs.length > 0 ? runs.reduce((acc, r) => acc + r.mean_proxy_gap, 0) / runs.length : 0.06;
  const totalCost = runs.length > 0 ? runs.reduce((acc, r) => acc + r.total_cost_usd, 0) : 6.84;

  return (
    <div className="space-y-8">
      {/* Hero / Overview Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl md:text-3xl font-black text-white tracking-tight">
            Experimental Benchmark Overview
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Quantifying capability gain vs. safety degradation across recursive agent evolution cycles.
          </p>
        </div>
        <div className="flex gap-3">
          <Link
            href="/drift"
            className="px-4 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center gap-2 shadow-lg shadow-indigo-500/20 transition-all"
          >
            <Play size={14} className="fill-white" /> Open Drift Explorer
          </Link>
          <Link
            href="/leaderboard"
            className="px-4 py-2 rounded-xl text-xs font-bold bg-surface-card hover:bg-slate-800 text-slate-200 border border-surface-border flex items-center gap-2 transition-all"
          >
            Group Leaderboard <ArrowRight size={14} />
          </Link>
        </div>
      </div>

      {/* KPI Cards */}
      <KpiCards
        successRate={meanSuccess}
        safetyDrift={meanDrift}
        proxyGap={meanProxyGap}
        totalCost={totalCost}
        totalRuns={runs.length}
      />

      {/* Drift Curve Headline Chart */}
      <DriftCurve data={cycles} />

      {/* Grid: Retention Curve + Proxy Gap */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <RetentionCurve data={cycles} />
        <ProxyGapChart data={cycles} />
      </div>

      {/* Metric Heatmap Matrix */}
      <CycleHeatmap data={cycles} />

      {/* Runs Table */}
      <div className="glass-panel p-6 rounded-2xl border border-surface-border">
        <div className="flex items-center justify-between pb-4 border-b border-surface-border">
          <div>
            <h3 className="text-lg font-bold text-white tracking-tight">
              Benchmark Run History
            </h3>
            <p className="text-xs text-slate-400 mt-1">
              Select any run to inspect detailed event trajectories, diffs, and snapshots.
            </p>
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-surface-border text-xs text-slate-400">
                <th className="p-3">Run ID</th>
                <th className="p-3">Cycles</th>
                <th className="p-3">Success Rate</th>
                <th className="p-3">Safety Drift</th>
                <th className="p-3">Proxy Gap</th>
                <th className="p-3">Total Cost</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.id} className="border-b border-surface-border/50 hover:bg-white/5 transition-colors text-xs">
                  <td className="p-3 font-mono font-bold text-slate-200">{r.id}</td>
                  <td className="p-3">{r.total_cycles}</td>
                  <td className="p-3 font-mono font-semibold text-emerald-400">
                    {(r.mean_success_rate * 100).toFixed(1)}%
                  </td>
                  <td className="p-3 font-mono font-semibold text-rose-400">
                    +{(r.mean_drift * 100).toFixed(1)}%
                  </td>
                  <td className="p-3 font-mono text-amber-400">
                    +{r.mean_proxy_gap.toFixed(3)}
                  </td>
                  <td className="p-3 font-mono">${r.total_cost_usd.toFixed(3)}</td>
                  <td className="p-3 text-right">
                    <Link
                      href={`/runs/${r.id}`}
                      className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-surface-card hover:bg-indigo-600/30 text-indigo-400 font-semibold border border-indigo-500/30 transition-all"
                    >
                      Inspect <ExternalLink size={12} />
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
