import { fetchLeaderboard } from "@/lib/api";
import { Trophy, ShieldCheck, TrendingUp, AlertTriangle, ArrowUpDown } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function LeaderboardPage({
  searchParams,
}: {
  searchParams: { sort?: string };
}) {
  const sort = searchParams.sort || "safety_drift";
  const leaderboard = await fetchLeaderboard(sort);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-surface-border gap-4">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <Trophy className="text-amber-400" /> Group Taxonomy Leaderboard
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Comparative Pareto ranking of agent archetypes ($G_1$–$G_6$) across safety drift and capability gain.
          </p>
        </div>

        {/* Sort Controls */}
        <div className="flex items-center gap-2 bg-surface p-1 rounded-xl border border-surface-border text-xs">
          <span className="text-slate-400 px-2 flex items-center gap-1 font-semibold">
            <ArrowUpDown size={12} /> Sort by:
          </span>
          <a
            href="/leaderboard?sort=safety_drift"
            className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
              sort === "safety_drift" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Safety Drift
          </a>
          <a
            href="/leaderboard?sort=capability_gain"
            className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
              sort === "capability_gain" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Capability Gain
          </a>
          <a
            href="/leaderboard?sort=retention_ratio"
            className={`px-3 py-1.5 rounded-lg font-bold transition-all ${
              sort === "retention_ratio" ? "bg-indigo-600 text-white" : "text-slate-400 hover:text-white"
            }`}
          >
            Retention Ratio
          </a>
        </div>
      </div>

      {/* Leaderboard Table */}
      <div className="glass-panel p-6 rounded-2xl border border-surface-border overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-surface-border text-xs text-slate-400 font-semibold">
              <th className="p-3">Rank</th>
              <th className="p-3">Group</th>
              <th className="p-3">Agent Archetype</th>
              <th className="p-3">Capability Gain $\Delta P$</th>
              <th className="p-3">Safety Drift</th>
              <th className="p-3">Retention Ratio</th>
              <th className="p-3">Proxy Gap</th>
              <th className="p-3">Status</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard.map((item) => (
              <tr
                key={item.group}
                className="border-b border-surface-border/50 hover:bg-white/5 transition-colors text-xs"
              >
                <td className="p-3 font-mono font-bold text-slate-300">#{item.rank}</td>
                <td className="p-3 font-mono font-extrabold text-indigo-400">{item.group}</td>
                <td className="p-3 font-semibold text-white">{item.name}</td>
                <td className="p-3 font-mono font-bold text-emerald-400">
                  +{(item.capability_gain * 100).toFixed(0)}%
                </td>
                <td className="p-3 font-mono font-bold text-rose-400">
                  +{(item.safety_drift * 100).toFixed(1)}%
                </td>
                <td className="p-3 font-mono text-purple-400">
                  {item.retention_ratio.toFixed(2)}
                </td>
                <td className="p-3 font-mono text-amber-400">
                  +{item.proxy_gap.toFixed(3)}
                </td>
                <td className="p-3">
                  <span
                    className={`px-2.5 py-1 rounded-full text-[11px] font-bold ${
                      item.status.includes("Optimal")
                        ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                        : item.status.includes("Safe")
                        ? "bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                        : item.status.includes("Moderate")
                        ? "bg-amber-500/20 text-amber-300 border border-amber-500/30"
                        : "bg-rose-500/20 text-rose-300 border border-rose-500/30"
                    }`}
                  >
                    {item.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
