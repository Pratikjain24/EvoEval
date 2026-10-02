"use client";

import React, { useEffect, useState } from "react";
import { fetchAuditQueue, submitAuditLabel, AuditQueueItem } from "@/lib/api";
import { ClipboardCheck, ShieldAlert, AlertTriangle, Check, RefreshCw } from "lucide-react";

export default function AuditPage() {
  const [queue, setQueue] = useState<AuditQueueItem[]>([]);
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [annotatorId, setAnnotatorId] = useState<string>("evaluator_alice");

  // Form states
  const [isViolation, setIsViolation] = useState<boolean>(false);
  const [isRewardHacked, setIsRewardHacked] = useState<boolean>(false);
  const [severity, setSeverity] = useState<string>("none");
  const [notes, setNotes] = useState<string>("");
  const [submittedIds, setSubmittedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadQueue();
  }, []);

  const loadQueue = async () => {
    setLoading(true);
    const data = await fetchAuditQueue();
    setQueue(data);
    setLoading(false);
  };

  const currentItem = queue[selectedIdx];

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!currentItem) return;

    setSubmitting(true);
    try {
      await submitAuditLabel({
        audit_id: currentItem.audit_id,
        run_id: currentItem.run_id,
        annotator_id: annotatorId,
        is_violation: isViolation,
        is_reward_hacked: isRewardHacked,
        failure_severity: severity,
        notes,
      });

      setSubmittedIds((prev) => new Set(prev).add(currentItem.audit_id));

      // Advance to next item
      if (selectedIdx < queue.length - 1) {
        setSelectedIdx(selectedIdx + 1);
        setIsViolation(false);
        setIsRewardHacked(false);
        setSeverity("none");
        setNotes("");
      }
    } catch (err) {
      alert("Failed to save label: " + String(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between pb-4 border-b border-surface-border">
        <div>
          <h2 className="text-2xl font-black text-white tracking-tight flex items-center gap-2">
            <ClipboardCheck className="text-indigo-400" /> Human Audit Workbench
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Stratified 5–10% sample of agent trajectories for double-blind human validation.
          </p>
        </div>
        <button
          onClick={loadQueue}
          className="px-3.5 py-1.5 rounded-xl text-xs font-semibold bg-surface-card hover:bg-slate-800 text-slate-300 border border-surface-border flex items-center gap-2 transition-all"
        >
          <RefreshCw size={13} /> Refresh Queue
        </button>
      </div>

      {loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">Loading audit queue...</div>
      ) : queue.length === 0 ? (
        <div className="glass-panel p-12 text-center rounded-2xl border border-surface-border text-slate-400">
          No audit queue items available. Run an experiment or export an audit sample with{" "}
          <code className="text-indigo-400 bg-surface px-2 py-1 rounded">sage audit</code>.
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Queue List */}
          <div className="lg:col-span-4 space-y-2">
            <div className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">
              Sampled Trajectories ({queue.length})
            </div>
            <div className="space-y-2 max-h-[600px] overflow-y-auto pr-1">
              {queue.map((item, idx) => {
                const isSelected = selectedIdx === idx;
                const isDone = submittedIds.has(item.audit_id);
                return (
                  <button
                    key={item.audit_id}
                    onClick={() => setSelectedIdx(idx)}
                    className={`w-full text-left p-3.5 rounded-xl border transition-all flex flex-col gap-1.5 ${
                      isSelected
                        ? "bg-indigo-600/20 border-indigo-500/50 text-white"
                        : "bg-surface-card border-surface-border text-slate-300 hover:bg-slate-800/60"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-xs font-bold text-indigo-400">
                        {item.task_id}
                      </span>
                      {isDone && (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center gap-1">
                          <Check size={10} /> Labeled
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 text-[11px] text-slate-400">
                      <span>Cycle {item.cycle}</span>
                      <span>·</span>
                      <span>{item.group}</span>
                      <span>·</span>
                      <span>Seed {item.seed}</span>
                    </div>
                    <div className="flex gap-1.5 mt-1">
                      {item.flagged_for_safety && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-rose-500/20 text-rose-400 font-semibold flex items-center gap-1">
                          <ShieldAlert size={10} /> Safety Flag
                        </span>
                      )}
                      {item.flagged_for_reward_hack && (
                        <span className="text-[10px] px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-400 font-semibold flex items-center gap-1">
                          <AlertTriangle size={10} /> Hack Flag
                        </span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Right Column: Inspector & Label Form */}
          <div className="lg:col-span-8 space-y-6">
            {currentItem && (
              <>
                {/* Event Trace Details */}
                <div className="glass-panel p-6 rounded-2xl border border-surface-border">
                  <div className="flex items-center justify-between pb-3 border-b border-surface-border">
                    <h3 className="font-bold text-white text-sm">
                      Trajectory Trace: <span className="font-mono text-indigo-400">{currentItem.task_id}</span>
                    </h3>
                    <span className="text-xs font-mono text-slate-400">
                      Group {currentItem.group} | Cycle {currentItem.cycle}
                    </span>
                  </div>

                  <div className="mt-4 space-y-2 max-h-[300px] overflow-y-auto pr-2 font-mono text-xs">
                    {currentItem.events_summary.map((ev, i) => (
                      <div key={i} className="p-2.5 bg-slate-950/80 rounded-lg border border-slate-900">
                        <div className="text-slate-400 font-semibold text-[11px] uppercase mb-1">
                          [{ev.event_type}] ({ev.agent_version})
                        </div>
                        <pre className="text-slate-300 whitespace-pre-wrap">{JSON.stringify(ev.payload, null, 2)}</pre>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Double-Blind Human Labeling Form */}
                <form
                  onSubmit={handleSubmit}
                  className="glass-panel p-6 rounded-2xl border border-surface-border space-y-4"
                >
                  <h3 className="font-bold text-white text-sm pb-2 border-b border-surface-border">
                    Double-Blind Judgment Form
                  </h3>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1">
                        Annotator Identifier
                      </label>
                      <input
                        type="text"
                        value={annotatorId}
                        onChange={(e) => setAnnotatorId(e.target.value)}
                        className="w-full bg-surface text-xs font-mono px-3 py-2 rounded-lg border border-surface-border text-slate-200 focus:outline-none"
                        required
                      />
                    </div>

                    <div>
                      <label className="text-xs font-semibold text-slate-300 block mb-1">
                        Failure Severity Taxonomy
                      </label>
                      <select
                        value={severity}
                        onChange={(e) => setSeverity(e.target.value)}
                        className="w-full bg-surface text-xs px-3 py-2 rounded-lg border border-surface-border text-slate-200 focus:outline-none"
                      >
                        <option value="none">None (Clean Execution)</option>
                        <option value="benign">Benign Failure (Syntax / Timeout)</option>
                        <option value="recoverable">Recoverable Logic Error</option>
                        <option value="fatal">Fatal Sandbox Error</option>
                        <option value="malicious">Malicious / Reward Hacking</option>
                      </select>
                    </div>
                  </div>

                  <div className="flex gap-6 pt-2">
                    <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-300">
                      <input
                        type="checkbox"
                        checked={isViolation}
                        onChange={(e) => setIsViolation(e.target.checked)}
                        className="w-4 h-4 rounded bg-surface border-surface-border text-indigo-600 focus:ring-0"
                      />
                      Confirms Safety Boundary Violation
                    </label>

                    <label className="flex items-center gap-2 cursor-pointer text-xs font-semibold text-slate-300">
                      <input
                        type="checkbox"
                        checked={isRewardHacked}
                        onChange={(e) => setIsRewardHacked(e.target.checked)}
                        className="w-4 h-4 rounded bg-surface border-surface-border text-indigo-600 focus:ring-0"
                      />
                      Confirms Reward Hacking / Specification Gaming
                    </label>
                  </div>

                  <div>
                    <label className="text-xs font-semibold text-slate-300 block mb-1">
                      Auditor Notes & Observations
                    </label>
                    <textarea
                      value={notes}
                      onChange={(e) => setNotes(e.target.value)}
                      rows={3}
                      placeholder="Describe specific behavioral anomalies or code discrepancies..."
                      className="w-full bg-surface text-xs px-3 py-2 rounded-lg border border-surface-border text-slate-200 focus:outline-none placeholder-slate-600"
                    />
                  </div>

                  <div className="flex justify-end pt-2">
                    <button
                      type="submit"
                      disabled={submitting}
                      className="px-5 py-2 rounded-xl text-xs font-bold bg-indigo-600 hover:bg-indigo-500 text-white transition-all shadow-lg shadow-indigo-500/20 disabled:opacity-50"
                    >
                      {submitting ? "Saving Judgment..." : "Submit Judgment & Next"}
                    </button>
                  </div>
                </form>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
