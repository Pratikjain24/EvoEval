"use client";

import React, { useState } from "react";
import { CycleMetricPoint } from "@/lib/api";

const GROUP_COLORS: Record<string, { stroke: string; fill: string; name: string }> = {
  G1: { stroke: "#94a3b8", fill: "rgba(148, 163, 184, 0.15)", name: "G1: Frozen Baseline" },
  G2: { stroke: "#3b82f6", fill: "rgba(59, 130, 246, 0.15)", name: "G2: Prompt Rewriter" },
  G3: { stroke: "#10b981", fill: "rgba(16, 185, 129, 0.15)", name: "G3: Memory Accumulator" },
  G4: { stroke: "#f59e0b", fill: "rgba(245, 158, 11, 0.15)", name: "G4: Reflection Agent" },
  G5: { stroke: "#8b5cf6", fill: "rgba(139, 92, 246, 0.15)", name: "G5: Static Verifier" },
  G6: { stroke: "#ec4899", fill: "rgba(236, 72, 153, 0.15)", name: "G6: Regression Guard" },
};

interface DriftCurveProps {
  data: CycleMetricPoint[];
}

export const DriftCurve: React.FC<DriftCurveProps> = ({ data }) => {
  const [activeGroup, setActiveGroup] = useState<string | null>(null);

  const cycles = Array.from(new Set(data.map((d) => d.cycle))).sort((a, b) => a - b);
  const maxCycle = Math.max(...cycles, 4);

  // Group data by group code
  const groups = ["G1", "G2", "G3", "G4", "G5", "G6"];
  const width = 680;
  const height = 300;
  const padding = { top: 30, right: 30, bottom: 40, left: 50 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const maxDrift = 0.35;
  const minDrift = -0.05;

  const scaleX = (cycle: number) => padding.left + (cycle / maxCycle) * plotWidth;
  const scaleY = (val: number) => padding.top + plotHeight - ((val - minDrift) / (maxDrift - minDrift)) * plotHeight;

  return (
    <div className="glass-panel p-6 rounded-2xl border border-surface-border">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-surface-border gap-2">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
            Safety Drift Dynamics: <span className="font-mono text-sm text-indigo-400">SafetyDrift(t) = Violations(t) - Violations(0)</span>
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Solid line shows 3-seed mean; shaded envelopes indicate bootstrap 95% confidence intervals.
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          {groups.map((grp) => {
            const isHovered = activeGroup === grp;
            const style = GROUP_COLORS[grp];
            return (
              <button
                key={grp}
                onMouseEnter={() => setActiveGroup(grp)}
                onMouseLeave={() => setActiveGroup(null)}
                className={`text-xs px-2.5 py-1 rounded-md font-semibold transition-all flex items-center gap-1.5 ${
                  isHovered ? "bg-white/10 ring-1 ring-white/20" : "bg-surface text-slate-300 hover:bg-surface-card"
                }`}
              >
                <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: style.stroke }} />
                {grp}
              </button>
            );
          })}
        </div>
      </div>

      <div className="mt-4 overflow-x-auto">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full h-auto min-w-[500px]">
          {/* Grid lines */}
          {[0, 0.1, 0.2, 0.3].map((val) => {
            const y = scaleY(val);
            return (
              <g key={val}>
                <line x1={padding.left} y1={y} x2={width - padding.right} y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                <text x={padding.left - 8} y={y + 4} fill="#64748b" fontSize="10" textAnchor="end">
                  +{(val * 100).toFixed(0)}%
                </text>
              </g>
            );
          })}

          {/* Zero baseline */}
          <line
            x1={padding.left}
            y1={scaleY(0)}
            x2={width - padding.right}
            y2={scaleY(0)}
            stroke="#475569"
            strokeWidth="1.5"
          />

          {/* Cycle X axis marks */}
          {cycles.map((c) => {
            const x = scaleX(c);
            return (
              <g key={c}>
                <line x1={x} y1={padding.top} x2={x} y2={height - padding.bottom} stroke="#1e293b" strokeDasharray="2 2" />
                <text x={x} y={height - padding.bottom + 20} fill="#94a3b8" fontSize="11" textAnchor="middle" fontWeight="bold">
                  Cycle {c}
                </text>
              </g>
            );
          })}

          {/* Lines & CI bands */}
          {groups.map((grp) => {
            const grpData = data.filter((d) => d.group === grp).sort((a, b) => a.cycle - b.cycle);
            if (grpData.length === 0) return null;

            const style = GROUP_COLORS[grp];
            const isDimmed = activeGroup !== null && activeGroup !== grp;

            // Generate Path for mean line
            const linePoints = grpData.map((d) => `${scaleX(d.cycle)},${scaleY(d.safety_drift_mean)}`).join(" L ");
            const linePath = `M ${linePoints}`;

            // Generate Path for CI Area band
            const upperPoints = grpData.map((d) => `${scaleX(d.cycle)},${scaleY(d.safety_drift_ci[1])}`).join(" L ");
            const lowerPoints = grpData.map((d) => `${scaleX(d.cycle)},${scaleY(d.safety_drift_ci[0])}`).reverse().join(" L ");
            const areaPath = `M ${upperPoints} L ${lowerPoints} Z`;

            return (
              <g key={grp} opacity={isDimmed ? 0.2 : 1.0} className="transition-opacity duration-200">
                <path d={areaPath} fill={style.fill} />
                <path d={linePath} fill="none" stroke={style.stroke} strokeWidth={isDimmed ? 1.5 : 3.0} />
                {grpData.map((d) => (
                  <circle
                    key={d.cycle}
                    cx={scaleX(d.cycle)}
                    cy={scaleY(d.safety_drift_mean)}
                    r={activeGroup === grp ? 5 : 3.5}
                    fill={style.stroke}
                  />
                ))}
              </g>
            );
          })}
        </svg>
      </div>
    </div>
  );
};
