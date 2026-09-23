"use client";

import React from "react";
import { ShieldAlert, TrendingUp, AlertTriangle, DollarSign, Layers } from "lucide-react";

interface KpiCardsProps {
  successRate: number;
  safetyDrift: number;
  proxyGap: number;
  totalCost: number;
  totalRuns: number;
}

export const KpiCards: React.FC<KpiCardsProps> = ({
  successRate,
  safetyDrift,
  proxyGap,
  totalCost,
  totalRuns,
}) => {
  const cards = [
    {
      label: "Mean Capability Success",
      value: `${(successRate * 100).toFixed(1)}%`,
      sub: "Across all benchmark groups",
      icon: TrendingUp,
      color: "text-emerald-400",
      bg: "bg-emerald-500/10",
      border: "border-emerald-500/20",
    },
    {
      label: "Mean Safety Drift",
      value: `+${(safetyDrift * 100).toFixed(1)}%`,
      sub: "Violation rate delta vs. cycle 0",
      icon: ShieldAlert,
      color: safetyDrift > 0.05 ? "text-rose-400" : "text-slate-400",
      bg: safetyDrift > 0.05 ? "bg-rose-500/10" : "bg-slate-500/10",
      border: safetyDrift > 0.05 ? "border-rose-500/20" : "border-slate-500/20",
    },
    {
      label: "Proxy Reward Gap",
      value: proxyGap.toFixed(3),
      sub: "Automated Proxy - Ground Truth",
      icon: AlertTriangle,
      color: proxyGap > 0.1 ? "text-amber-400" : "text-blue-400",
      bg: proxyGap > 0.1 ? "bg-amber-500/10" : "bg-blue-500/10",
      border: proxyGap > 0.1 ? "border-amber-500/20" : "border-blue-500/20",
    },
    {
      label: "Cumulative Expenditure",
      value: `$${totalCost.toFixed(2)}`,
      sub: "Enforced by BudgetGuard",
      icon: DollarSign,
      color: "text-indigo-400",
      bg: "bg-indigo-500/10",
      border: "border-indigo-500/20",
    },
    {
      label: "Active Benchmark Runs",
      value: totalRuns.toString(),
      sub: "G1-G6 evolutionary matrices",
      icon: Layers,
      color: "text-purple-400",
      bg: "bg-purple-500/10",
      border: "border-purple-500/20",
    },
  ];

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <div
            key={i}
            className={`glass-card p-5 rounded-xl border ${c.border} flex flex-col justify-between`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">
                {c.label}
              </span>
              <div className={`p-2 rounded-lg ${c.bg} ${c.color}`}>
                <Icon size={18} />
              </div>
            </div>
            <div>
              <div className={`text-2xl font-extrabold ${c.color} tracking-tight`}>
                {c.value}
              </div>
              <div className="text-xs text-slate-500 mt-1 font-medium">{c.sub}</div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
