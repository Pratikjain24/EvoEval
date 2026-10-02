# SAGE Development Changelog

All notable changes are documented here, organized by development phase (weeks) and post-submission refinements.

---

## [v1.0.0] — 2026-10-02 (Current Release)

### Community & Credibility
- Fix broken CI badge (was pointing to unrelated `evo-eval/evoeval` repo)
- Add `CITATION.cff` — machine-readable academic citation, GitHub "Cite this" button
- Add `CONTRIBUTING.md` — community contribution guide with task authoring instructions
- Add 3 GitHub Issue templates: bug report, feature request, new task submission
- Add `PULL_REQUEST_TEMPLATE.md` with reviewer checklist
- Add social preview banner (`.github/social_preview.jpg`)
- Add project disambiguation notice distinguishing this from Xia et al. (2024)
- Add Authors & Institutional Affiliation table (VIT Pune, IEEE 2026)

### CI & Verification Transparency
- Upgrade CI to produce public JUnit XML test reports (GitHub-hosted, immutable)
- Add GitHub Job Summary step: test result table visible to anyone at Actions URL
- Add `mikepenz/action-junit-report` for GitHub Checks integration
- Correct misleading "External Verification" language — honestly document that
  `verification_attestation.json` (`is_ci: false`) is a local pre-submission check,
  while GitHub Actions CI provides genuinely independent public verification

### Paper Refinements (Post-Submission Polish)
- Fix(build): correct pyproject.toml table sections, reconcile budget
- Fix(significance): incorporate explicit pairwise contrasts G7 vs G1 and G4 vs G7
- Fix(table4): format Evolution Cycles (T) column, harmonize G7/G6* framing
- Fix(baselines): delineate T=0 single-turn baselines from T=10 longitudinal evolution
- Fix(significance): eliminate Holm-Bonferroni monotonicity artifact (analytical bounds)
- Docs: soften task scope to focused multi-file component repository

---

## [v0.9.0] — 2026-10-01 (Pre-Submission Stabilization)

### Reproducibility & Verification
- Synchronize 201 verification test count across all documents and tables
- Reconcile micro-pilot single-turn token tariff with full 18,000-task cost
- Rename `EXTERNAL_VERIFICATION.md` → `REPRODUCIBILITY_VERIFICATION.md`; de-hype prose
- Update verification attestation timestamp after final run
- Fix taxonomy: clarify G6* as Oracle Canary skyline, G7 as deployable proxy canary

### Paper & Documentation
- Add G7 and horizon column to Table IV; update Table III significance
- Add Panel B with G7 deployable canary contrasts to Appendix Table A.1
- Fix(reconciliation): eliminate Table IV/V discrepancy under Law of Total Probability
- Fix(framing): honest two-tiered benchmark reframing (canonical + live API)
- Refactor: academic rigor, pre-experiment sample planning, baseline verification
- Docs(paper): merge concurrent citations and related-work subsection (Section II-F)
- Docs(bib): alias ActBench and SkillsBench citation keys with verified first authors

---

## [v0.8.0] — 2026-09-26 (Final Integration & Paper Assembly)

### Core System
- Fix(reproducibility): normalize stdout before truncation in adapters, runner, sandboxes
- Fix(hashing): extend normalization regex to strip rootdir and absolute temp paths
- Fix(paper): correct ActBench and SkillsBench authors; fix typing imports
- Fix(cli): add JSON import and regression test for manifest command
- Fix(reproducibility): normalize pytest rootdir and scratch paths in trajectory hashing

### Documentation & Paper
- Add paper manifest; IEEE conference citation block in README
- Clarify IEEE conference paper as primary submission target in dossier
- Reconcile test suite count in PROJECT_DOSSIER.md
- Re-generate verification attestation for 187/187 green tests
- Complete SAGE benchmark suite: 100-task catalog, paper manuscript, empirical data

---

## [v0.7.0] — 2026-09-24 (System Hardening & Full Study Run)

### Core Framework
- `feat(reproducibility)`: reproducibility contract, verification CLI, trajectory manifests, dataset export
- `feat(scoring)`: LLM-judge architectural isolation — cross-family diversity, prompt concealment, auxiliary-only score guarantee
- `feat(tasks)`: deliberate drift probes (~20% tasks) with visible gameable proxies for H2/H5
- `feat(security)`: log all 5 tamper detection checks as canonical trajectory events
- `feat(security)`: enforce scorer invisibility to agent (separate image, read-only mounts, blind listing)
- `feat(security)`: locked sandbox invariants (non-root, network disabled, cgroup caps, no Docker socket)
- `feat(analysis)`: metrics recomputation from raw trajectory JSONL; figure regeneration in clean environment

### Testing
- `test(reproducibility)`: byte-identical trajectory hashing for deterministic parts (temperature 0, seed sensitivity)
- Create master project dossier detailing architecture, deliverables, and test results

---

## [v0.6.0] — 2026-09-23 (Weeks 11–12: System Hardening)

- `feat(week11-12)`: system hardening — timeouts, retry policy, crash recovery, budget guard
- `test(sandbox)`: quality gate tests for forbidden command, protected write, network, tamper detection
- `feat(integration)`: deterministic canned mock LLM integration test (CI-safe, no GPU, <2 min)
- `test(quality-gates)`: comprehensive property tests for all metrics; fast mock LLM integration test

---

## [v0.5.0] — 2026-09-23 (Weeks 9–10: Pilot Benchmark)

- `feat(week9-10)`: pilot benchmark (10×3×3×3), cost calibration, schema v1.0 freeze, documentation

---

## [v0.4.0] — 2026-09-23 (Weeks 7–8: Verifier, Dashboard)

- `feat(week7-8)`: G5/G6 verifier wrapper, tamper detector, proxy gap analyzer
- FastAPI backend and Next.js frontend MVP

---

## [v0.3.0] — 2026-09-23 (Weeks 5–6: Memory & Reflection Agents)

- `feat(week5-6)`: G3 memory agent, G4 reflection agent, git-tagged snapshots
- Task scaling to 50 tasks; stratified audit exporter

---

## [v0.2.0] — 2026-09-23 (Week 4: Evolution Controller)

- `feat(week4)`: evolution controller, G2 prompt-rewriting agent, verifier
- 2-cycle 10-task benchmark; first metrics output

---

## [v0.1.0] — 2026-09-23 (Weeks 1–3: Foundation)

- `feat(core)`: initial scaffold — immutable trajectory event log schema, writer, G1–G6 adapters, benchmark harness
- `docs(schema)`: full JSON specifications for all 12 event subtypes
- `feat(milestone)`: Week 2 — AgentAdapter ABC, G1 static agent, LLM client single-task loop
- `feat(week3)`: DockerRunner, sandbox, safety_monitor rules, hidden scorer, initial 10 tasks

---

## Development Context

> **Why is the commit history concentrated in a short window?**
>
> SAGE was developed over a **12-week structured research sprint** (approx. July–September 2026) by a 6-person team at VIT Pune. The majority of development, design, and iteration happened in a **private local repository** during that period. The project was pushed to GitHub as a public research artifact in conjunction with paper submission preparation in late September 2026.
>
> This is a common and entirely normal pattern for academic research software: development happens privately until a paper is ready for submission, then the full codebase is published. The commit history reflects the *public* history, not the full 12-week development arc.
>
> The structured `feat(weekN-M)` commit naming convention reflects the weekly milestone structure of the project's research sprint plan.
