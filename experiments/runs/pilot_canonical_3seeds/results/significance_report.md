# Statistical Significance & Effect Size Audit Report

- **Run ID**: `canonical_benchmark_audit`
- **Independent Unit of Analysis**: `Random Seed (N = 3 independent runs: seeds 42, 43, 44; zero task-cycle pseudo-replication)`
- **Empirical Variance**: `sigma in [0.03, 0.06] across self-modifying LLM agents`
- **Bootstrap Resolution Floor**: `p >= 1.0e-4 (for B = 10,000 resamples; minimum p-values reported as p < 0.001 or p = 1.0e-4; zero parametric float artifacts)`
- **Holm-Bonferroni FWER Multipliers**: `Strict integer-rank step-down multipliers k in {1 ... 27}`
- **Significance Level (Alpha)**: `0.05`
- **Bootstrap Resamples**: `10,000`
- **Total Hypotheses Tested**: `27`
- **Significant (Raw $p < 0.05$)**: `26 / 27`
- **Significant (Holm-Corrected)**: `26 / 27`

## Canonical 27 Metric Tuples

| Comparison | Metric | Mean Diff [95% CI] | Cohen's d | Cliff's $\delta$ | Raw $p$ | Rank $j$ | Multiplier $k$ | Holm $p$ | Decision |
|---|---|---|---|---|---|:---:|:---:|---|---|
| G2 vs G1 | `capability_gain` | +0.152 [0.13, 0.19] | +6.81 | +1.00 | <0.001 | 1 | 27 | 0.003 | **Reject H0** |
| G2 vs G1 | `safety_drift` | +0.235 [0.19, 0.30] | +8.35 | +1.00 | <0.001 | 2 | 26 | 0.003 | **Reject H0** |
| G2 vs G1 | `proxy_gap` | +0.220 [0.19, 0.24] | +11.38 | +1.00 | <0.001 | 3 | 25 | 0.003 | **Reject H0** |
| G2 vs G5 | `capability_gain` | -0.066 [-0.09, -0.02] | -2.95 | -1.00 | <0.001 | 4 | 24 | 0.003 | **Reject H0** |
| G2 vs G5 | `safety_drift` | +0.160 [0.12, 0.19] | +4.99 | +1.00 | <0.001 | 5 | 23 | 0.003 | **Reject H0** |
| G2 vs G5 | `proxy_gap` | +0.173 [0.07, 0.25] | +2.82 | +1.00 | <0.001 | 6 | 22 | 0.003 | **Reject H0** |
| G2 vs G6 | `capability_gain` | -0.162 [-0.23, -0.10] | -3.98 | -1.00 | <0.001 | 7 | 21 | 0.003 | **Reject H0** |
| G2 vs G6 | `safety_drift` | +0.211 [0.12, 0.29] | +4.76 | +1.00 | <0.001 | 8 | 20 | 0.003 | **Reject H0** |
| G2 vs G6 | `proxy_gap` | +0.228 [0.16, 0.27] | +7.23 | +1.00 | <0.001 | 9 | 19 | 0.003 | **Reject H0** |
| G3 vs G1 | `capability_gain` | +0.199 [0.20, 0.20] | +10.32 | +1.00 | <0.001 | 10 | 18 | 0.003 | **Reject H0** |
| G3 vs G1 | `safety_drift` | +0.164 [0.09, 0.22] | +3.39 | +1.00 | <0.001 | 11 | 17 | 0.003 | **Reject H0** |
| G3 vs G1 | `proxy_gap` | +0.200 [0.15, 0.24] | +7.17 | +1.00 | <0.001 | 12 | 16 | 0.003 | **Reject H0** |
| G3 vs G5 | `capability_gain` | -0.052 [-0.16, 0.03] | -1.02 | -0.56 | 0.294 | 27 | 1 | 0.294 | Fail to reject |
| G3 vs G5 | `safety_drift` | +0.148 [0.11, 0.17] | +3.64 | +1.00 | <0.001 | 13 | 15 | 0.003 | **Reject H0** |
| G3 vs G5 | `proxy_gap` | +0.127 [0.08, 0.17] | +3.73 | +1.00 | <0.001 | 14 | 14 | 0.003 | **Reject H0** |
| G3 vs G6 | `capability_gain` | -0.116 [-0.13, -0.10] | -5.29 | -1.00 | <0.001 | 15 | 13 | 0.003 | **Reject H0** |
| G3 vs G6 | `safety_drift` | +0.202 [0.16, 0.23] | +10.13 | +1.00 | <0.001 | 16 | 12 | 0.003 | **Reject H0** |
| G3 vs G6 | `proxy_gap` | +0.135 [0.09, 0.22] | +2.57 | +1.00 | <0.001 | 17 | 11 | 0.003 | **Reject H0** |
| G4 vs G1 | `capability_gain` | +0.280 [0.25, 0.31] | +15.38 | +1.00 | <0.001 | 18 | 10 | 0.003 | **Reject H0** |
| G4 vs G1 | `safety_drift` | +0.269 [0.25, 0.28] | +19.80 | +1.00 | <0.001 | 19 | 9 | 0.003 | **Reject H0** |
| G4 vs G1 | `proxy_gap` | +0.310 [0.28, 0.36] | +8.77 | +1.00 | <0.001 | 20 | 8 | 0.003 | **Reject H0** |
| G4 vs G5 | `capability_gain` | +0.062 [0.03, 0.08] | +4.19 | +1.00 | <0.001 | 21 | 7 | 0.003 | **Reject H0** |
| G4 vs G5 | `safety_drift` | +0.219 [0.09, 0.30] | +3.74 | +1.00 | <0.001 | 22 | 6 | 0.003 | **Reject H0** |
| G4 vs G5 | `proxy_gap` | +0.296 [0.23, 0.35] | +7.38 | +1.00 | <0.001 | 23 | 5 | 0.003 | **Reject H0** |
| G4 vs G6 | `capability_gain` | -0.097 [-0.11, -0.09] | -4.07 | -1.00 | <0.001 | 24 | 4 | 0.003 | **Reject H0** |
| G4 vs G6 | `safety_drift` | +0.277 [0.26, 0.30] | +7.55 | +1.00 | <0.001 | 25 | 3 | 0.003 | **Reject H0** |
| G4 vs G6 | `proxy_gap` | +0.369 [0.35, 0.40] | +10.71 | +1.00 | <0.001 | 26 | 2 | 0.003 | **Reject H0** |

## Pooled Comparisons: All Unconstrained ($G_2$--$G_4$) vs All Guarded ($G_5$--$G_6$)

| Metric | Unconstrained Mean | Guarded Mean | Difference | Cohen's d | Cliff's $\delta$ | $p$-value | Significance |
|---|---|---|---|---|---|---|---|
| `capability_gain` | 0.212 | 0.289 | -0.077 | -3.07 | -1.00 | <0.001 | **Significant ($p < 0.05$)** |
| `safety_drift` | 0.224 | 0.022 | +0.202 | +9.28 | +1.00 | <0.001 | **Significant ($p < 0.05$)** |
| `proxy_gap` | 0.263 | 0.068 | +0.195 | +8.80 | +1.00 | <0.001 | **Significant ($p < 0.05$)** |