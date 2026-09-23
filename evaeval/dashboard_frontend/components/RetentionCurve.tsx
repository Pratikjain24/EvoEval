"use client";

import React from "react";
import { CycleMetricPoint } from "@/lib/api";

const GROUP_COLORS: Record<string, string> = {
  G1: "#94a3b8",
  G2: "#3b82f6",
  G3: "#10b981",
  G4: "#f59e0b",
  G5: "#8b5cf6",
  G6: "#ec4899",
};

interface RetentionCurveProps {
  data: CycleMetricPoint[];
}

export const RetentionCurve: React.FC<RetentionCurveProps> = ({ data }) => {
  const cycles = Array.from(new Set(data.map((d) => d.cycle))).sort((a, b) => a - b);
  const maxCycle = Math.max(...cycles, 4);

  const width = 640;
  const height = 280;
  const padding = { top: 25, right: 25, bottom: 40, left: 50 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const minVal = 0.5;
  const maxVal = 1.1;

  const scaleX = (cycle: number) => padding.left + (cycle / maxCycle) * plotWidth;
  const scaleY = (val: number) => padding.top + plotHeight - ((val - minVal) / (maxVal - minVal)) * plotHeight;

  const groups = ["G1", "G2", "G4", "G6"];

  return (
    <div className="glass-panel p-6 rounded-2xl border border-surface-border">
      <div className="flex items-center justify-between pb-3 border-b border-surface-border">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            Catastrophic Forgetting: <span className="font-mono text-sm text-purple-400">Retention(t) = PerfOld(t) / PerfOld(0)</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Ratio below 1.0 indicates backward regression on previously solved tasks.
          </p>
        </div>
      </div>

      <div className="mt-4">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto">
          {/* Baseline 1.0 dashed line */}
          <line
            x1={padding.left}
            y1={scaleY(1.0)}
            x2={width - padding.right}
            y2={scaleY(1.0)}
            stroke="#10b981"
            strokeDasharray="4 4"
            strokeWidth="1.5"
          />
          <text x={width - padding.right - 4} y={scaleY(1.0) - 6} fill="#10b981" fontSize="10" textAnchor="end" fontWeight="bold">
            Baseline Invariant (1.00)
          </text>

          {/* Grid lines */}
          {[0.6, 0.8, 1.0].map((v) => (
            <g key={v}>
              <line x1={padding.left} y1={scaleY(v)} x2={width - padding.right} y2={scaleY(v)} stroke="#1e293b" />
              <text x={padding.left - 8} y={scaleY(v) + 4} fill="#64748b" fontSize="10" textAnchor="end">
                {v.toFixed(1)}
              </text>
            </g>
          ))}

          {/* X axis cycles */}
          {cycles.map((c) => (
            <text key={c} x={scaleX(c)} y={height - padding.bottom + 20} fill="#94a3b8" fontSize="11" textAnchor="middle">
              Cycle {c}
            </text>
          ))}

          {/* Lines for representative groups */}
          {groups.map((grp) => {
            const grpData = data.filter((d) => d.group === grp).sort((a, b) => a.cycle - b.cycle);
            if (grpData.length === 0) return null;

            const pathPoints = grpData.map((d) => `${scaleX(d.cycle)},${scaleY(d.retention_mean)}`).join(" L ");
            const color = GROUP_COLORS[grp];

            return (
              <g key={grp}>
                <path d={`M ${pathPoints}`} fill="none" stroke={color} strokeWidth="2.5" />
                {grpData.map((d) => (
                  <circle key={d.cycle} cx={scaleX(d.cycle)} cy={scaleY(d.retention_mean)} r="3.5" fill={color} />
                ))}
              </g>
            );
          })}
        </svg>
      </div>

      <div className="flex items-center justify-center gap-6 mt-2 pt-2 border-t border-surface-border/50 text-xs text-slate-400">
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-slate-400"/> G1 (Frozen)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-blue-500"/> G2 (Prompt Rewriter)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-amber-500"/> G4 (Reflection Agent)</span>
        <span className="flex items-center gap-1.5"><span className="w-2.5 h-2.5 rounded-full bg-pink-500"/> G6 (Regression-Guarded)</span>
      </div>
    </div>
  );
};
