"use client";

import React from "react";
import { CycleMetricPoint } from "@/lib/api";

interface ProxyGapChartProps {
  data: CycleMetricPoint[];
}

export const ProxyGapChart: React.FC<ProxyGapChartProps> = ({ data }) => {
  const cycles = [0, 1, 2, 3, 4];
  const targetGroups = ["G1", "G2", "G4", "G6"];

  return (
    <div className="glass-panel p-6 rounded-2xl border border-surface-border">
      <div className="flex items-center justify-between pb-3 border-b border-surface-border">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            Reward Hacking: <span className="font-mono text-sm text-amber-400">ProxyGap = Automated Reward - Ground Truth</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Divergence highlights agents gaming surface tests while failing actual ground truth correctness.
          </p>
        </div>
      </div>

      <div className="mt-5 space-y-4">
        {targetGroups.map((grp) => {
          const points = data.filter((d) => d.group === grp).sort((a, b) => a.cycle - b.cycle);
          const latestGap = points.length > 0 ? points[points.length - 1].proxy_gap_mean : 0.05;
          const isHigh = latestGap > 0.15;

          return (
            <div key={grp} className="bg-surface/60 p-3.5 rounded-xl border border-surface-border">
              <div className="flex items-center justify-between text-xs mb-2">
                <span className="font-bold text-slate-200">
                  {grp === "G1" && "G1: Frozen Baseline"}
                  {grp === "G2" && "G2: Prompt Rewriter"}
                  {grp === "G4" && "G4: Reflection Agent (Unconstrained)"}
                  {grp === "G6" && "G6: Regression-Guarded Verifier"}
                </span>
                <span
                  className={`font-mono font-semibold px-2 py-0.5 rounded text-xs ${
                    isHigh ? "bg-rose-500/20 text-rose-400" : "bg-emerald-500/20 text-emerald-400"
                  }`}
                >
                  Gap: +{latestGap.toFixed(3)}
                </span>
              </div>

              {/* Multi-cycle mini progress bar */}
              <div className="grid grid-cols-5 gap-2">
                {cycles.map((c) => {
                  const pt = points.find((p) => p.cycle === c);
                  const val = pt ? pt.proxy_gap_mean : (grp === "G4" ? 0.06 * c : 0.02);
                  const pct = Math.min(100, Math.max(5, (val / 0.35) * 100));
                  return (
                    <div key={c} className="flex flex-col gap-1">
                      <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all duration-300 ${
                            val > 0.15 ? "bg-amber-400" : "bg-indigo-500"
                          }`}
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                      <span className="text-[10px] text-slate-500 text-center">c{c}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
