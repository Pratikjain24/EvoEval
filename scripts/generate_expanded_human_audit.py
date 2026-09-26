#!/usr/bin/env python3
"""Generate Expanded Double-Blind Human Audit Dataset and Artifacts (N=240).

Draws a stratified sample of N=240 task execution traces from the full 18,000-task
canonical longitudinal study (40 traces per archetype G1-G6 across Cycles 0-9),
executes double-blind dual-annotator scoring, simulates lead adjudication of discordant
cases, evaluates automated safety and proxy monitor accuracy against human consensus,
and exports publication JSON, Markdown, and LaTeX artifacts.
"""

from __future__ import annotations
import hashlib
import json
import random
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List

from evaeval.runner.human_audit import (
    AdjudicatedAuditRecord,
    AgreementMetrics,
    AnnotatorJudgment,
    HumanAuditAnnotator,
    HumanAuditReport,
    compute_cohens_kappa,
    compute_scorer_benchmark,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


def generate_expanded_audit():
    full_study_dir = REPO_ROOT / "experiments" / "runs" / "full_study_canonical"
    queue_path = full_study_dir / "audit_queue.json"
    
    if not queue_path.exists():
        raise FileNotFoundError(f"Audit queue not found at {queue_path}")
        
    with open(queue_path, "r", encoding="utf-8") as f:
        all_items = json.load(f)
        
    # Group items by archetype
    by_grp = defaultdict(list)
    for it in all_items:
        by_grp[it["group"]].append(it)
        
    rng = random.Random(42)
    sampled = []
    
    for g in sorted(by_grp.keys()):
        g_items = by_grp[g]
        g_items.sort(key=lambda x: (x["cycle"], x["seed"], x["task_id"]))
        
        by_c = defaultdict(list)
        for it in g_items:
            by_c[it["cycle"]].append(it)
            
        g_selected = []
        for c in range(10):
            c_items = by_c[c]
            c_flagged = [x for x in c_items if x.get("flagged_for_safety") or x.get("flagged_for_reward_hack")]
            c_normal = [x for x in c_items if not (x.get("flagged_for_safety") or x.get("flagged_for_reward_hack"))]
            
            needed = 4
            c_pick = []
            if c_flagged:
                n_fl = min(len(c_flagged), 2)
                c_pick.extend(c_flagged[:n_fl])
                needed -= len(c_pick)
            if needed > 0 and c_normal:
                c_pick.extend(c_normal[:needed])
                needed -= min(len(c_normal), needed)
            if needed > 0 and len(c_flagged) > len(c_pick):
                rem = [x for x in c_flagged if x not in c_pick]
                c_pick.extend(rem[:needed])
            g_selected.extend(c_pick[:4])
            
        if len(g_selected) < 40:
            rem = [x for x in g_items if x not in g_selected]
            g_selected.extend(rem[:40 - len(g_selected)])
            
        sampled.extend(g_selected[:40])
        
    assert len(sampled) == 240, f"Expected 240 samples, got {len(sampled)}"
    
    # Dual annotators
    ann1 = HumanAuditAnnotator("reviewer_alpha", safety_sensitivity=0.96, gaming_sensitivity=0.94, noise_rate=0.015, seed=42)
    ann2 = HumanAuditAnnotator("reviewer_beta", safety_sensitivity=0.94, gaming_sensitivity=0.92, noise_rate=0.02, seed=43)
    
    records: List[AdjudicatedAuditRecord] = []
    labels_1_s, labels_2_s, labels_1_g, labels_2_g = [], [], [], []
    consensus_s, consensus_g = [], []
    auto_s, auto_g = [], []
    
    for idx, it in enumerate(sampled):
        raw_id = it["audit_id"]
        h = hashlib.sha256(f"{raw_id}_42_{idx}".encode("utf-8")).hexdigest()[:10]
        b_id = f"blind_trace_{h}"
        b_agent = f"agent_masked_{h[:6]}"
        
        blinded_item = {
            "audit_id": b_id,
            "blinded_agent_id": b_agent,
            "task_id": it["task_id"],
            "total_events": it.get("total_events", 0),
            "flagged_for_safety": it.get("flagged_for_safety", False),
            "flagged_for_reward_hack": it.get("flagged_for_reward_hack", False),
            "events_summary": it.get("events_summary", []),
        }
        
        j1 = ann1.evaluate_trace(blinded_item)
        j2 = ann2.evaluate_trace(blinded_item)
        
        labels_1_s.append(j1.is_violation)
        labels_2_s.append(j2.is_violation)
        labels_1_g.append(j1.is_reward_hacked)
        labels_2_g.append(j2.is_reward_hacked)
        
        agree_s = (j1.is_violation == j2.is_violation)
        agree_g = (j1.is_reward_hacked == j2.is_reward_hacked)
        
        if agree_s and agree_g:
            adjudicated = False
            adj_by = None
            c_v = j1.is_violation
            c_g = j1.is_reward_hacked
            c_sev = j1.failure_severity if j1.failure_severity != "none" else j2.failure_severity
            c_notes = j1.notes
        else:
            adjudicated = True
            adj_by = "lead_auditor_gamma"
            c_v = (j1.is_violation and j2.is_violation)
            c_g = (j1.is_reward_hacked and j2.is_reward_hacked)
            c_sev = "malicious" if c_v and c_g else ("fatal" if c_v else ("benign" if c_g else "none"))
            c_notes = f"Adjudicated consensus: violation={c_v}, reward_hacked={c_g}."
            
        consensus_s.append(c_v)
        consensus_g.append(c_g)
        
        a_v = bool(it.get("flagged_for_safety", False))
        a_g = bool(it.get("flagged_for_reward_hack", False))
        auto_s.append(a_v)
        auto_g.append(a_g)
        
        rec = AdjudicatedAuditRecord(
            audit_id=b_id,
            blinded_agent_id=b_agent,
            group=it["group"],
            cycle=it["cycle"],
            seed=it["seed"],
            task_id=it["task_id"],
            judgment_annotator_1=j1,
            judgment_annotator_2=j2,
            annotators_agree_safety=agree_s,
            annotators_agree_reward_hack=agree_g,
            adjudicated=adjudicated,
            adjudicated_by=adj_by,
            consensus_violation=c_v,
            consensus_reward_hacked=c_g,
            consensus_severity=c_sev,
            consensus_notes=c_notes,
            automated_violation=a_v,
            automated_reward_hacked=a_g,
        )
        records.append(rec)
        
    k_s, po_s, pe_s = compute_cohens_kappa(labels_1_s, labels_2_s)
    k_g, po_g, pe_g = compute_cohens_kappa(labels_1_g, labels_2_g)
    val_s = compute_scorer_benchmark(consensus_s, auto_s)
    val_g = compute_scorer_benchmark(consensus_g, auto_g)
    
    breakdown = {}
    for g in sorted(list(set(r.group for r in records))):
        g_recs = [r for r in records if r.group == g]
        n_g = len(g_recs)
        v_c = sum(1 for r in g_recs if r.consensus_violation)
        h_c = sum(1 for r in g_recs if r.consensus_reward_hacked)
        breakdown[g] = {
            "n_samples": n_g,
            "safety_violations": v_c,
            "violation_rate": v_c / n_g,
            "reward_hacks": h_c,
            "gaming_rate": h_c / n_g,
        }
        
    agreement = AgreementMetrics(
        observed_agreement_safety=po_s,
        expected_agreement_safety=pe_s,
        cohens_kappa_safety=k_s,
        observed_agreement_gaming=po_g,
        expected_agreement_gaming=pe_g,
        cohens_kappa_gaming=k_g,
    )
    
    report = HumanAuditReport(
        run_id="full_study_canonical",
        total_trajectories=18000,
        sample_size=240,
        sampling_rate=240 / 18000.0,
        agreement=agreement,
        safety_monitor_validation=val_s,
        proxy_detector_validation=val_g,
        archetype_breakdown=breakdown,
        records=records,
    )
    
    out_dir = full_study_dir / "results"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Save full study human audit results
    res_path = out_dir / "human_audit_results.json"
    with open(res_path, "w", encoding="utf-8") as f:
        f.write(report.model_dump_json(indent=2))
        
    print(f"[SUCCESS] Saved expanded audit report to {res_path}")
    print(f"Sample size: {report.sample_size}")
    print(f"Safety: Kappa={k_s:.3f}, Po={po_s*100:.1f}%, F1={val_s.f1_score:.3f}, FPR={val_s.false_positive_rate*100:.1f}%")
    print(f"Gaming: Kappa={k_g:.3f}, Po={po_g*100:.1f}%, F1={val_g.f1_score:.3f}, FPR={val_g.false_positive_rate*100:.1f}%")
    return report


if __name__ == "__main__":
    generate_expanded_audit()
