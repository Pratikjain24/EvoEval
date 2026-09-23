"use client";

import React, { useState } from "react";
import { TrajectoryEvent } from "@/lib/api";
import { Terminal, Shield, CheckCircle2, XCircle, Wrench, AlertOctagon, GitCommit } from "lucide-react";

interface TrajectoryViewerProps {
  events: TrajectoryEvent[];
}

export const TrajectoryViewer: React.FC<TrajectoryViewerProps> = ({ events }) => {
  const [selectedTask, setSelectedTask] = useState<string>("all");
  const [filterType, setFilterType] = useState<string>("all");

  const taskIds = Array.from(new Set(events.map((e) => e.task_id)));

  const filtered = events.filter((e) => {
    if (selectedTask !== "all" && e.task_id !== selectedTask) return false;
    if (filterType !== "all" && e.event_type !== filterType) return false;
    return true;
  });

  const getEventIcon = (type: string) => {
    switch (type) {
      case "tool_call":
        return <Wrench size={16} className="text-blue-400" />;
      case "observation":
        return <Terminal size={16} className="text-emerald-400" />;
      case "safety_check":
        return <Shield size={16} className="text-rose-400" />;
      case "task_start":
        return <GitCommit size={16} className="text-purple-400" />;
      case "task_end":
        return <CheckCircle2 size={16} className="text-indigo-400" />;
      case "evolution_proposal":
      case "evolution_decision":
        return <AlertOctagon size={16} className="text-amber-400" />;
      default:
        return <Terminal size={16} className="text-slate-400" />;
    }
  };

  return (
    <div className="glass-panel p-6 rounded-2xl border border-surface-border">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between pb-4 border-b border-surface-border gap-3">
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">
            Trajectory Event Timeline & Tool Calls
          </h3>
          <p className="text-xs text-slate-400 mt-1">
            Append-only JSONL stream showing agent tool executions, sandbox observations, and safety monitor checks.
          </p>
        </div>

        <div className="flex gap-2">
          {/* Task filter */}
          <select
            value={selectedTask}
            onChange={(e) => setSelectedTask(e.target.value)}
            className="bg-surface text-xs text-slate-200 border border-surface-border rounded-lg px-2.5 py-1.5 focus:outline-none"
          >
            <option value="all">All Tasks</option>
            {taskIds.map((id) => (
              <option key={id} value={id}>
                {id}
              </option>
            ))}
          </select>

          {/* Type filter */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-surface text-xs text-slate-200 border border-surface-border rounded-lg px-2.5 py-1.5 focus:outline-none"
          >
            <option value="all">All Event Types</option>
            <option value="tool_call">Tool Calls</option>
            <option value="observation">Observations</option>
            <option value="safety_check">Safety Checks</option>
            <option value="evolution_proposal">Evolution Proposals</option>
            <option value="task_end">Task Ends</option>
          </select>
        </div>
      </div>

      <div className="mt-4 space-y-3 max-h-[600px] overflow-y-auto pr-2">
        {filtered.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-sm">
            No trajectory events matching current filters.
          </div>
        ) : (
          filtered.map((ev, idx) => (
            <div
              key={idx}
              className="bg-surface/80 p-4 rounded-xl border border-surface-border/70 hover:border-indigo-500/30 transition-colors"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-md bg-surface-card border border-surface-border">
                    {getEventIcon(ev.event_type)}
                  </div>
                  <span className="font-mono text-xs font-bold text-slate-200 uppercase tracking-wider">
                    {ev.event_type}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 font-mono">
                    {ev.agent_version}
                  </span>
                  <span className="text-[11px] px-2 py-0.5 rounded-full bg-indigo-950 text-indigo-300 font-mono">
                    {ev.group}
                  </span>
                </div>
                <div className="text-[11px] font-mono text-slate-500">
                  {new Date(ev.ts).toLocaleTimeString()} · task: {ev.task_id}
                </div>
              </div>

              {/* Payload content */}
              <div className="mt-2 bg-slate-950/80 p-3 rounded-lg border border-slate-900 font-mono text-xs overflow-x-auto text-slate-300">
                {ev.event_type === "tool_call" && (
                  <div>
                    <span className="text-blue-400 font-bold">$ {ev.payload.tool_name}</span>{" "}
                    <span className="text-slate-400">{JSON.stringify(ev.payload.arguments)}</span>
                  </div>
                )}
                {ev.event_type === "observation" && (
                  <div>
                    <span className="text-slate-500">// Output (code: {ev.payload.exit_code}):</span>
                    <pre className="text-emerald-400 mt-1 whitespace-pre-wrap">{ev.payload.stdout || ev.payload.stderr || "(no output)"}</pre>
                  </div>
                )}
                {ev.event_type === "safety_check" && (
                  <div className="text-rose-400 font-semibold">
                    [RULE: {ev.payload.rule_name}] Passed: {String(ev.payload.passed)} - {ev.payload.violation_details || "Allowed"}
                  </div>
                )}
                {ev.event_type === "task_end" && (
                  <div className="flex gap-4">
                    <span className={ev.payload.success ? "text-emerald-400 font-bold" : "text-rose-400 font-bold"}>
                      Status: {ev.payload.status}
                    </span>
                    <span>GT Score: {ev.payload.ground_truth_score}</span>
                    <span className="text-amber-400">Proxy Gap: +{ev.payload.proxy_gap}</span>
                  </div>
                )}
                {!["tool_call", "observation", "safety_check", "task_end"].includes(ev.event_type) && (
                  <pre className="whitespace-pre-wrap">{JSON.stringify(ev.payload, null, 2)}</pre>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
