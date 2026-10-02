import { fetchRun, fetchTrajectories, fetchCycles } from "@/lib/api";
import { TrajectoryViewer } from "@/components/TrajectoryViewer";
import { DriftCurve } from "@/components/DriftCurve";
import Link from "next/link";
import { ArrowLeft, GitBranch, Shield, Terminal, Zap, FileText } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function RunDetailPage({ params }: { params: { id: string } }) {
  const runId = params.id;
  const run = await fetchRun(runId);
  const trajectories = await fetchTrajectories(runId, { limit: 100 });
  const cycles = await fetchCycles(runId);

  const proposals = trajectories.filter(
    (e) => e.event_type === "evolution_proposal" || e.event_type === "evolution_decision" || e.event_type === "rollback"
  );
  const safetyEvents = trajectories.filter((e) => e.event_type === "safety_check");

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-surface-border">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="p-2 rounded-xl bg-surface-card hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
          >
            <ArrowLeft size={16} />
          </Link>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-xl font-black text-white font-mono">{runId}</h2>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 font-semibold border border-emerald-500/30">
                Completed
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Experiment Run Matrix Details & Trajectory Inspector
            </p>
          </div>
        </div>
      </div>

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="glass-card p-4 rounded-xl border border-surface-border">
          <div className="text-xs text-slate-400 font-semibold">Total Trajectory Events</div>
          <div className="text-xl font-mono font-bold text-indigo-400 mt-1">{trajectories.length}</div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-surface-border">
          <div className="text-xs text-slate-400 font-semibold">Evolution Steps</div>
          <div className="text-xl font-mono font-bold text-purple-400 mt-1">{proposals.length}</div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-surface-border">
          <div className="text-xs text-slate-400 font-semibold">Safety Interceptions</div>
          <div className="text-xl font-mono font-bold text-rose-400 mt-1">{safetyEvents.length}</div>
        </div>
        <div className="glass-card p-4 rounded-xl border border-surface-border">
          <div className="text-xs text-slate-400 font-semibold">Storage Path</div>
          <div className="text-xs font-mono text-slate-300 mt-1 truncate">experiments/runs/{runId}</div>
        </div>
      </div>

      {/* Drift curve for this specific run */}
      <DriftCurve data={cycles} />

      {/* Evolution Proposals & Decisions Timeline */}
      <div className="glass-panel p-6 rounded-2xl border border-surface-border">
        <div className="flex items-center gap-2 pb-3 border-b border-surface-border mb-4">
          <GitBranch size={18} className="text-purple-400" />
          <h3 className="text-lg font-bold text-white tracking-tight">
            Inter-Cycle Evolution & Verifier Gating Timeline
          </h3>
        </div>

        <div className="space-y-3">
          {proposals.length === 0 ? (
            <div className="text-xs text-slate-500 py-4">No evolution events recorded yet.</div>
          ) : (
            proposals.map((p, idx) => (
              <div key={idx} className="bg-surface/70 p-4 rounded-xl border border-surface-border flex items-start justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-indigo-400">
                      Cycle {p.cycle}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 font-mono">
                      {p.group} ({p.agent_version})
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full font-bold uppercase ${
                        p.payload.decision === "accepted" || p.event_type === "evolution_proposal"
                          ? "bg-emerald-500/20 text-emerald-400"
                          : "bg-rose-500/20 text-rose-400"
                      }`}
                    >
                      {p.event_type} : {p.payload.decision || "Proposed"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-300 mt-2 font-mono">
                    {p.payload.rationale || p.payload.reason || JSON.stringify(p.payload)}
                  </p>
                </div>
                <div className="text-[11px] font-mono text-slate-500 shrink-0">
                  {new Date(p.ts).toLocaleTimeString()}
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Trajectory Stream Viewer */}
      <TrajectoryViewer events={trajectories} />
    </div>
  );
}
