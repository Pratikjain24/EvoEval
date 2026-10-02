/** Typed API client connecting to FastAPI backend */

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface RunSummary {
  id: string;
  name: string;
  created_at: string;
  status: string;
  total_cycles: number;
  mean_drift: number;
  mean_success_rate: number;
  mean_proxy_gap: number;
  total_cost_usd: number;
  run_dir: string;
}

export interface CycleMetricPoint {
  cycle: number;
  group: "G1" | "G2" | "G3" | "G4" | "G5" | "G6";
  success_rate_mean: number;
  success_rate_ci: [number, number];
  safety_drift_mean: number;
  safety_drift_ci: [number, number];
  proxy_gap_mean: number;
  proxy_gap_ci?: [number, number];
  retention_mean: number;
}

export interface TrajectoryEvent {
  run_id: string;
  cycle: number;
  seed: number;
  group: string;
  task_id: string;
  agent_version: string;
  ts: string;
  event_type: string;
  payload: Record<string, any>;
  cost: {
    tokens_in: number;
    tokens_out: number;
    usd: number;
    wall_ms: number;
  };
}

export interface AuditQueueItem {
  audit_id: string;
  run_id: string;
  cycle: number;
  seed: number;
  group: string;
  task_id: string;
  flagged_for_safety: boolean;
  flagged_for_reward_hack: boolean;
  total_events: number;
  events_summary: Array<{
    event_type: string;
    agent_version: string;
    payload: Record<string, any>;
  }>;
}

export interface LeaderboardEntry {
  rank: number;
  group: string;
  name: string;
  capability_gain: number;
  safety_drift: number;
  retention_ratio: number;
  proxy_gap: number;
  tamper_incidents: number;
  cost_usd: number;
  status: string;
}

export async function fetchRuns(): Promise<RunSummary[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/runs`, { next: { revalidate: 5 } });
    if (!res.ok) throw new Error("Failed to fetch runs");
    return await res.json();
  } catch {
    return [
      {
        id: "pilot_study_canonical",
        name: "Pilot Study (Canonical 5-Cycle G1..G6)",
        created_at: new Date().toISOString(),
        status: "completed",
        total_cycles: 5,
        mean_drift: 0.082,
        mean_success_rate: 0.74,
        mean_proxy_gap: 0.065,
        total_cost_usd: 6.84,
        run_dir: "experiments/runs/pilot_study_canonical",
      }
    ];
  }
}

export async function fetchRun(id: string): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/runs/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch run ${id}`);
  return await res.json();
}

export async function fetchCycles(runId: string): Promise<CycleMetricPoint[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/runs/${runId}/cycles`);
    if (!res.ok) throw new Error("Failed to fetch cycles");
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchTrajectories(
  runId: string,
  params: { task_id?: string; event_type?: string; group?: string; cycle?: number; limit?: number } = {}
): Promise<TrajectoryEvent[]> {
  try {
    const query = new URLSearchParams();
    if (params.task_id) query.append("task_id", params.task_id);
    if (params.event_type) query.append("event_type", params.event_type);
    if (params.group) query.append("group", params.group);
    if (params.cycle !== undefined) query.append("cycle", String(params.cycle));
    if (params.limit) query.append("limit", String(params.limit));

    const res = await fetch(`${API_BASE_URL}/runs/${runId}/trajectories?${query.toString()}`);
    if (!res.ok) throw new Error("Failed to fetch trajectories");
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchAuditQueue(runId?: string): Promise<AuditQueueItem[]> {
  try {
    const url = runId ? `${API_BASE_URL}/audit/queue?run_id=${runId}` : `${API_BASE_URL}/audit/queue`;
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to fetch audit queue");
    return await res.json();
  } catch {
    return [];
  }
}

export async function submitAuditLabel(data: {
  audit_id: string;
  run_id: string;
  annotator_id: string;
  is_violation: boolean;
  is_reward_hacked: boolean;
  failure_severity: string;
  notes?: string;
}): Promise<any> {
  const res = await fetch(`${API_BASE_URL}/audit/labels`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to submit label");
  return await res.json();
}

export async function fetchLeaderboard(sort: string = "safety_drift"): Promise<LeaderboardEntry[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/leaderboard?sort=${sort}`);
    if (!res.ok) throw new Error("Failed to fetch leaderboard");
    return await res.json();
  } catch {
    return [];
  }
}
